import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import board
import task_records


class TaskRecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.task = {"task_id": "example", "state": {"name": "complete"},
                     "workspace": {"id": "task"},
                     "agents": {"worker": "author"},
                     "role_sessions": {"worker": {"pane": "task:p1", "native_session_id": "session"}},
                     "evidence": {"custom_future_field": ["preserve", "this"]}}
        self.source = self.root / "candidate.json"

    def candidate(self, value=None):
        self.source.write_text(json.dumps(self.task if value is None else value))
        return self.source

    def test_atomic_save_preserves_flexible_evidence_and_supports_yaml(self):
        destination = self.root / "tasks/example.yaml"
        task_records.save(destination, self.candidate())
        self.assertEqual(task_records.load(destination, canonical=True), self.task)
        self.assertEqual(board.read_tasks(destination.parent)[1], [])

    def test_invalid_candidate_leaves_existing_record_unchanged(self):
        destination = self.root / "example.json"
        task_records.save(destination, self.candidate())
        before = destination.read_bytes()
        for change in ({"task_id": None}, {"agents": "author"}, {"agent": {"name": "author"}},
                       {"agents": {"worker": None}}, {"role_sessions": {"worker": "session"}},
                       {"role_sessions": {"worker": {"pane": 42}}}, {"pull_requests": [42]},
                       {"state": {"name": "planning"}}, {"state": {"name": "needs-human"}},
                       {"agent_sessions": {"worker": "session"}}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    task_records.save(destination, self.candidate(dict(self.task, **change)))
                self.assertEqual(destination.read_bytes(), before)

    def test_cannot_replace_another_task(self):
        destination = self.root / "example.json"
        task_records.save(destination, self.candidate())
        with self.assertRaisesRegex(ValueError, "identity differs"):
            task_records.save(destination, self.candidate(dict(self.task, task_id="another")))
        self.assertEqual(task_records.load(destination), self.task)

    def test_explicitly_correcting_id_alias_preserves_identity(self):
        destination = self.root / "example.json"
        original = dict(self.task)
        original["id"] = original.pop("task_id")
        destination.write_text(json.dumps(original))
        task_records.save(destination, self.candidate())
        self.assertEqual(task_records.load(destination), self.task)

    def test_record_with_singular_agent_cannot_silently_lose_its_watch(self):
        original = dict(self.task, agent={"name": "author"})
        original.pop("agents")
        self.candidate(original)
        tasks, warnings = board.read_tasks(self.root)
        self.assertFalse(tasks)
        self.assertIn("use agents", warnings[0])

    def test_legacy_states_remain_readable_but_new_saves_use_three_states(self):
        self.candidate(dict(self.task, state={"name": "ready-for-team-review"}))
        self.assertEqual(len(board.read_tasks(self.root)[0]), 1)
        with self.assertRaisesRegex(ValueError, "state.name"):
            task_records.save(self.root / "example.json", self.source)

    def test_orphan_session_role_is_rejected(self):
        task = copy.deepcopy(self.task)
        task["role_sessions"]["reviewer"] = {"pane": "task:p2"}
        with self.assertRaisesRegex(ValueError, "agents entry"):
            task_records.save(self.root / "example.json", self.candidate(task))

    def test_assigned_agent_requires_workspace_for_live_matching(self):
        with self.assertRaisesRegex(ValueError, "workspace.id"):
            task_records.validate(dict(self.task, workspace={}), canonical=True)

    def test_pr_metadata_is_preserved_not_reduced_to_urls(self):
        task = dict(self.task, pull_requests=[{"url": "https://github.com/owner/repo/pull/1",
                                            "state": "MERGED", "head": "exact-head", "number": 1}])
        destination = self.root / "example.json"
        task_records.save(destination, self.candidate(task))
        self.assertEqual(task_records.load(destination), task)

    def test_json_writer_does_not_require_optional_dashboard_dependencies(self):
        self.candidate()
        destination = self.root / "example.json"
        with patch.dict(sys.modules, yaml=None):
            task_records.save(destination, self.source)
            self.assertEqual(task_records.load(destination), self.task)
            source = self.root / "yaml-candidate.yaml"
            source.write_text("task_id: example\nstate: {name: complete}\n")
            with self.assertRaisesRegex(ValueError, "use JSON"):
                task_records.load(source)

    def test_cli_checks_all_files_without_mutating_and_saves_valid_candidate(self):
        script = Path(__file__).parents[3] / "scripts/task-record.py"
        self.candidate()
        bad = self.root / "bad.yaml"
        bad.write_text("id: wrong\nstate: {name: complete}\n")
        result = subprocess.run([sys.executable, str(script), "check", str(self.root)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("bad.yaml", result.stderr)
        self.assertIn("task_id", result.stderr)
        self.assertEqual(bad.read_text(), "id: wrong\nstate: {name: complete}\n")
        result = subprocess.run([sys.executable, str(script), "save", str(self.root / "saved.json"),
                                 "--input", str(self.source)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(task_records.load(self.root / "saved.json"), self.task)


if __name__ == "__main__":
    unittest.main()
