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
