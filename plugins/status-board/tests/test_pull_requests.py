from concurrent.futures import Future
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import board
import pull_requests
from preview_links import LinkedScreen


class PullRequestTests(unittest.TestCase):
    def test_fetch_distinguishes_closed_and_merged_preserving_host(self):
        for host in ("github.com", "github.carnegierobotics.com"):
            for raw, expected in (({"state": "open", "merged_at": None}, "open"),
                                  ({"state": "closed", "merged_at": None}, "closed"),
                                  ({"state": "closed", "merged_at": "2026-10-05"}, "merged"),
                                  ({"state": "unexpected"}, None), ([], None)):
                with patch.object(pull_requests.subprocess, "run", return_value=Mock(stdout=json.dumps(raw))) as run:
                    self.assertEqual(pull_requests.fetch_state(f"https://{host}/team/repo/pull/123"), expected)
                    self.assertEqual(run.call_args.args[0][3], host)
                    self.assertIn("repos/team/repo/pulls/123", run.call_args.args[0])
                    self.assertEqual(run.call_args.kwargs["timeout"], 5)

    def test_unsupported_links_do_not_trigger_requests(self):
        with patch.object(pull_requests.subprocess, "run") as run:
            for url in ("http://github.com/team/repo/pull/1", "https://user@github.com/team/repo/pull/1",
                        "https://github.com/team/repo/issues/1", "https://github.com/team/repo/pull/0"):
                self.assertIsNone(pull_requests.fetch_state(url))
            run.assert_not_called()

    def test_cache_returns_immediately_coalesces_and_retries_after_interval(self):
        with patch.object(pull_requests, "ThreadPoolExecutor") as pool, patch.object(pull_requests.time, "monotonic", return_value=10) as clock:
            cache = pull_requests.PullRequestStates()
            future = Future()
            pool.return_value.submit.return_value = future
            url = "https://github.com/team/repo/pull/1"
            self.assertEqual(cache.snapshot([url, url]), {})
            self.assertEqual(cache.snapshot([url]), {})
            self.assertEqual(pool.return_value.submit.call_count, 1)
            future.set_result("closed")
            self.assertEqual(cache.snapshot([url]), {url: "closed"})
            clock.return_value = 129
            self.assertEqual(cache.snapshot([url]), {url: "closed"})
            self.assertEqual(pool.return_value.submit.call_count, 1)
            clock.return_value = 130
            cache.snapshot([url])
            self.assertEqual(pool.return_value.submit.call_count, 2)
            cache.close()
            pool.return_value.shutdown.assert_called_once_with(wait=False, cancel_futures=True)

    def test_failed_refresh_removes_unconfirmed_marker_without_raising(self):
        with patch.object(pull_requests, "ThreadPoolExecutor") as pool:
            cache = pull_requests.PullRequestStates()
            future = Future()
            future.set_exception(subprocess.TimeoutExpired("gh", 5))
            pool.return_value.submit.return_value = future
            url = "https://github.com/team/repo/pull/1"
            cache.snapshot([url])
            self.assertEqual(cache.snapshot([url]), {})
            self.assertEqual(pool.return_value.submit.call_count, 1)
            cache.close()

    def test_removed_queued_request_can_be_added_again(self):
        with patch.object(pull_requests, "ThreadPoolExecutor") as pool:
            cache = pull_requests.PullRequestStates()
            future = Future()
            pool.return_value.submit.return_value = future
            url = "https://github.com/team/repo/pull/1"
            cache.snapshot([url])
            cache.snapshot([])
            self.assertTrue(future.cancelled())
            pool.return_value.submit.return_value = Future()
            self.assertEqual(cache.snapshot([url]), {})
            self.assertEqual(pool.return_value.submit.call_count, 2)
            cache.close()

    def test_table_and_wrapped_details_keep_complete_clickable_labels(self):
        urls = [f"https://github.com/team/repo/pull/{n}" for n in (123, 456)]
        row = {"prs": urls, "pr_states": dict(zip(urls, ("closed", "merged"))),
               "color": 3, "action": None, "objective": "Completed investigation."}
        text, spans = board.pr_cell(row, 30)
        self.assertEqual(text, "#123×, #456✓")
        self.assertEqual([text[left:right] for left, right, _ in spans], ["#123×", "#456✓"])
        self.assertEqual([url for _, _, url in spans], urls)
        for width in (20, 100):
            lines = board.detail_lines(row, width)
            for url, expected in zip(urls, ("repo#123 (closed)", "repo#456 (merged)")):
                rendered = "".join(line[left:right] for line, _, links in lines
                                   for left, right, target in links if target == url)
                self.assertEqual(rendered.replace(" ", ""), expected.replace(" ", ""))

    def test_terminal_hyperlinks_and_underline_fallback_survive_markers(self):
        screen = Mock()
        screen.getmaxyx.return_value = (20, 80)
        output = io.StringIO()
        linked = LinkedScreen(screen, output)
        url = "https://github.com/team/repo/pull/123"
        board.draw_pr_links(linked, 3, 4, "#123×", [(0, 5, url)])
        linked.refresh()
        self.assertIn(f"\x1b]8;;{url}\x1b\\#123×", output.getvalue())
        self.assertEqual(screen.addnstr.call_args.args[-1], board.curses.A_UNDERLINE)


if __name__ == "__main__":
    unittest.main()
