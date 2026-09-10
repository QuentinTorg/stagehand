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
    def test_responsive_views_stay_inside_terminal_bounds(self):
        for height, width in ((24, 60), (28, 80), (38, 110), (44, 160), (60, 240), (72, 320)):
            for view in ("t", "c", "?"):
                executor = Mock()
                pending = Future()
                row = board.task_summary(self.task(), 0, None, None, 5)
                row["agent_names"] = {"author": "author", "reviewer": "reviewer"}
                row["conversation"] = {"role": "reviewer", "status": "done", "output": "A long worker response. " * 200}
                pending.set_result(([row], [], {"status": "idle", "output": "A response.\n" * 60}))
                executor.submit.return_value = pending
                screen = self.run_display(executor, [-1, ord(view), ord("q")], (height, width))
                for call in screen.addnstr.call_args_list:
                    y, x, text, count, *_ = call.args
                    self.assertTrue(0 <= y < height and 0 <= x < width, (height, width, call))
                    self.assertLessEqual(x + min(len(text), count), width, (height, width, call))
                self.assertTrue(any("Message orchestrator" in str(call) for call in screen.addnstr.call_args_list))

    def test_task_details_put_action_first_and_keep_technical_info_optional(self):
        task = self.task("decision-required")
        task["state"].update(attention_required=True, attention_reason="Approve the plan")
        row = board.task_summary(task, 0, None, None, 5)
        row["location"] = "/private/worktree/path"
        compact = "\n".join(line for line, _, _ in board.detail_lines(row, 140))
        expanded = "\n".join(line for line, _, _ in board.detail_lines(row, 140, info=True))
        self.assertTrue(compact.startswith("NEXT: Approve the plan"))
        self.assertNotIn("record saved", compact)
        self.assertNotIn(row["location"], compact)
        self.assertIn("record saved", expanded)
        self.assertIn(row["location"], expanded)

    def test_task_and_controller_navigation_keep_message_context_separate(self):
        executor = Mock()
        pending = Future()
        row = board.task_summary(self.task(), 0, None, None, 5)
        pending.set_result(([row], [], {"status": "idle", "output": "Ready"}))
        executor.submit.return_value = pending
        with patch.object(board, "compose", return_value="Draft saved.") as compose, patch.object(board, "open_target") as navigate:
            self.run_display(executor, [-1, ord("c"), ord("m"), ord("t"), ord("m"), ord("q")])
        self.assertIsNone(compose.call_args_list[0].args[2])
        self.assertEqual(compose.call_args_list[1].args[2]["id"], row["id"])
        navigate.assert_not_called()

    def test_legacy_stages_remain_readable_without_counters(self):
        row = board.task_summary(self.task("reviewing"), 0, None, None, 5)
        self.assertEqual(board.task_stage(row), "In review")
        row = board.task_summary(self.task("resolving"), 0, None, None, 5)
        self.assertEqual(board.task_stage(row), "Fixing findings")

    def test_prose_does_not_stretch_across_ultrawide_screen(self):
        row = board.task_summary(self.task(), 0, None, None, 5)
        row["objective"] = "An intentionally long description. " * 40
        self.assertTrue(all(len(line) <= 110 for line, _, _ in board.detail_lines(row, 320)))
        self.assertTrue(all(len(line) <= 120 for line, _, _ in board.controller_lines({"status": "idle", "output": row["objective"]}, 320)))

    def test_common_record_shows_work_and_next_actor_without_review_metadata(self):
        for mode in ("development", "reviewer-only", "delegated-work", "workspace-only"):
            task = {"task_id": "simple", "mode": mode, "state": {
                "name": "active", "summary": "Author fixing findings", "next_role": "author",
                "next_action": "Apply the selected fix", "attention_required": False}}
            row = board.task_summary(task, 0, None, None, 5)
            self.assertEqual(board.task_stage(row), "Author fixing findings")
            self.assertEqual(board.task_next(row), "Author")
            self.assertEqual(row["color"], 2)
            self.assertEqual(board.detail_lines(row, 100)[0], ("NEXT: Apply the selected fix", 0, []))

    def test_obsolete_counters_do_not_change_display(self):
        task = self.task()
        before = board.task_summary(task, 0, None, None, 5)
        task.update(scope={"version": 50}, review={"rounds_this_scope": 99, "rounds_total": 999},
                    limits={"max_rounds_total": 6})
        self.assertEqual(before, board.task_summary(task, 0, None, None, 5))

    def test_text_snapshot_distinguishes_worker_steps_from_human_actions(self):
        task = {"task_id": "simple", "state": {"name": "active", "next_role": "author",
                "next_action": "Apply the fix"}}
        for attention in (False, True):
            task["state"]["attention_required"] = attention
            row = board.task_summary(task, 0, None, None, 5)
            with patch.object(board, "snapshot", return_value=([row], [])), patch.object(
                board.sys, "argv", ["board", "--tasks", "/unused", "--once", "--offline"]
            ), patch("builtins.print") as output:
                board.main()
            lines = [call.args[0] for call in output.call_args_list]
            label = "YOUR ACTION" if attention else "NEXT"
            self.assertIn(f"  {label}: Apply the fix", lines)
            self.assertEqual(any("YOUR ACTION:" in line for line in lines), attention)

    def test_complete_is_green_but_explicit_human_attention_wins(self):
        task = {"task_id": "simple", "state": {"name": "complete", "summary": "Ready on GitHub"}}
        row = board.task_summary(task, 0, None, None, 5)
        self.assertEqual(row["color"], 3)
        self.assertEqual(board.task_next(row), "—")
        task["state"].update(attention_required=True, attention_reason="Confirm the changed scope")
        row = board.task_summary(task, 0, None, None, 5)
        self.assertEqual(row["color"], 1)
        self.assertEqual(board.task_next(row), "You")
        self.assertEqual(row["action"], "Confirm the changed scope")

    def test_legacy_completed_handoff_stays_green_without_record_migration(self):
        for stage in ("ready-for-team-review", "delegated-complete", "review-complete"):
            task = self.task(stage)
            task["state"].update(attention_required=True, attention_reason="Human handoff")
            row = board.task_summary(task, 0, None, None, 5)
            self.assertEqual(row["color"], 3)

    def test_common_template_parses_and_renders_without_optional_sections(self):
        path = Path(__file__).parents[3] / "skills/orchestrating-development/assets/task-record.yaml"
        task = board.yaml.safe_load(path.read_text())
        task.pop("development_target")
        row = board.task_summary(task, 0, None, None, 5)
        self.assertEqual(row["color"], 2)
        self.assertEqual(row["prs"], [])

    def test_ready_candidate_remains_a_human_decision_for_legacy_records(self):
        row = board.task_summary(self.task("ready-candidate"), 0, None, None, 5)
        self.assertEqual(row["color"], 1)
        self.assertEqual(board.task_next(row), "You")
        self.assertEqual(row["action"], "Authorize reviewer finalization.")

    def test_task_frame_has_matching_corners_and_separate_scroll_rail(self):
        for width in (40, 140):
            screen = Mock()
            board.draw_task_frame(screen, width, 5, 9, 10, "Tasks 6–10 of 10")
            calls = [call.args for call in screen.addnstr.call_args_list]
            self.assertEqual(calls[0][2][0], "┌")
            self.assertEqual(calls[0][2][-1], "┐")
            self.assertEqual(len(calls[0][2]), width - 1)
            self.assertNotIn("…", calls[0][2])
            self.assertEqual(calls[-1], (11, 0, "└" + "─" * (width - 3) + "┘", width - 1))
            self.assertIn((10, width - 2, "█", 1), calls)

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

    def run_display(self, executor, keys, size=(38, 140)):
        screen = Mock()
        screen.getmaxyx.return_value = size
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
        executor.submit.assert_called_once_with(board.board_snapshot, Path("/unused/tasks"), True, "", None)
        self.assertEqual(screen.getch.call_count, 4)

    def test_failed_background_refresh_is_visible_without_crashing(self):
        executor = Mock()
        pending = Future()
        pending.set_exception(OSError("inventory unavailable"))
        executor.submit.return_value = pending
        screen = self.run_display(executor, [-1, ord("q")])
        self.assertTrue(any("Updates need attention" in str(call) for call in screen.addnstr.call_args_list))

    def test_empty_board_has_general_message_and_controller_actions(self):
        executor = Mock()
        pending = Future()
        pending.set_result(([], [], {"status": "idle", "output": "What would you like to work on?"}))
        executor.submit.return_value = pending
        with patch.object(board, "compose", return_value="Draft saved.") as compose:
            screen = self.run_display(executor, [-1, ord("m"), ord("q")])
        self.assertIsNone(compose.call_args.args[2])
        output = " ".join(str(call) for call in screen.addnstr.call_args_list)
        for text in ("Open orchestrator", "General / new task", "What would you like to work on?"):
            self.assertIn(text, output)

    def test_navigation_uses_exact_workspace_id(self):
        args = SimpleNamespace(offline=False)
        row = board.task_summary(self.task(), 0, None, None, 5)
        reply = board.json.dumps({"result": {"workspace": {"workspace_id": "w1"}}})
        with patch.dict(board.os.environ, {"HERDR_ENV": "1"}), patch.object(
            board, "herdr_call", side_effect=[reply, "{}"]
        ) as call:
            self.assertIn("Opened", board.open_target(args, row))
        self.assertEqual([c.args for c in call.call_args_list], [("workspace", "get", "w1"), ("workspace", "focus", "w1")])

    def test_orchestrator_navigation_rejects_wrong_control_workspace(self):
        args = SimpleNamespace(offline=False)
        for workspace in ("control", "other"):
            reply = board.json.dumps({"result": {"agent": {"workspace_id": workspace, "pane_id": "control:p1"}}})
            with patch.dict(board.os.environ, {"HERDR_ENV": "1", "HERDR_WORKSPACE_ID": "control"}), patch.object(
                board, "herdr_call", side_effect=[reply, "{}"]
            ) as call:
                result = board.open_target(args)
            self.assertEqual(call.call_count, 2 if workspace == "control" else 1)
            if workspace == "control":
                self.assertEqual(call.call_args.args, ("agent", "focus", "control:p1"))
            else:
                self.assertIn("Could not open", result)

    def test_missing_workspace_is_not_recreated(self):
        args = SimpleNamespace(offline=False)
        row = board.task_summary(self.task(), 0, None, None, 5)
        with patch.dict(board.os.environ, {"HERDR_ENV": "1"}), patch.object(
            board, "herdr_call", side_effect=OSError("workspace not found")
        ) as call:
            self.assertIn("Could not open", board.open_target(args, row))
        call.assert_called_once_with("workspace", "get", "w1")

    def test_controller_preview_is_bounded_and_read_only(self):
        agent = {"workspace_id": "control", "pane_id": "control:p1", "agent_status": "blocked"}
        reply = board.json.dumps({"result": {"agent": agent}})
        with patch.dict(board.os.environ, {"HERDR_ENV": "1", "HERDR_WORKSPACE_ID": "control"}), patch.object(
            board, "herdr_call", side_effect=[reply, "x" * 40000]
        ) as call:
            result = board.controller_snapshot()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(len(result["output"]), 32000)
        self.assertEqual(call.call_args.args, ("agent", "read", "control:p1", "--source", "recent-unwrapped", "--lines", "120"))
        self.assertIn("Needs you", board.controller_lines(result, 80)[0][0])

    def test_worker_preview_is_bounded_and_agent_neutral(self):
        row = board.task_summary(self.task(), 0, None, None, 5)
        for kind in ("codex", "claude", "other"):
            agent = {"workspace_id": "w1", "pane_id": "w1:p2", "name": "reviewer",
                     "agent": kind, "agent_status": "done"}
            with patch.dict(board.os.environ, {"HERDR_ENV": "1"}), patch.object(
                board, "herdr_call", side_effect=[board.json.dumps({"result": {"agent": agent}}), "x" * 40000]
            ) as call:
                result = board.worker_snapshot(row)
            self.assertEqual(result["role"], "reviewer")
            self.assertEqual(len(result["output"]), 32000)
            self.assertEqual(call.call_count, 2)
            self.assertEqual(call.call_args.args, ("agent", "read", "w1:p2", "--source", "recent-unwrapped", "--lines", "120"))

    def test_worker_preview_does_not_read_a_reused_or_missing_identity(self):
        row = board.task_summary(self.task(), 0, None, None, 5)
        for agent in ({"workspace_id": "other", "pane_id": "other:p1", "name": "reviewer"},
                      {"workspace_id": "w1", "pane_id": "w1:p1", "name": "unrelated"},
                      {"workspace_id": "w1", "name": "reviewer"}):
            with patch.dict(board.os.environ, {"HERDR_ENV": "1"}), patch.object(
                board, "herdr_call", return_value=board.json.dumps({"result": {"agent": agent}})
            ) as call:
                result = board.worker_snapshot(row)
            self.assertEqual(result["status"], "unavailable")
            self.assertEqual(call.call_count, 1)
        with patch.object(board, "herdr_call") as call:
            self.assertEqual(board.worker_snapshot(row, offline=True)["status"], "offline")
        call.assert_not_called()

    def test_refresh_reads_only_selected_workspace_and_role(self):
        rows = [board.task_summary(dict(self.task(), task_id=str(i)), 0, None, None, 5) for i in range(10)]
        with patch.object(board, "snapshot", return_value=(rows, [])), patch.object(
            board, "controller_snapshot", return_value={}
        ), patch.object(board, "worker_snapshot", return_value={"output": "Selected reply"}) as read:
            result, _, _ = board.board_snapshot(Path("/unused"), False, "5", "reviewer")
            read.assert_called_once_with(rows[5], "reviewer", False)
            self.assertEqual([row["id"] for row in result if "conversation" in row], ["5"])
            read.reset_mock()
            board.board_snapshot(Path("/unused"), False, "")
            read.assert_not_called()

    def test_workspace_conversation_and_details_keep_message_routing(self):
        executor = Mock()
        pending = Future()
        row = board.task_summary(self.task(), 0, None, None, 5)
        row["objective"] = "Task purpose remains available."
        row["conversation"] = {"role": "reviewer", "status": "done", "output": "Please clarify the boundary case."}
        pending.set_result(([row], [], {"status": "idle", "output": "Orchestrator reply"}))
        executor.submit.return_value = pending
        with patch.object(board, "compose", return_value="Draft saved") as compose, patch.object(
            board, "mouse_event", return_value=("select", 16, 8, 0)
        ), patch.object(board, "open_target") as navigate:
            screen = self.run_display(executor, [-1, board.curses.KEY_MOUSE, ord("m"), ord("i"), ord("q")])
        navigate.assert_not_called()
        rendered = " ".join(str(call) for call in screen.addnstr.call_args_list)
        self.assertIn("Please clarify the boundary case.", rendered)
        self.assertIn("Task purpose remains available.", rendered)
        self.assertIn("Details", rendered)
        self.assertLess(rendered.index("Task purpose remains available."), rendered.index("Please clarify the boundary case."))
        self.assertEqual(compose.call_args.args[2]["id"], row["id"])

    def test_message_box_grows_then_caps_without_losing_text(self):
        for height, width in ((24, 60), (38, 88), (60, 200)):
            short = board.message_layout("Hi", height, width)
            multiline = board.message_layout("line\n" * 7, height, width)
            long = board.message_layout("line\n" * 100, height, width)
            self.assertEqual(short[3], 3)
            self.assertGreaterEqual(multiline[3], short[3])
            self.assertLessEqual(long[3], 12)
            self.assertGreaterEqual(long[2], 0)
            self.assertEqual(long[2] + long[3] + 5, height)
            self.assertEqual(len(long[0]), 101)
            screen = Mock()
            screen.getmaxyx.return_value = (height, width)
            board.draw_message_box(screen, None, "line\n" * 100)
            for call in screen.addnstr.call_args_list:
                y, x, text, count, *_ = call.args
                self.assertTrue(0 <= y < height)
                self.assertLessEqual(x + min(len(text), count), width)
        self.assertGreater(board.message_layout("x\n" * 7, 60, 88)[3], 3)
        self.assertGreater(board.message_layout("x" * 600, 60, 88)[3], 3)

    def test_grown_editor_click_and_send_preserve_exact_multiline_message(self):
        with tempfile.TemporaryDirectory() as root:
            args = SimpleNamespace(tasks=Path(root) / "tasks", offline=False)
            screen = Mock()
            screen.getmaxyx.return_value = (60, 88)
            message = "first\n" * 20
            board.save_draft(board.draft_path(args, None), message)
            screen.get_wch.side_effect = [board.curses.KEY_MOUSE, "\r"]
            top = board.message_layout(message, 60, 88)[2]
            with patch.object(board.curses, "curs_set"), patch.object(
                board, "mouse_event", return_value=("select", 4, top + 1, 0)
            ), patch.object(board, "send_message", return_value=(True, "Delivered")) as send:
                self.assertEqual(board.compose(screen, args, None, inline=True), "Delivered")
            send.assert_called_once_with(args, None, message)
            screen.dupwin.return_value.overwrite.assert_called()

    def test_navigation_buttons_have_distinct_color_and_remain_last(self):
        screen = Mock()
        screen.getmaxyx.return_value = (60, 88)
        with patch.object(board.curses, "has_colors", return_value=True), patch.object(
            board.curses, "color_pair", side_effect=lambda number: number
        ) as colors:
            hits, _ = board.draw_actions(screen, 8, 88, [
                ("info", "Details"), ("role-author", "Author"), ("role-reviewer", "Reviewer"),
                ("workspace", "Open workspace ↗")], "info")
        self.assertEqual(hits[-1][-1], "workspace")
        self.assertEqual([call.args[0] for call in colors.call_args_list], [8, 9, 9, 11])

    def test_actions_wrap_and_hit_targets_do_not_overlap(self):
        for width in (40, 80, 140):
            screen = Mock()
            screen.getmaxyx.return_value = (38, width)
            actions, bottom = board.draw_actions(screen, 8, width,
                [("task", "Tasks"), ("controller", "Orchestrator"), ("workspace", "Open workspace"), ("open-controller", "Open orchestrator")], "controller")
            self.assertEqual(len(actions), 4)
            for y, left, right, _ in actions:
                self.assertLess(y, bottom)
                self.assertTrue(0 < left < right <= width - 1)
            for i, (y, left, right, _) in enumerate(actions):
                for other_y, other_left, other_right, _ in actions[i + 1:]:
                    self.assertTrue(y != other_y or right <= other_left or other_right <= left)

    def test_buttons_have_filled_styles_without_brackets(self):
        screen = Mock()
        screen.getmaxyx.return_value = (38, 140)
        with patch.object(board.curses, "has_colors", return_value=True), patch.object(
            board.curses, "color_pair", side_effect=lambda number: number
        ):
            board.draw_actions(screen, 8, 140, [("task", "Tasks"), ("controller", "Orchestrator")], "controller")
        calls = [call.args for call in screen.addnstr.call_args_list]
        self.assertTrue(all("[" not in args[2] for args in calls))
        self.assertEqual(calls[1][-1], 8 | board.curses.A_BOLD)
        self.assertEqual(calls[0][-1], 9 | board.curses.A_BOLD)

    def test_recap_heading_is_highlighted_without_dropping_prose(self):
        controller = {"status": "idle", "output": "Tool output\n" + "─" * 100 + "\n\n─ Conversation recap ───\n\nA useful summary.\n\n\n› Your prompt"}
        lines = board.controller_lines(controller, 40)
        self.assertIn(("CONVERSATION RECAP", 10, []), lines)
        output = "\n".join(line for line, _, _ in lines)
        for text in ("Tool output", "A useful summary.", "› Your prompt"):
            self.assertIn(text, output)
        self.assertNotIn("\n\n\n", output)

    def test_compact_table_keeps_next_actor_and_whole_pr_numbers(self):
        row = board.task_summary(self.task(), 0, None, None, 5)
        row.update(label="A very long workspace name " * 3, stage="A lengthy status " * 3,
                   roles="Reviewer", prs=["https://github.com/team/repo/pull/123456"])
        for width in (52, 60, 80, 99, 100, 140, 300):
            line = board.table_line(row, width, 9)
            self.assertLessEqual(len(line), width)
            self.assertIn("#123456", line)
            self.assertIn("Reviewer", line)
        details = "\n".join(line for line, _, _ in board.detail_lines(row, 80, info=True))
        self.assertIn("A very long workspace name", details)

    def test_pr_overflow_is_explicit_and_never_links_partial_ids(self):
        row = {"prs": [f"https://github.com/team/repo/pull/{number}" for number in (123456, 234567, 345678, 456789)]}
        for width in (9, 12, 20, 40):
            text, spans = board.pr_cell(row, width)
            self.assertLessEqual(len(text), width)
            visible = 0
            for left, right, url in spans:
                if url:
                    self.assertEqual(text[left:right], "#" + url.rsplit("/", 1)[-1])
                    visible += 1
                else:
                    self.assertEqual(text[left:right], f"+{len(row['prs']) - visible}")
            if visible < len(row["prs"]):
                self.assertIsNone(spans[-1][2])

    def test_overflow_click_opens_full_pr_details_in_narrow_pane(self):
        executor = Mock()
        pending = Future()
        row = board.task_summary(self.task(), 0, None, None, 5)
        row["prs"] = [f"https://github.com/team/repo/pull/{n}" for n in (123456, 234567, 345678, 456789)]
        pending.set_result(([row], [], {"status": "idle", "output": "Ready"}))
        executor.submit.return_value = pending
        width = 88
        pr_width = min(width // 3, len(", ".join(label for label, _ in board.pr_labels(row))))
        sizes = board.columns(width - 8, pr_width)
        start = 5 + sum(sizes) + 2 * sum(size > 0 for size in sizes)
        _, spans = board.pr_cell(row, pr_width)
        with patch.object(board, "mouse_event", return_value=("select", start + spans[-1][0], 5, 0)), patch.object(board, "open_pr") as open_pr:
            screen = self.run_display(executor, [-1, board.curses.KEY_MOUSE, ord("q")], (60, width))
        open_pr.assert_not_called()
        rendered = " ".join(str(call) for call in screen.addnstr.call_args_list)
        for number in (123456, 234567, 345678, 456789):
            self.assertIn(f"repo#{number}", rendered)

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
        self.assertEqual(command[-1], f"Human message about {row['label']} (w1):\n\n{message}")

    def test_general_message_has_no_task_context_and_its_own_draft(self):
        args = SimpleNamespace(offline=False, tasks=Path("/control/tasks"))
        row = board.task_summary(self.task(), 0, None, None, 5)
        self.assertNotEqual(board.draft_path(args, row), board.draft_path(args, None))
        reply = SimpleNamespace(stdout=board.json.dumps({"result": {"agent": {"workspace_id": "control", "agent_status": "idle"}}}))
        delivered = SimpleNamespace(stdout=board.json.dumps({"result": {"type": "agent_prompted"}}))
        message = "Let's discuss a new task.\nDo not start yet."
        with patch.dict(board.os.environ, {"HERDR_ENV": "1", "HERDR_WORKSPACE_ID": "control"}), patch.object(
            board.subprocess, "run", side_effect=[reply, delivered]
        ) as run:
            self.assertTrue(board.send_message(args, None, message)[0])
        self.assertEqual(run.call_args.args[0][-1], message)

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
        self.assertEqual("reviewing", row["stage"])
        self.assertIn("Reviewer done → reviewer", row["roles"])
        self.assertIsNone(row["action"])
        self.assertEqual(task["workspace"]["label"], "old-name")

    def test_next_actor_without_legacy_worker_events(self):
        task = self.task("resolving")
        del task["event_recovery"]
        row = board.task_summary(task, 0, None, None, 5)
        self.assertEqual("author", row["next"])
        self.assertEqual("resolving", row["stage"])
        task["state"].update(attention_required=True, attention_reason="Choose findings")
        row = board.task_summary(task, 0, None, None, 5)
        self.assertEqual("you", row["next"])

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
        self.assertEqual([row["id"] for row in rows], ["decision", "passive", "ready"])

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
