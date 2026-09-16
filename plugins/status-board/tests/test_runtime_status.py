"""Live presentation is evidence, not authorization or a workflow state writer."""

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]))
import board


class RuntimeStatusTests(unittest.TestCase):
    def setUp(self):
        self.task = {"task_id": "feature", "workspace": {"id": "w1", "label": "Feature"},
                     "agents": {"author": "author"},
                     "state": {"name": "needs-human", "summary": "Approve initial plan", "next_action": "Approve plan"}}
        self.agent = {"name": "author", "workspace_id": "w1", "pane_id": "w1:p1", "terminal_id": "term1",
                      "agent_status": "working", "agent_session": {"value": "session1"}}

    def row(self, status="working", agents=None):
        return board.task_summary(self.task, 0, [{"workspace_id": "w1"}],
                                  agents if agents is not None else [dict(self.agent, agent_status=status)], 10)

    def test_live_start_overrides_old_approval_without_mutating_task(self):
        before = deepcopy(self.task)
        row = self.row()
        self.assertEqual((row["color"], board.task_stage(row), board.task_next(row)), (2, "Agent working", "Author"))
        self.assertNotIn("Approve", row["action"])
        self.assertIn("Approve", row["runtime_note"])
        self.assertEqual(self.task, before)

    def test_restart_retains_observed_work_until_record_is_reconciled(self):
        with tempfile.TemporaryDirectory() as root:
            tasks = Path(root) / "tasks"
            viewer = board.ViewerState(tasks)
            viewer.reconcile([self.row()])
            viewer = board.ViewerState(tasks)
            for settled in ("done", "idle"):
                row = self.row(settled)
                viewer.reconcile([row])
                self.assertEqual(row["color"], 0)
                self.assertEqual(board.task_stage(row), "Awaiting status update")
            self.task["state"] = {"name": "complete", "summary": "Review passed and PR ready"}
            row = self.row("idle")
            viewer.reconcile([row])
            self.assertEqual(row["color"], 3)
            self.assertEqual(viewer.observations, {})
            self.assertFalse(tasks.exists())  # Only private viewer state is written.

    def test_direct_human_resume_does_not_reuse_old_completion(self):
        self.task["state"] = {"name": "complete", "summary": "Original request finished"}
        with tempfile.TemporaryDirectory() as root:
            viewer = board.ViewerState(Path(root) / "tasks")
            row = self.row()
            viewer.reconcile([row])
            self.assertEqual(row["color"], 2)
            row = self.row("idle")
            viewer.reconcile([row])
            self.assertEqual(row["color"], 0)

    def test_unavailable_inventory_keeps_pending_reconciliation(self):
        with tempfile.TemporaryDirectory() as root:
            viewer = board.ViewerState(Path(root) / "tasks")
            viewer.reconcile([self.row()])
            row = board.task_summary(self.task, 0, None, None, 10)
            viewer.reconcile([row])
            self.assertEqual(row["color"], 0)
            self.assertIn("unavailable", board.task_stage(row))
            self.assertIn("feature", viewer.observations)

    def test_duplicate_wrong_workspace_and_pinned_replacements_are_unconfirmed(self):
        for agents in ([self.agent, self.agent], [dict(self.agent, workspace_id="w2")], []):
            with self.subTest(agents=agents):
                self.assertEqual(self.row(agents=agents)["color"], 0)
        self.task["role_sessions"] = {"author": {"session_id": "previous"}}
        self.assertEqual(self.row()["color"], 0)

    def test_observed_identity_change_requires_reconciliation(self):
        with tempfile.TemporaryDirectory() as root:
            viewer = board.ViewerState(Path(root) / "tasks")
            viewer.reconcile([self.row()])
            self.agent["agent_session"] = {"value": "replacement"}
            row = self.row()
            viewer.reconcile([row])
            self.assertEqual((row["color"], board.task_stage(row)), (0, "Agent identity changed"))
            self.task["role_sessions"] = {"author": {"session_id": "replacement"}}
            row = self.row()
            viewer.reconcile([row])
            self.assertEqual(row["color"], 2)

    def test_actual_block_takes_precedence_over_other_worker_activity(self):
        self.task["agents"]["reviewer"] = "reviewer"
        reviewer = dict(self.agent, name="reviewer", pane_id="w1:p2", agent_status="blocked")
        row = self.row(agents=[self.agent, reviewer])
        self.assertEqual(row["color"], 1)
        self.assertIn("reviewer", row["action"])
        self.assertNotIn("Approve plan", row["action"])


if __name__ == "__main__":
    unittest.main()
