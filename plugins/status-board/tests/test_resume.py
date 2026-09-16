import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import resume


class ResumeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.tasks = self.root / "tasks"
        self.tasks.mkdir()
        self.config = self.root / "plugin-config"
        env = patch.dict(os.environ, HERDR_SOCKET_PATH="/test/herdr.sock", HERDR_PANE_ID="w1:p2")
        env.start()
        self.addCleanup(env.stop)
        self.pane = {"pane_id": "w1:p2", "workspace_id": "w1", "terminal_id": "restored-terminal"}
        self.info = {"pane_id": "w1:p2", "shell_pid": 10, "foreground_process_group_id": 10,
                     "foreground_processes": [{"pid": 10, "argv": ["/bin/bash"]}]}
        self.calls = []
        self.launch_starts = True
        caller = patch.object(resume, "call", side_effect=self.call)
        caller.start()
        self.addCleanup(caller.stop)
        sleeper = patch.object(resume.time, "sleep")
        sleeper.start()
        self.addCleanup(sleeper.stop)
        self.registration = resume.register(self.tasks, 5, self.config)
        self.record_path = self.registration[0]

    def call(self, *args):
        self.calls.append(args)
        if args[:2] == ("pane", "get"):
            return json.dumps({"result": {"pane": self.pane}})
        if args == ("api", "snapshot"):
            return json.dumps({"result": {"snapshot": {"panes": [self.pane] if self.pane else []}}})
        if args[:2] == ("pane", "process-info"):
            return json.dumps({"result": {"process_info": self.info}})
        if args[:2] == ("pane", "run"):
            if self.launch_starts:
                self.info.update(foreground_process_group_id=20, foreground_processes=[{
                    "pid": 20, "argv": self.record()["argv"]}])
            return ""
        if args[:2] == ("notification", "show"):
            return ""
        self.fail(f"Unexpected command: {args}")

    def record(self):
        return json.loads(self.record_path.read_text())

    def launches(self):
        return [call for call in self.calls if call[:2] == ("pane", "run")]

    def test_restart_reuses_saved_pane_and_exact_venv_without_focus_or_rebinding(self):
        self.assertFalse(resume.restore(self.config))
        self.assertEqual(len(self.launches()), 1)
        _, _, pane, command = self.launches()[0]
        self.assertEqual(pane, "w1:p2")
        argv = resume.shlex.split(command)
        self.assertEqual(argv[:3], ["env", "-u", "STAGEHAND_CONTROLLER_PANE"])
        self.assertEqual(argv[3:], self.record()["argv"])
        self.assertEqual(argv[3], os.path.abspath(sys.executable))
        self.assertFalse(resume.restore(self.config))
        self.assertEqual(len(self.launches()), 1)

    def test_live_handoff_preserves_existing_board_even_with_relative_script(self):
        script = Path(self.record()["argv"][1])
        self.info.update(foreground_process_group_id=20, foreground_processes=[{
            "argv": [sys.executable, "board.py"], "cwd": str(script.parent)}])
        self.assertFalse(resume.restore(self.config))
        self.assertFalse(self.launches())

    def test_intentional_close_and_explicit_optout_disable_restore(self):
        resume.close(self.registration)
        self.assertFalse(resume.restore(self.config))
        self.assertFalse(self.launches())
        resume.register(self.tasks, 5, self.config, enabled=False)
        self.assertFalse(resume.restore(self.config))
        self.assertFalse(self.launches())

    def test_old_instance_cannot_disable_new_viewer(self):
        newer = resume.register(self.tasks, 5, self.config)
        resume.close(self.registration)
        self.assertTrue(self.record()["enabled"])
        resume.close(newer)
        self.assertFalse(self.record()["enabled"])

    def test_closed_pane_is_retired_not_recreated(self):
        self.pane = None
        self.assertFalse(resume.restore(self.config))
        self.assertFalse(self.record()["enabled"])
        self.assertFalse(self.launches())

    def test_other_session_is_untouched(self):
        with patch.dict(os.environ, HERDR_SOCKET_PATH="/test/other.sock"):
            self.assertFalse(resume.restore(self.config))
        self.assertFalse(self.launches())

    def test_occupied_pane_is_not_given_input_and_failure_is_visible(self):
        self.info["foreground_process_group_id"] = 99
        with patch.object(resume.sys, "stderr"):
            failures = resume.restore(self.config)
        self.assertIn("occupied", failures[0])
        self.assertFalse(self.launches())
        self.assertTrue(any(call[:2] == ("notification", "show") for call in self.calls))

    def test_failed_launch_does_not_loop_on_same_terminal(self):
        self.launch_starts = False
        with patch.object(resume.sys, "stderr"):
            self.assertTrue(resume.restore(self.config))
        self.assertEqual(len(self.launches()), 1)
        resume.restore(self.config)
        self.assertEqual(len(self.launches()), 1)
        self.pane["terminal_id"] = "next-server-terminal"
        with patch.object(resume.sys, "stderr"):
            resume.restore(self.config)
        self.assertEqual(len(self.launches()), 2)

    def test_command_quotes_paths_and_never_interpolates_task_text(self):
        tasks = self.root / "tasks with 'quotes' and $dollars"
        tasks.mkdir()
        resume.close(self.registration)
        self.registration = resume.register(tasks, 5, self.config)
        self.record_path = self.registration[0]
        self.assertFalse(resume.restore(self.config))
        self.assertEqual(resume.shlex.split(self.launches()[0][3])[6], str(tasks))
