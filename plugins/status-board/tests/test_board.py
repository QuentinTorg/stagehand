import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("board", Path(__file__).parents[1] / "board.py")
board = importlib.util.module_from_spec(spec)
spec.loader.exec_module(board)


class BoardTests(unittest.TestCase):
    def task(self, stage="reviewing"):
        return {"task_id": "example", "workspace": {"id": "w1", "label": "old-name"},
                "agents": {"reviewer": "reviewer"}, "state": {"name": stage},
                "review": {"rounds_this_scope": 2}, "event_recovery": {"expected_role": "reviewer"}}

    def test_live_done_does_not_complete_review(self):
        task = self.task()
        rows, action = board.task_lines(task, 0, [{"workspace_id": "w1", "label": "new-name"}],
            [{"name": "reviewer", "workspace_id": "w1", "agent_status": "done"}], 5)
        self.assertEqual(rows[0], ("● new-name", 2))
        self.assertIn("reviewing", rows[1][0])
        self.assertIn("2 reviews completed", rows[1][0])
        self.assertIn("Reviewer done → reviewer", rows[1][0])
        self.assertIsNone(action)
        self.assertEqual(task["workspace"]["label"], "old-name")

    def test_completed_pr_is_green_with_human_handoff(self):
        rows, action = board.task_lines(self.task("ready-for-team-review"), 0, None, None, 5)
        self.assertEqual(rows[0][1], 3)
        self.assertIn("Review the ready PR", action)

    def test_attention_and_missing_identity(self):
        task = self.task()
        task["state"].update(attention_required=True, attention_reason="Approve the plan")
        rows, action = board.task_lines(task, 0, [],
            [{"name": "reviewer", "workspace_id": "other", "agent_status": "working"}], 5)
        self.assertEqual(rows[0][1], 1)
        self.assertIn("workspace missing", rows[0][0])
        self.assertIn("Reviewer missing → you", rows[1][0])
        self.assertIn("Approve the plan", action)

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
