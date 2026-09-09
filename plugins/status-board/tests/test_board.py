import importlib.util
from concurrent.futures import Future
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


spec = importlib.util.spec_from_file_location("board", Path(__file__).parents[1] / "board.py")
board = importlib.util.module_from_spec(spec)
spec.loader.exec_module(board)


class BoardTests(unittest.TestCase):
    def test_enter_sends_and_ctrl_j_inserts_newline(self):
        for enter in ("\r", board.curses.KEY_ENTER):
            with tempfile.TemporaryDirectory() as root:
                args = SimpleNamespace(tasks=Path(root) / "tasks", offline=False)
                row = board.task_summary(self.task(), 0, None, None, 5)
                screen = Mock()
                screen.getmaxyx.return_value = (38, 140)
                screen.get_wch.side_effect = [*"First", "\n", *"Second", enter]
                with patch.object(board.curses, "curs_set"), patch.object(
                    board, "send_message", return_value=(True, "Delivered")
                ) as send:
                    self.assertEqual(board.compose(screen, args, row, inline=True), "Delivered")
                send.assert_called_once_with(args, row, "First\nSecond")

    def run_display(self, executor, keys):
        screen = Mock()
        screen.getmaxyx.return_value = (38, 140)
        screen.getch.side_effect = keys
        args = SimpleNamespace(tasks=Path("/unused/tasks"), offline=True, interval=5)
        with patch.object(board.curses, "nonl"), patch.object(board.curses, "curs_set"), patch.object(board.curses, "mousemask"), patch.object(
            board.curses, "mouseinterval"
        ) as interval, patch.object(board.curses, "has_colors", return_value=False):
            board.display_loop(screen, args, executor)
        interval.assert_called_once_with(0)
        return screen

    def test_slow_refresh_does_not_block_input_or_queue_more_work(self):
        executor = Mock()
        pending = Future()
        executor.submit.return_value = pending
        screen = self.run_display(executor, [ord("r"), board.curses.KEY_DOWN, ord("r"), ord("q")])
        self.assertFalse(pending.done())
        executor.submit.assert_called_once_with(board.snapshot, Path("/unused/tasks"), True)
        self.assertEqual(screen.getch.call_count, 4)

    def test_failed_background_refresh_is_visible_without_crashing(self):
        executor = Mock()
        pending = Future()
        pending.set_exception(OSError("inventory unavailable"))
        executor.submit.return_value = pending
        screen = self.run_display(executor, [-1, ord("q")])
        self.assertTrue(any("Refresh failed" in str(call) for call in screen.addnstr.call_args_list))

    def test_multiple_prs_preserve_hosts_and_ignore_historical_links(self):
        public = "https://github.com/team/project/pull/12"
        enterprise = "https://github.carnegierobotics.com/team/project/pull/12"
        stacked = "https://github.com/team/meta/pull/34"
        task = self.task()
        task.update(pull_request={"url": public, "legacy_url": "https://github.com/old/project/pull/1"},
                    follow_up_pull_requests={"component": {"url": enterprise}, "duplicate": {"url": public},
                                             "review_order": ["component", "duplicate"]},
                    stacked_pull_request={"url": stacked})
        row = board.task_summary(task, 0, None, None, 5)
        self.assertEqual(row["prs"], [public, enterprise, stacked])
        self.assertIn("#12, #12, #34", board.table_line(row, 140, 20))
        self.assertEqual(board.pr_labels(row), [("#12", public), ("#12", enterprise), ("#34", stacked)])
        lines = board.detail_lines(row, 40)
        for url, label in [(public, "project#12"), (enterprise, "project#12"), (stacked, "meta#34")]:
            self.assertEqual("".join(line[left:right] for line, _, spans in lines
                                     for left, right, target in spans if target == url), label)
        self.assertTrue(all(len(line) <= 36 for line, _, _ in lines))
        self.assertEqual(board.detail_lines(row, 140)[-1][0], "PRs: project#12, project#12, meta#34")
        narrow = board.detail_lines(row, 10)
        for url in row["prs"]:
            self.assertTrue(any(target == url for _, _, spans in narrow for _, _, target in spans))

    def test_pr_collection_list_and_absent_prs(self):
        url = "https://github.com/team/project/pull/1"
        self.assertEqual(board.pr_links({"pull_requests": [{"url": url}, url, "not a PR"]}), [url])
        self.assertEqual(board.pr_links({}), [])

    def test_composer_preserves_failed_message_then_restores_and_sends(self):
        with tempfile.TemporaryDirectory() as root:
            args = SimpleNamespace(tasks=Path(root) / "tasks", offline=False)
            row = board.task_summary(self.task(), 0, None, None, 5)
            screen = Mock()
            screen.getmaxyx.return_value = (24, 80)
            screen.get_wch.side_effect = list("Please investigate\nfirst") + ["\x07", "\x1b"]
            with patch.object(board.curses, "curs_set"), patch.object(
                board, "send_message", return_value=(False, "Busy; draft kept")
            ) as send:
                board.compose(screen, args, row)
                self.assertEqual(send.call_args.args[2], "Please investigate\nfirst")
            self.assertEqual(board.draft_path(args, row).read_text(), "Please investigate\nfirst")
            screen.get_wch.side_effect = ["\x07"]
            with patch.object(board.curses, "curs_set"), patch.object(
                board, "send_message", return_value=(True, "Delivered")
            ) as send:
                self.assertEqual(board.compose(screen, args, row), "Delivered")
                self.assertEqual(send.call_args.args[2], "Please investigate\nfirst")
            self.assertFalse(board.draft_path(args, row).exists())

    def test_inline_composer_keeps_task_visible_and_saves_on_blur(self):
        with tempfile.TemporaryDirectory() as root:
            args = SimpleNamespace(tasks=Path(root) / "tasks", offline=False)
            row = board.task_summary(self.task(), 0, None, None, 5)
            screen = Mock()
            screen.getmaxyx.return_value = (38, 100)
            screen.get_wch.side_effect = list("Investigate this") + [board.curses.KEY_MOUSE]
            with patch.object(board.curses, "curs_set"), patch.object(board.curses, "ungetmouse") as mouse, patch.object(
                board, "mouse_event", return_value=("select", 10, 6, 0)
            ):
                self.assertEqual(board.compose(screen, args, row, inline=True),
                                 ("Draft saved; nothing sent.", ("select", 10, 6, 0)))
            screen.erase.assert_not_called()
            mouse.assert_not_called()
            self.assertEqual(board.draft_path(args, row).read_text(), "Investigate this")

    def test_clear_only_removes_selected_task_draft_and_never_sends(self):
        with tempfile.TemporaryDirectory() as root:
            args = SimpleNamespace(tasks=Path(root) / "tasks", offline=False)
            row = board.task_summary(self.task(), 0, None, None, 5)
            other = dict(row, id="another-task")
            board.save_draft(board.draft_path(args, row), "discard this")
            board.save_draft(board.draft_path(args, other), "keep this")
            with patch.object(board, "send_message") as send:
                self.assertIn("cleared", board.compose(Mock(), args, row, inline=True, clear_now=True))
            send.assert_not_called()
            self.assertEqual(board.draft_path(args, row).read_text(), "")
            self.assertEqual(board.draft_path(args, other).read_text(), "keep this")

    def test_escape_outside_editor_does_not_close_board(self):
        executor = Mock()
        executor.submit.return_value = Future()
        screen = self.run_display(executor, [27, ord("q")])
        self.assertEqual(screen.getch.call_count, 2)

    def test_selected_objective_and_rows_below_it_are_clickable(self):
        task = self.task()
        task["objective"] = "Investigate reconnect failures without changing source."
        row = board.task_summary(task, 0, None, None, 5)
        self.assertEqual(row["objective"], task["objective"])
        self.assertEqual(board.clicked_row(10, 6, 100, 0, 5, 10, 0), 0)
        self.assertEqual(board.clicked_row(10, 7, 100, 0, 5, 10, 0), 1)
        self.assertEqual(board.clicked_row(10, 6, 100, 0, 5, 10, 2), 1)
        self.assertEqual(board.clicked_row(10, 8, 100, 0, 5, 10, 2), 2)
        self.assertEqual(board.clicked_row(10, 9, 100, 0, 5, 10, 2), 3)
        self.assertIsNone(board.clicked_row(10, 11, 100, 0, 5, 10, 2))

    def test_send_preserves_exact_human_message_and_routes_only_to_controller(self):
        row = board.task_summary(self.task(), 0, None, None, 5)
        args = SimpleNamespace(offline=False, tasks=Path("/control/.orchestrator/tasks"))
        response = SimpleNamespace(stdout=board.json.dumps({"result": {"agent": {
            "workspace_id": "control", "agent_status": "idle"}}}))
        delivered = SimpleNamespace(stdout=board.json.dumps({"result": {"type": "agent_prompted"}}))
        message = 'Please investigate this first.\nDo not implement yet: "scope".'
        with patch.dict(board.os.environ, {"HERDR_ENV": "1", "HERDR_WORKSPACE_ID": "control"}), patch.object(
            board.subprocess, "run", side_effect=[response, delivered]
        ) as run:
            success, _ = board.send_message(args, row, message)
        self.assertTrue(success)
        command = run.call_args_list[1].args[0]
        self.assertEqual(command[1:4], ["agent", "prompt", "workflow_orchestrator"])
        self.assertEqual(command[-1], f"Human message about {row['label']} (task: example):\n\n{message}")

    def test_busy_or_wrong_workspace_never_receives_prompt(self):
        args = SimpleNamespace(offline=False, tasks=Path("/control/tasks"))
        row = board.task_summary(self.task(), 0, None, None, 5)
        for workspace, status in [("control", "working"), ("control", "blocked"), ("other", "idle")]:
            response = SimpleNamespace(stdout=board.json.dumps({"result": {"agent": {
                "workspace_id": workspace, "agent_status": status}}}))
            with patch.dict(board.os.environ, {"HERDR_ENV": "1", "HERDR_WORKSPACE_ID": "control"}), patch.object(
                board.subprocess, "run", return_value=response
            ) as run:
                success, _ = board.send_message(args, row, "Hello")
            self.assertFalse(success)
            self.assertEqual(run.call_count, 1)

    def test_uncertain_delivery_is_not_retried(self):
        args = SimpleNamespace(offline=False, tasks=Path("/control/tasks"))
        row = board.task_summary(self.task(), 0, None, None, 5)
        response = SimpleNamespace(stdout=board.json.dumps({"result": {"agent": {
            "workspace_id": "control", "agent_status": "idle"}}}))
        with patch.dict(board.os.environ, {"HERDR_ENV": "1", "HERDR_WORKSPACE_ID": "control"}), patch.object(
            board.subprocess, "run", side_effect=[response, board.subprocess.TimeoutExpired("herdr", 10)]
        ) as run:
            success, note = board.send_message(args, row, "Hello")
        self.assertFalse(success)
        self.assertIn("Check orchestrator before retrying", note)
        self.assertEqual(run.call_count, 2)

    def test_private_draft_survives_reopen_without_touching_task_records(self):
        with tempfile.TemporaryDirectory() as root:
            args = SimpleNamespace(tasks=Path(root) / "tasks")
            path = board.draft_path(args, {"id": "../../example"})
            board.save_draft(path, "Original\nmessage")
            self.assertEqual(path.parent, Path(root) / "board-drafts")
            self.assertEqual(path.read_text(), "Original\nmessage")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            board.save_draft(path, "Updated")
            self.assertEqual(path.read_text(), "Updated")
            self.assertFalse(args.tasks.exists())

    def test_mouse_clicks_map_only_visible_task_rows(self):
        self.assertEqual(board.clicked_row(10, 6, 100, 3, 5, 10), 4)
        for x, y in [(0, 6), (100, 6), (10, 4), (10, 10)]:
            self.assertIsNone(board.clicked_row(x, y, 100, 3, 5, 10))
        self.assertIsNone(board.clicked_row(10, 9, 100, 3, 5, 6))

    def test_mouse_reports_clicks_and_wheel_direction(self):
        for flag, expected in [(board.curses.BUTTON1_CLICKED, "select"),
                               (board.curses.BUTTON1_DOUBLE_CLICKED, "open"),
                               (board.curses.BUTTON4_PRESSED, "wheel")]:
            with patch.object(board.curses, "getmouse", return_value=(0, 10, 6, 0, flag)):
                event = board.mouse_event()
                self.assertEqual(event[0], expected)
                if expected == "wheel":
                    self.assertEqual(event[3], -1)

    def test_pr_links_preserve_public_and_enterprise_urls(self):
        with patch.object(board.webbrowser, "open", return_value=True) as launch:
            for host in ["github.com", "github.carnegierobotics.com"]:
                url = f"https://{host}/team/repo/pull/123"
                self.assertTrue(board.open_pr(url))
                launch.assert_called_with(url, new=2)
            launch.reset_mock()
            for url in ["file:///tmp/example", "javascript:alert(1)", "https://[broken"]:
                self.assertFalse(board.open_pr(url))
            launch.assert_not_called()

    def task(self, stage="reviewing"):
        return {"task_id": "example", "workspace": {"id": "w1", "label": "old-name"},
                "agents": {"reviewer": "reviewer"}, "state": {"name": stage},
                "review": {"rounds_this_scope": 2}, "event_recovery": {"expected_role": "reviewer"}}

    def test_live_done_does_not_complete_review(self):
        task = self.task()
        row = board.task_summary(task, 0, [{"workspace_id": "w1", "label": "new-name"}],
            [{"name": "reviewer", "workspace_id": "w1", "agent_status": "done"}], 5)
        self.assertEqual((row["label"], row["color"]), ("new-name", 2))
        self.assertIn("reviewing r3", row["stage"])
        self.assertIn("Reviewer done → reviewer", row["roles"])
        self.assertIsNone(row["action"])
        self.assertEqual(task["workspace"]["label"], "old-name")

    def test_completed_pr_is_green_with_human_handoff(self):
        row = board.task_summary(self.task("ready-for-team-review"), 0, None, None, 5)
        self.assertEqual(row["color"], 3)
        self.assertIn("Review the ready PR", row["action"])

    def test_attention_and_missing_identity(self):
        task = self.task()
        task["state"].update(attention_required=True, attention_reason="Approve the plan")
        row = board.task_summary(task, 0, [],
            [{"name": "reviewer", "workspace_id": "other", "agent_status": "working"}], 5)
        self.assertEqual(row["color"], 1)
        self.assertIn("workspace missing", row["label"])
        self.assertIn("Reviewer missing → you", row["roles"])
        self.assertIn("Approve the plan", row["action"])

    def test_decisions_precede_completed_handoffs_and_passive_work(self):
        passive = self.task()
        passive["task_id"] = "passive"
        ready = self.task("ready-for-team-review")
        ready["task_id"] = "ready"
        decision = self.task("decision-required")
        decision["task_id"] = "decision"
        decision["state"].update(attention_required=True, attention_reason="Choose scope")
        with patch.object(board, "read_tasks", return_value=([(t, 0) for t in [passive, ready, decision]], [])):
            rows, _ = board.snapshot(Path("/unused"), offline=True)
        self.assertEqual([row["id"] for row in rows], ["decision", "ready", "passive"])

    def test_bad_record_does_not_hide_other_tasks_or_modify_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contents = {"active.yaml": "task_id: active\nstate: {name: reviewing}\n",
                        "closed.yaml": "task_id: gone\nstate: {name: cleaned}\n",
                        "bad.yaml": "state: [unfinished"}
            for name, content in contents.items():
                (root / name).write_text(content)
            tasks, warnings = board.read_tasks(root)
            self.assertEqual([t["task_id"] for t, _ in tasks], ["active"])
            self.assertEqual(len(warnings), 1)
            for name, content in contents.items():
                self.assertEqual((root / name).read_text(), content)

    def test_live_failure_is_visible_and_does_not_reuse_stale_inventory(self):
        with patch.dict(board.os.environ, {"HERDR_ENV": "1"}), patch.object(
            board.subprocess, "run", side_effect=board.subprocess.TimeoutExpired("herdr", 3)
        ):
            workspaces, agents, warnings = board.inventory()
        self.assertIsNone(workspaces)
        self.assertIsNone(agents)
        self.assertIn("Live state unavailable", warnings[0])


if __name__ == "__main__":
    unittest.main()
