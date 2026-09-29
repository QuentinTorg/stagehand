"""Exercise worker lifetime and file locks without a live Herdr session."""

import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_agent_wake import wake, SCRIPT


class ReminderProcessTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.config = self.root / "config"
        self.config.mkdir()
        self.socket = self.root / "herdr.sock"
        self.socket.touch()
        self.source = {"pane_id": "w2:p1", "workspace_id": "w2", "name": "worker",
                       "agent_status": "working", "agent_session": {"kind": "id", "value": "worker-session"}}
        self.watch_path = self.root / "watches" / ("a" * 32 + ".json")
        self.watch = {"id": "a" * 32, "key": "task", "metadata": {}, "pane_id": "w2:p1",
                      "workspace_id": "w2", "workspace_label": "feature", "agent_name": "worker",
                      "session": self.source["agent_session"], "persistent": True, "state": "armed",
                      "last_status": "working", "reminder_due": time.time() - 1}
        self.entry = {"root": str(self.root), "target": "controller", "socket": str(self.socket),
                      "reminder_seconds": 900}
        wake._atomic_json(self.config / "config.json", {"consumers": [self.entry]})
        wake._atomic_json(self.watch_path, self.watch)
        state = {"source": self.source, "enabled": True, "plugin_root": str(SCRIPT.parent)}
        wake._atomic_json(self.root / "fake.json", state)
        env = patch.dict(os.environ, HERDR_PLUGIN_CONFIG_DIR=str(self.config), HERDR_SOCKET_PATH=str(self.socket),
                         HERDR_BIN_PATH=str(Path(__file__).parent / "fixtures" / "reminder-herdr.py"),
                         FAKE_HERDR_STATE=str(self.root / "fake.json"), FAKE_HERDR_CALLS=str(self.root / "calls.jsonl"))
        env.start()
        self.addCleanup(env.stop)
        self.children = []
        self.addCleanup(self.stop_children)

    def stop_children(self):
        for child in self.children:
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=5)

    def launch(self):
        popen = subprocess.Popen
        def capture(*args, **kwargs):
            child = popen(*args, **kwargs)
            self.children.append(child)
            return child
        with patch.object(wake.subprocess, "Popen", side_effect=capture):
            wake._ensure_timer(self.root)

    def until(self, predicate):
        deadline = time.monotonic() + 8
        while not predicate():
            if time.monotonic() > deadline:
                self.fail("Reminder worker did not reach expected state")
            time.sleep(.03)

    def calls(self):
        path = self.root / "calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_real_worker_is_singleton_delivers_once_and_exits_when_idle(self):
        self.launch()
        self.launch()
        self.assertEqual(len(self.children), 1)
        self.until(lambda: any(call[:2] == ["agent", "prompt"] for call in self.calls()))
        self.watch.update(last_status="idle")
        self.watch.pop("reminder_due")
        wake._atomic_json(self.watch_path, self.watch)
        self.children[0].wait(timeout=8)
        self.assertEqual(self.children[0].returncode, 0)
        self.launch()
        self.assertEqual(len(self.children), 1)  # Idle hooks never launch a timer.
        self.assertEqual(sum(call[:2] == ["agent", "prompt"] for call in self.calls()), 1)

    def test_dead_worker_releases_lock_and_recovery_does_not_redeliver(self):
        self.launch()
        self.until(lambda: any(call[:2] == ["agent", "prompt"] for call in self.calls()))
        self.children[0].terminate()
        self.children[0].wait(timeout=5)
        self.launch()
        self.assertEqual(len(self.children), 2)
        # Restored schedule is in the future; the worker sleeps without API calls.
        calls = self.calls()
        time.sleep(.15)
        self.assertEqual(self.calls(), calls)
        self.watch_path.unlink()
        self.children[1].wait(timeout=8)

    def test_disabled_or_relinked_plugin_exits_without_prompt(self):
        for change in ({"enabled": False}, {"plugin_root": "/another/checkout"}):
            with self.subTest(change=change):
                state = {"source": self.source, "enabled": True, "plugin_root": str(SCRIPT.parent), **change}
                wake._atomic_json(self.root / "fake.json", state)
                self.launch()
                self.children[-1].wait(timeout=5)
                self.assertEqual(self.children[-1].returncode, 0)
        self.assertFalse(any(call[:2] == ["agent", "prompt"] for call in self.calls()))

    def test_timer_checks_no_api_between_deadlines_and_releases_on_socket_change(self):
        self.watch["reminder_due"] = time.time() + 900
        wake._atomic_json(self.watch_path, self.watch)
        lock_path = self.root / "timer-test.lock"
        with lock_path.open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            args = SimpleNamespace(state_root=str(self.root), lock_fd=os.dup(lock.fileno()), socket_identity="original")
            with patch.object(wake, "_socket_identity", side_effect=["original", "replacement"]), patch.object(
                wake.time, "sleep"
            ) as sleep, patch.object(wake, "_herdr") as api:
                self.assertEqual(wake._timer(args), 0)
            sleep.assert_called_once_with(wake.TIMER_CHECK_SECONDS)
            api.assert_not_called()
            with lock_path.open("a+") as another:
                fcntl.flock(another, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_disabled_interval_foreign_socket_and_no_work_never_spawn(self):
        with patch.object(wake.subprocess, "Popen") as launch:
            with patch.dict(os.environ, HERDR_SOCKET_PATH="/different/session.sock"):
                wake._ensure_timer(self.root)
            self.entry["reminder_seconds"] = 0
            wake._atomic_json(self.config / "config.json", {"consumers": [self.entry]})
            wake._ensure_timer(self.root)
            self.entry["reminder_seconds"] = 900
            wake._atomic_json(self.config / "config.json", {"consumers": [self.entry]})
            self.watch_path.unlink()
            wake._ensure_timer(self.root)
        launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
