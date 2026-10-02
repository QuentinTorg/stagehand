import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import board
import reporting


def agent(name, pane, workspace="control", sequence=1, status="idle"):
    return {"name": name, "pane_id": pane, "workspace_id": workspace,
            "terminal_id": pane + "-terminal", "agent_status": status, "state_change_seq": sequence,
            "agent_session": {"agent": "codex", "kind": "session", "value": name + "-session"}}


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.tasks = self.root / "control/tasks"
        self.tasks.mkdir(parents=True)
        self.directory = self.root / "reporter"
        self.directory.mkdir()
        self.controller = agent("coordinator", "control:p1")
        self.observer = agent("observer", "control:p2")
        self.author = agent("author", "task:p1", "task")
        self.agents = [self.controller, self.observer, self.author]
        self.task = {"task_id": "example", "objective": "Investigate the fault",
                     "workspace": {"id": "task", "label": "Fault investigation"},
                     "repository": {"name": "demo", "worktree": "/confirmed/worktree"},
                     "agents": {"worker": "author"}, "state": {"name": "working", "summary": "Investigating"}}
        env = patch.dict(os.environ, HERDR_ENV="1", HERDR_SOCKET_PATH="/test/reporter.sock")
        env.start()
        self.addCleanup(env.stop)
        # The execution sandbox supplies /tmp/.git. Hide only that synthetic
        # ancestor so tests can exercise genuine isolated-directory setup.
        exists = Path.exists
        paths = patch.object(Path, "exists", lambda path: False if path == Path("/tmp/.git") else exists(path))
        paths.start()
        self.addCleanup(paths.stop)
        reporting.agent_binding.save(self.tasks.parent / "controller.json", reporting.agent_binding.capture(self.controller))
        reporting.agent_binding.save(self.directory / "binding.json", reporting.agent_binding.capture(self.observer))

    def configure(self):
        config = dict(reporting.DEFAULTS, enabled=True, directory=str(self.directory), socket=os.environ["HERDR_SOCKET_PATH"])
        reporting.write(reporting.config_path(self.tasks), config)
        return config

    def sources(self):
        return reporting.scoped_sources([(self.task, 0)], self.agents, self.controller)

    def record(self):
        return {"task_id": "example", "fingerprint": reporting.fingerprint(self.task, self.sources()),
                "status": "needs-human", "summary": "Proposal ready", "recent_work": "Fault isolated; proposal written.",
                "review_coverage": "Proposal only; no implementation to review.", "next_actor": "you",
                "next_action": "Choose the proposed approach.", "human_action": "Read the proposal and choose an approach.",
                "evidence": ["task:p1 latest answer"]}

    def publish(self):
        record = self.record()
        reporting.write(self.directory / "context.json", {"example": record["fingerprint"]})
        reporting.publish(self.directory, [record])
        return record

    def row(self):
        return board.task_summary(self.task, 0, [{"workspace_id": "task"}], self.agents, 1)

    def test_default_off_has_no_subscriptions_or_display_changes(self):
        row = self.row()
        original = copy.deepcopy(row)
        with patch.object(reporting, "relay") as relay:
            reporting.sync(self.tasks, [(self.task, 0)], self.agents, self.controller)
            reporting.decorate(self.tasks, [(self.task, 0)], self.agents, self.controller, [row])
            reporting.apply_display(row)
        relay.assert_not_called()
        self.assertEqual(row, original)
        self.assertFalse((self.tasks.parent / "reporter.lock").exists())

    def test_scoped_sources_exclude_unrelated_and_wrong_native_sessions(self):
        other = agent("author", "other:p1", "other")
        self.agents.append(other)
        self.assertEqual([a["pane_id"] for _, _, a in self.sources()], ["control:p1", "task:p1"])
        self.task["role_sessions"] = {"worker": {"pane": "task:p1", "native_session_id": "different-session"}}
        self.assertEqual([a["pane_id"] for _, _, a in self.sources()], ["control:p1"])

    def test_fingerprints_bind_intent_identity_and_later_turns(self):
        initial = reporting.fingerprint(self.task, self.sources())
        self.task["objective"] = "Changed human scope"
        self.assertNotEqual(initial, reporting.fingerprint(self.task, self.sources()))
        self.task["objective"] = "Investigate the fault"
        self.author["state_change_seq"] += 1
        self.assertNotEqual(initial, reporting.fingerprint(self.task, self.sources()))
        self.author["state_change_seq"] -= 1
        self.author["agent_session"]["value"] = "replacement"
        self.assertNotEqual(initial, reporting.fingerprint(self.task, self.sources()))

    def test_fresh_report_overlays_then_later_work_falls_back(self):
        self.configure()
        self.publish()
        row = self.row()
        reporting.decorate(self.tasks, [(self.task, 0)], self.agents, self.controller, [row])
        reporting.apply_display(row)
        self.assertEqual((row["status"], row["summary"]), ("needs-human", "Proposal ready"))
        self.author["state_change_seq"] += 1
        self.author["agent_status"] = "working"
        row = self.row()
        before = row["status"], row["summary"]
        reporting.decorate(self.tasks, [(self.task, 0)], self.agents, self.controller, [row])
        reporting.apply_display(row)
        self.assertEqual((row["status"], row["summary"]), before)
        self.assertIn("Previous", row["reporter_note"])

    def test_missing_blocked_or_replaced_reporter_preserves_original_status(self):
        self.configure()
        self.publish()
        for agents in ([self.controller, self.author], [self.controller, dict(self.observer, agent_status="blocked"), self.author]):
            row = self.row()
            reporting.decorate(self.tasks, [(self.task, 0)], agents, self.controller, [row])
            self.assertFalse(row["report_fresh"])
            reporting.apply_display(row)
            self.assertEqual(row["summary"], row["saved_display"]["summary"])

    def test_native_work_and_blockers_cannot_be_hidden_by_a_report(self):
        for native, expected in (("working", "working"), ("blocked", "needs-human")):
            row = self.row()
            report = dict(self.record(), status="complete", human_action="")
            row.update(report=report, report_fresh=True, runtime_states={"worker": native}, action="Inspect worker permission")
            reporting.apply_display(row)
            self.assertEqual(row["status"], expected)
            if native == "blocked":
                self.assertEqual(row["action"], "Inspect worker permission")
            else:
                self.assertEqual(row["next"], "worker")
                self.assertNotEqual(row["summary"], report["summary"])

    def test_publish_validates_entire_batch_and_controls_before_writing(self):
        self.publish()
        before = (self.directory / "reports.json").read_bytes()
        invalid = dict(self.record(), fingerprint="wrong")
        with self.assertRaises(ValueError):
            reporting.publish(self.directory, [self.record(), invalid])
        with self.assertRaises(ValueError):
            reporting.publish(self.directory, [dict(self.record(), recent_work="\x1b[2J")])
        self.assertEqual((self.directory / "reports.json").read_bytes(), before)

    def test_malformed_report_is_visible_and_does_not_break_other_rows(self):
        self.configure()
        reporting.write(self.directory / "reports.json", {"example": {"status": "complete"}})
        row = self.row()
        reporting.decorate(self.tasks, [(self.task, 0)], self.agents, self.controller, [row])
        self.assertIn("Invalid", row["reporter_note"])
        self.assertNotIn("report", row)

    def test_context_includes_confirmed_paths_and_all_pr_hosts(self):
        self.task["pull_requests"] = ["https://github.com/a/b/pull/1", "https://github.company.test/c/d/pull/2"]
        reporting.write(self.tasks / "task.json", self.task)
        reporting.write(self.directory / "connection.json", {"tasks": str(self.tasks), "socket": os.environ["HERDR_SOCKET_PATH"]})
        wake = Mock()
        wake._documents.return_value = []
        with patch.object(reporting, "call", return_value={"agents": self.agents}), patch.object(reporting, "relay", return_value=wake):
            result = reporting.context(self.directory)
        self.assertEqual(result["tasks"][0]["repository"]["worktree"], "/confirmed/worktree")
        self.assertEqual(result["tasks"][0]["pull_requests"], self.task["pull_requests"])
        self.assertEqual(result["controller_pane"], "control:p1")
        self.assertEqual(list(reporting.read(self.directory / "context.json")), ["example"])

    def test_sync_and_disable_only_touch_the_reporter_inbox(self):
        self.configure()
        wake = Mock()
        wake._documents.return_value = []
        with patch.object(reporting, "relay", return_value=wake), patch.object(reporting, "relay_action") as action:
            reporting.sync(self.tasks, [(self.task, 0)], self.agents, self.controller)
            self.assertEqual(action.call_count, 2)
            for invocation in action.call_args_list:
                self.assertEqual(invocation.kwargs["state_root"], str(self.directory / "wake"))
                self.assertNotEqual(invocation.kwargs["pane"], self.observer["pane_id"])
            wake._documents.return_value = [(Path("watch"), {"id": "a" * 32})]
            reporting.disable(self.tasks)
            self.assertEqual(action.call_args.args[1], "_remove")
            self.assertEqual(action.call_args.kwargs["state_root"], str(self.directory / "wake"))
            self.assertFalse(reporting.configuration(self.tasks)["enabled"])
        self.assertTrue((self.tasks.parent / "controller.json").exists())

    def test_ack_uses_only_reporter_root(self):
        with patch.object(reporting, "relay"), patch.object(reporting, "relay_action") as action:
            reporting.worker_main(self.directory, ["ack", "a" * 32])
        self.assertEqual(action.call_args.kwargs, {"state_root": str(self.directory / "wake"), "wake": "a" * 32, "acknowledge": True})

    def test_another_session_cannot_cancel_reporter_watches(self):
        self.configure()
        with patch.dict(os.environ, HERDR_SOCKET_PATH="/other/session.sock"), patch.object(reporting, "relay") as relay:
            with self.assertRaisesRegex(ValueError, "another Herdr session"):
                reporting.disable(self.tasks)
            relay.assert_not_called()
        self.assertTrue(reporting.configuration(self.tasks)["enabled"])

    def test_harness_arguments_are_native_and_not_a_shell(self):
        args = reporting.launch_arguments(dict(reporting.DEFAULTS, arguments='--config "custom=value"'))
        self.assertEqual(args[:4], ["--model", "gpt-6-luna", "-c", 'model_reasoning_effort="medium"'])
        self.assertEqual(args[-2:], ["--config", "custom=value"])
        with self.assertRaises(ValueError):
            reporting.launch_arguments(dict(reporting.DEFAULTS, kind="claude"))
        self.assertEqual(reporting.launch_arguments(dict(reporting.DEFAULTS, kind="claude", model="", reasoning="", arguments="--model example")), ["--model", "example"])

    def test_directory_is_separate_preserves_instructions_and_links_only_herdr(self):
        skill = self.root / "installed/herdr"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("Herdr skill")
        config = dict(reporting.DEFAULTS, directory=str(self.directory), herdr_skill=str(skill))
        prepared = reporting.prepare_directory(self.tasks, config)
        self.assertEqual(prepared, self.directory)
        for discovery in (".codex", ".agents"):
            self.assertEqual((prepared / discovery / "skills/herdr").resolve(), skill)
        self.assertIn("All workers and the orchestrator are read-only", (prepared / "AGENTS.md").read_text())
        (prepared / "AGENTS.md").write_text("Human customization")
        with self.assertRaisesRegex(ValueError, "Preserving"):
            reporting.prepare_directory(self.tasks, config)
        with self.assertRaisesRegex(ValueError, "outside repositories"):
            reporting.prepare_directory(self.tasks, dict(config, directory=str(reporting.PACKAGE / "reporter")))

    def test_relay_configuration_ignores_the_board_plugin_config_directory(self):
        with patch.dict(os.environ, HERDR_PLUGIN_CONFIG_DIR="/wrong/board"), patch.object(
                reporting.subprocess, "run", return_value=Mock(stdout="/right/wake\n")) as run:
            wake = reporting.relay()
            self.assertEqual(wake._config_dir(), Path("/right/wake"))
        self.assertEqual(run.call_args.args[0][-2:], ["config-dir", "quentintorg.agent-wake"])

    def test_start_timeout_does_not_create_duplicate_tabs_on_retry(self):
        (self.directory / "binding.json").unlink()
        with patch.object(reporting, "prepare_directory", return_value=self.directory), patch.object(reporting, "call") as call:
            call.side_effect = [{"agents": self.agents}, {"plugins": [{"plugin_id": "quentintorg.agent-wake", "enabled": True}]},
                                {"root_pane": {"pane_id": "control:p2", "terminal_id": "t"}, "tab": {"tab_id": "reporter-tab"}},
                                subprocess.TimeoutExpired("agent start", 40)]
            with self.assertRaises(subprocess.TimeoutExpired):
                reporting.enable(self.tasks)
            self.assertFalse(reporting.configuration(self.tasks)["enabled"])
            self.assertEqual(reporting.configuration(self.tasks)["pane"], "control:p2")
            call.reset_mock()
            resumed = dict(self.observer, terminal_id="t", name="reporter_" + reporting.hashlib.sha256(str(self.tasks).encode()).hexdigest()[:12])
            call.side_effect = [{"agents": self.agents}, {"plugins": [{"plugin_id": "quentintorg.agent-wake", "enabled": True}]},
                                {"agent": resumed}, {}, {"agents": self.agents}]
            with patch.object(reporting, "relay"), patch.object(reporting, "relay_action"), patch.object(reporting, "_sync"):
                reporting.enable(self.tasks)
            self.assertNotIn(("tab", "create"), [entry.args[:2] for entry in call.call_args_list])
            self.assertNotIn(("agent", "start"), [entry.args[:2] for entry in call.call_args_list])

    def test_startup_retry_cannot_adopt_another_terminal(self):
        config = dict(reporting.DEFAULTS, directory=str(self.directory), socket=os.environ["HERDR_SOCKET_PATH"],
                      pane="control:p2", terminal="original-terminal")
        reporting.write(reporting.config_path(self.tasks), config)
        (self.directory / "binding.json").unlink()
        with patch.object(reporting, "prepare_directory", return_value=self.directory), patch.object(reporting, "call") as call:
            call.side_effect = [{"agents": self.agents}, {"plugins": [{"plugin_id": "quentintorg.agent-wake", "enabled": True}]},
                                {"agent": self.observer}]
            with self.assertRaisesRegex(ValueError, "Cannot verify"):
                reporting.enable(self.tasks)
            self.assertEqual(call.call_count, 3)

    def test_settings_layout_bounds_long_native_arguments(self):
        settings = dict(board.VIEWER_DEFAULTS, reporter=dict(reporting.DEFAULTS, arguments="x" * 1000))
        for width in (60, 120, 240):
            lines, controls = board.settings_layout(settings, width)
            self.assertTrue(all(len(label) <= width - 4 for label, _, _ in controls.values()))
            self.assertTrue(all(len(line) <= width - 4 for line, _, _ in lines))

    def test_launch_option_editor_protects_pastes_and_cancels_without_saving(self):
        screen = Mock()
        screen.getmaxyx.return_value = (24, 120)
        reader = Mock()
        with patch.object(board.curses, "newwin"), patch.object(board.curses, "curs_set"):
            reader.read.side_effect = [board.InsertText("--option\nvalue"), "\r"]
            self.assertEqual(board.edit_reporter_setting(screen, "Arguments", "", reader), "--option value")
            reader.read.side_effect = ["x", "\x1b"]
            self.assertIsNone(board.edit_reporter_setting(screen, "Arguments", "original", reader))

    def test_real_relay_consumer_updates_reports_without_touching_coordinator(self):
        """Exercise real subscriptions/delivery/ack with isolated files and a fake Herdr."""
        self.configure()
        wake = reporting.relay()
        plugin = self.root / "wake-plugin"
        plugin.mkdir()
        coordinator_root = self.tasks.parent / "wake"
        coordinator_root.mkdir()
        coordinator_consumer = {"root": str(coordinator_root), "target": {"binding": str(self.tasks.parent / "controller.json")},
                                "socket": os.environ["HERDR_SOCKET_PATH"]}
        reporting.write(plugin / "config.json", {"consumers": [coordinator_consumer]})
        sentinel = coordinator_root / "inbox" / ("b" * 32 + ".json")
        reporting.write(sentinel, {"id": "b" * 32, "notified": True, "key": "example"})
        before = sentinel.read_bytes()
        submitted = []

        def herdr(*args):
            if args[:2] == ("agent", "list"):
                return {"result": {"agents": self.agents}}, None
            if args[:2] == ("agent", "get"):
                return {"result": {"agent": next(a for a in self.agents if a["pane_id"] == args[2])}}, None
            if args[:2] == ("agent", "prompt"):
                submitted.append(args)
                return {"result": {"type": "agent_prompted"}}, None
            raise AssertionError(args)

        with patch.object(wake, "_config_dir", return_value=plugin), patch.object(wake, "_herdr", side_effect=herdr), patch.object(
                wake, "_ensure_timer"), patch.object(wake.time, "sleep"), patch.object(reporting, "relay", return_value=wake):
            root = self.directory / "wake"
            reporting.relay_action(wake, "_configure", state_root=str(root), target=None,
                                   target_binding=str(self.directory / "binding.json"), reminder_minutes=0)
            self.assertIn(coordinator_consumer, reporting.read(plugin / "config.json")["consumers"])
            reporting.sync(self.tasks, [(self.task, 0)], self.agents, self.controller)
            self.author.update(agent_status="working", state_change_seq=2)
            wake._record_event_for(root, self.author)
            self.author.update(agent_status="done", state_change_seq=3)
            wake._record_event_for(root, self.author)
            wake._notify_consumer(root, {"binding": str(self.directory / "binding.json")})
            self.assertEqual(len(submitted), 1)
            self.assertEqual(submitted[0][2], self.observer["pane_id"])
            self.assertEqual(len(list(wake._documents(root / "inbox"))), 1)
            self.publish()
            row = self.row()
            reporting.decorate(self.tasks, [(self.task, 0)], self.agents, self.controller, [row])
            reporting.apply_display(row)
            self.assertEqual(row["summary"], "Proposal ready")
            identifiers = [record["id"] for _, record in wake._documents(root / "inbox")]
            reporting.worker_main(self.directory, ["ack", *identifiers])
            self.assertFalse(wake._documents(root / "inbox"))
            self.assertEqual(len(wake._documents(root / "watches")), 2)
            reporting.disable(self.tasks)
            self.assertFalse(wake._documents(root / "watches"))
        self.assertEqual(sentinel.read_bytes(), before)
        self.assertTrue(all(args[2] == self.observer["pane_id"] for args in submitted))


if __name__ == "__main__":
    unittest.main()
