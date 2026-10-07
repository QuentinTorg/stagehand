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

    def test_report_indicator_moves_from_pending_through_refresh_to_current(self):
        self.configure()
        self.publish()
        self.task["objective"] = "Expanded scope"
        for state in ("done", "working"):
            self.observer["agent_status"] = state
            row = self.row()
            reporting.decorate(self.tasks, [(self.task, 0)], self.agents, self.controller, [row])
            self.assertFalse(row["report_fresh"])
            self.assertEqual(row["reporter_activity"]["status"], state)
            self.assertIn("proposal written", row["report"]["recent_work"])
            before = (row["status"], row["action"])
            reporting.apply_display(row)
            self.assertEqual((row["status"], row["action"]), before)
        self.publish()
        reporting.decorate(self.tasks, [(self.task, 0)], self.agents, self.controller, [row])
        self.assertTrue(row["report_fresh"])
        self.assertEqual(board.report_label(row), ("✓ Report matches latest inputs", 3))

    def test_reconnect_failure_does_not_hide_retained_report(self):
        self.configure()
        self.publish()
        with patch.object(board, "CONTROLLER_BINDING", reporting.agent_binding.load(self.tasks.parent / "controller.json")), patch.object(
                board, "read_tasks", return_value=([(self.task, 0)], [])), patch.object(
                board, "inventory", return_value=([{"workspace_id": "task"}], [self.controller, self.author], [])), patch.object(
                reporting, "sync", side_effect=ValueError("Waiting for the reporter to resume")):
            rows, warnings, _ = board.snapshot(self.tasks, include_controller=True)
        self.assertIn("resume", " ".join(warnings))
        self.assertFalse(rows[0]["report_fresh"])
        self.assertEqual(rows[0]["reporter_activity"]["status"], "unavailable")
        self.assertIn("proposal written", rows[0]["report"]["recent_work"])

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

    def notice(self, identifier, key="example", observed=1, **extra):
        value = dict(id=identifier, key=key, observed_at=observed, notified=True,
                     watch_id=key, metadata={}, **extra)
        path = self.directory / "wake/inbox" / f"{identifier}.json"
        reporting.write(path, value)
        return path, value

    def test_publish_automatically_acks_only_covered_captured_notices(self):
        first, _ = self.notice("a" * 32)
        controller, _ = self.notice("b" * 32, key="controller")
        newer, _ = self.notice("c" * 32)
        other, _ = self.notice("d" * 32, key="other")
        reporting.write(self.directory / "context-wakes.json", {"a" * 32: 1, "b" * 32: 1, "d" * 32: 1})
        # The other task is not covered; its wake and the controller batch survive.
        record = self.record()
        reporting.write(self.directory / "context.json", {"example": record["fingerprint"], "other": "missing"})
        reporting.publish(self.directory, [record])
        self.assertFalse(first.exists())
        self.assertTrue(controller.exists())
        self.assertTrue(newer.exists())
        self.assertTrue(other.exists())
        reporting.write(self.directory / "context.json", {"example": record["fingerprint"]})
        reporting.publish(self.directory, [record])
        self.assertFalse(controller.exists())
        self.assertTrue(newer.exists())

    def test_publish_does_not_ack_a_notice_coalesced_after_context(self):
        path, _ = self.notice("a" * 32, observed=2)
        reporting.write(self.directory / "context-wakes.json", {"a" * 32: 1})
        self.publish()
        self.assertTrue(path.exists())

    def test_invalid_publication_does_not_ack(self):
        path, _ = self.notice("a" * 32)
        reporting.write(self.directory / "context-wakes.json", {"a" * 32: 1})
        reporting.write(self.directory / "context.json", {"example": self.record()["fingerprint"]})
        with self.assertRaises(ValueError):
            reporting.publish(self.directory, [dict(self.record(), fingerprint="wrong")])
        self.assertTrue(path.exists())

    def test_sync_ack_recovery_retains_a_newer_turn(self):
        old, _ = self.notice("a" * 32)
        self.publish()
        stamp = reporting.read(self.directory / "reports.json")["example"]["updated_at"]
        new, _ = self.notice("b" * 32, observed=stamp + 1)
        controller, _ = self.notice("c" * 32, key="controller", observed=stamp + 1)
        reporting.acknowledge_covered(self.directory, {"example": self.record()["fingerprint"]})
        self.assertFalse(old.exists())
        self.assertTrue(new.exists())
        self.assertTrue(controller.exists())

    def test_refresh_debounces_and_coalesces_without_repeating_same_snapshot(self):
        root = self.directory / "wake"
        root.mkdir()
        wake = reporting.relay()
        fingerprints = {"example": "first"}
        reporting.queue_refresh(self.directory, fingerprints, wake, now=10)
        reporting.queue_refresh(self.directory, {"example": "second"}, wake, now=12)
        reporting.queue_refresh(self.directory, {"example": "second"}, wake, now=16)
        self.assertFalse(wake._documents(root / "inbox"))
        reporting.queue_refresh(self.directory, {"example": "second"}, wake, now=17)
        first_path, first = wake._documents(root / "inbox")[0]
        reporting.queue_refresh(self.directory, {"example": "second"}, wake, now=100)
        self.assertEqual(wake._documents(root / "inbox"), [(first_path, first)])
        reporting.queue_refresh(self.directory, {"example": "third", "another": "new"}, wake, now=101)
        reporting.queue_refresh(self.directory, {"example": "third", "another": "new"}, wake, now=106)
        path, notice = wake._documents(root / "inbox")[0]
        self.assertEqual(path, first_path)
        self.assertEqual(notice["metadata"]["task_ids"], ["another", "example"])
        notice["notified"] = True
        reporting.write(path, notice)
        reporting.queue_refresh(self.directory, {"example": "fourth"}, wake, now=107)
        reporting.queue_refresh(self.directory, {"example": "fourth"}, wake, now=112)
        self.assertEqual(len(wake._documents(root / "inbox")), 2)
        self.assertEqual(reporting.read(path), notice)

    def test_current_reports_never_queue_a_refresh(self):
        self.publish()
        root = self.directory / "wake"
        root.mkdir()
        wake = reporting.relay()
        fingerprints = {"example": self.record()["fingerprint"]}
        reporting.queue_refresh(self.directory, fingerprints, wake, now=10)
        reporting.queue_refresh(self.directory, fingerprints, wake, now=1000)
        self.assertFalse(wake._documents(root / "inbox"))

    def test_real_relay_recovers_a_late_task_edit_and_an_orphaned_controller_notice(self):
        """Reproduce the observed publish/update race without touching live agents."""
        self.configure()
        self.publish()
        reporting.write(self.tasks / "task.json", self.task)
        reporting.write(self.directory / "connection.json", {"tasks": str(self.tasks), "socket": os.environ["HERDR_SOCKET_PATH"]})
        wake = reporting.relay()
        plugin = self.root / "plugin"
        plugin.mkdir()
        root = self.directory / "wake"
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
                wake, "_ensure_timer"), patch.object(wake.time, "sleep"), patch.object(reporting, "relay", return_value=wake), patch.object(
                reporting, "call", return_value={"agents": self.agents}), patch.object(reporting.time, "time", return_value=10):
            reporting.sync(self.tasks, [(self.task, 0)], self.agents, self.controller)
            self.notice("a" * 32, key="controller")  # Wrong manual ACK left yesterday's delivery outstanding.
            self.task["state"]["summary"] = "Review complete"
            reporting.write(self.tasks / "task.json", self.task)
            self.observer["agent_status"] = "working"
            reporting.sync(self.tasks, [(self.task, 0)], self.agents, self.controller)
            with patch.object(reporting.time, "time", return_value=15):
                reporting.sync(self.tasks, [(self.task, 0)], self.agents, self.controller)
            self.assertFalse(submitted)
            self.observer["agent_status"] = "idle"
            with patch.object(reporting.time, "time", return_value=16):
                reporting.sync(self.tasks, [(self.task, 0)], self.agents, self.controller)
            self.assertEqual(len(submitted), 1)
            self.assertIn('"kind":"report-refresh"', submitted[0][3])
            reporting.context(self.directory)
            record = self.record()
            self.task["state"]["summary"] = "Owner decision recorded during reporting"
            reporting.write(self.tasks / "task.json", self.task)
            reporting.publish(self.directory, [record])
            self.assertFalse(wake._documents(root / "inbox"))  # Captured IDs were ACKed by the helper.
            with patch.object(reporting.time, "time", return_value=20):
                reporting.sync(self.tasks, [(self.task, 0)], self.agents, self.controller)
            with patch.object(reporting.time, "time", return_value=25):
                reporting.sync(self.tasks, [(self.task, 0)], self.agents, self.controller)
            self.assertEqual(len(submitted), 2)  # The late edit receives one additional refresh.
            for now in (30, 35, 40):
                with patch.object(reporting.time, "time", return_value=now):
                    reporting.sync(self.tasks, [(self.task, 0)], self.agents, self.controller)
            self.assertEqual(len(submitted), 2)
            self.assertTrue(all(args[2] == self.observer["pane_id"] for args in submitted))

    def test_disable_cancels_pending_refreshes_and_reenable_can_request_again(self):
        self.configure()
        root = self.directory / "wake"
        root.mkdir()
        wake = reporting.relay()
        fingerprints = {"example": "new"}
        reporting.queue_refresh(self.directory, fingerprints, wake, now=10)
        reporting.queue_refresh(self.directory, fingerprints, wake, now=15)
        with patch.object(reporting, "relay", return_value=wake):
            reporting.disable(self.tasks)
        self.assertFalse(wake._documents(root / "inbox"))
        self.assertFalse((self.directory / "refresh.json").exists())
        self.configure()
        reporting.queue_refresh(self.directory, fingerprints, wake, now=20)
        reporting.queue_refresh(self.directory, fingerprints, wake, now=25)
        self.assertEqual(len(wake._documents(root / "inbox")), 1)

    def test_report_lists_survive_publish_and_display_without_multiline_table_labels(self):
        self.configure()
        record = dict(self.record(), summary="Proposal\nready",
                      recent_work="- Fault isolated.\n\t- Reproduced offline.\n- Proposal written.",
                      review_coverage="- Author checks passed.\n- Independent review pending.")
        reporting.write(self.directory / "context.json", {"example": record["fingerprint"]})
        reporting.publish(self.directory, [record])
        row = self.row()
        reporting.decorate(self.tasks, [(self.task, 0)], self.agents, self.controller, [row])
        reporting.apply_display(row)
        self.assertEqual(row["summary"], "Proposal ready")
        self.assertEqual(row["report"]["recent_work"], "- Fault isolated.\n  - Reproduced offline.\n- Proposal written.")
        lines = [line for line, _, _ in board.detail_lines(row, 100)]
        self.assertIn("  - Fault isolated.", lines)
        self.assertIn("    - Reproduced offline.", lines)
        self.assertIn("  - Independent review pending.", lines)

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

    def test_context_focuses_changed_evidence_but_exposes_obsolete_other_conclusions(self):
        self.publish()
        # This report is structurally fresh, but a different worker just
        # finished the dependency it still describes as blocking the human.
        reports = reporting.read(self.directory / "reports.json")
        reports["example"]["human_action"] = "Wait for SDK implementation."
        reporting.write(self.directory / "reports.json", reports)
        sdk = dict(self.task, task_id="sdk", agents={}, state={"name": "complete", "summary": "SDK drafts published"})
        reporting.write(self.tasks / "planner.json", self.task)
        reporting.write(self.tasks / "sdk.json", sdk)
        reporting.write(self.directory / "connection.json", {"tasks": str(self.tasks), "socket": os.environ["HERDR_SOCKET_PATH"]})
        wake = Mock()
        wake._documents.return_value = []
        with patch.object(reporting, "call", return_value={"agents": self.agents}), patch.object(reporting, "relay", return_value=wake):
            result = reporting.context(self.directory)
            self.assertEqual([task["task_id"] for task in result["tasks"]], ["sdk"])
            planner = next(item for item in result["index"] if item["task_id"] == "example")
            self.assertTrue(planner["report_matches_inputs"])
            self.assertEqual(planner["next_step"], "Wait for SDK implementation.")
            self.assertEqual(next(item for item in result["index"] if item["task_id"] == "sdk")["state"]["summary"], "SDK drafts published")
            detail = reporting.context(self.directory, ["example"])
            self.assertEqual(detail["tasks"][0]["previous_report"]["human_action"], "Wait for SDK implementation.")
            self.assertEqual(len(reporting.context(self.directory, all_tasks=True)["tasks"]), 2)
            with self.assertRaisesRegex(ValueError, "Unknown task"):
                reporting.context(self.directory, ["not-in-this-workspace"])
        # Correcting a related conclusion is allowed without inventing task
        # activity or changing the orchestrator's record or authority.
        corrected = dict(self.record(), human_action="", recent_work="SDK implementation finished; prior dependency resolved.")
        before = (self.tasks / "planner.json").read_bytes()
        reporting.publish(self.directory, [corrected])
        self.assertEqual(reporting.read(self.directory / "reports.json")["example"]["human_action"], "")
        self.assertEqual((self.tasks / "planner.json").read_bytes(), before)

    def test_context_includes_delivered_task_even_when_its_fingerprint_matches(self):
        self.publish()
        reporting.write(self.tasks / "task.json", self.task)
        reporting.write(self.directory / "connection.json", {"tasks": str(self.tasks), "socket": os.environ["HERDR_SOCKET_PATH"]})
        wake = Mock()
        wake._documents.return_value = [(Path("notice"), {"id": "a" * 32, "key": "example", "observed_at": 1})]
        with patch.object(reporting, "call", return_value={"agents": self.agents}), patch.object(reporting, "relay", return_value=wake):
            self.assertEqual([item["task_id"] for item in reporting.context(self.directory)["tasks"]], ["example"])

    def test_sync_and_disable_only_touch_the_reporter_inbox(self):
        self.configure()
        wake = Mock()
        wake._documents.return_value = []
        wake._configured_consumers.return_value = []
        with patch.object(reporting, "relay", return_value=wake), patch.object(reporting, "relay_action") as action:
            reporting.sync(self.tasks, [(self.task, 0)], self.agents, self.controller)
            self.assertEqual(action.call_count, 3)
            for invocation in action.call_args_list:
                self.assertEqual(invocation.kwargs["state_root"], str(self.directory / "wake"))
                self.assertNotEqual(invocation.kwargs.get("pane"), self.observer["pane_id"])
            wake._documents.return_value = [(Path("watch"), {"id": "a" * 32})]
            reporting.disable(self.tasks)
            self.assertEqual(action.call_args.args[1], "_remove")
            self.assertEqual(action.call_args.kwargs["state_root"], str(self.directory / "wake"))
            self.assertFalse(reporting.configuration(self.tasks)["enabled"])
        self.assertTrue((self.tasks.parent / "controller.json").exists())

    def test_bootstrap_binding_gains_native_identity_before_a_restart(self):
        path = self.directory / "binding.json"
        with patch.object(reporting.agent_binding, "process_identity", return_value=123):
            reporting.agent_binding.save(path, reporting.agent_binding.capture(dict(self.observer, agent_session=None)), replace=True)
            reporting.reporter_agent(self.directory, self.agents)
        self.assertEqual(reporting.agent_binding.load(path)["session"], reporting.agent_binding.native_session(self.observer))
        restored = dict(self.observer, pane_id="control:p99", terminal_id="restored-terminal", name=None)
        self.assertEqual(reporting.reporter_agent(self.directory, [restored]), restored)

    def test_bootstrap_binding_never_adopts_a_replaced_process(self):
        path = self.directory / "binding.json"
        with patch.object(reporting.agent_binding, "process_identity", return_value=123):
            reporting.agent_binding.save(path, reporting.agent_binding.capture(dict(self.observer, agent_session=None)), replace=True)
        before = path.read_bytes()
        with patch.object(reporting.agent_binding, "process_identity", return_value=456):
            with self.assertRaisesRegex(ValueError, "process changed"):
                reporting.reporter_agent(self.directory, self.agents)
        self.assertEqual(path.read_bytes(), before)

    def test_context_can_read_workers_while_the_orchestrator_is_still_resuming(self):
        reporting.write(self.tasks / "task.json", self.task)
        reporting.write(self.directory / "connection.json", {"tasks": str(self.tasks), "socket": os.environ["HERDR_SOCKET_PATH"]})
        wake = Mock()
        wake._documents.return_value = []
        with patch.object(reporting, "call", return_value={"agents": [self.observer, self.author]}), patch.object(
            reporting, "relay", return_value=wake
        ):
            context = reporting.context(self.directory)
        self.assertIsNone(context["controller_pane"])
        self.assertIn("still resuming", context["warnings"][0])
        self.assertEqual(context["tasks"][0]["roles"][0]["pane_id"], self.author["pane_id"])

    def test_reenable_uses_saved_launch_options_only_in_an_empty_reporter_shell(self):
        config = self.configure()
        config.update(enabled=False, pane=self.observer["pane_id"], terminal=self.observer["terminal_id"],
                      model="different-model", reasoning="high")
        reporting.write(reporting.config_path(self.tasks), config)
        info = {"shell_pid": 10, "foreground_process_group_id": 10,
                "foreground_processes": [{"pid": 10, "cwd": str(self.directory)}]}
        launched = dict(self.observer, name="reporter_" + reporting.hashlib.sha256(str(self.tasks).encode()).hexdigest()[:12])
        with patch.object(reporting, "prepare_directory", return_value=self.directory), patch.object(
            reporting, "call", side_effect=[{"agents": [self.controller, self.author]},
                {"plugins": [{"plugin_id": "quentintorg.agent-wake", "enabled": True}]},
                {"pane": {"workspace_id": "control", "terminal_id": self.observer["terminal_id"]}}, {"process_info": info},
                {"agent": launched}, {}, {"agents": self.agents}]
        ) as call, patch.object(reporting, "relay"), patch.object(reporting, "relay_action"), patch.object(reporting, "_sync"):
            reporting.enable(self.tasks)
        launch = next(entry for entry in call.call_args_list if entry.args[:2] == ("agent", "start"))
        self.assertEqual(launch.args[launch.args.index("--") + 1:], tuple(reporting.launch_arguments(config)))
        self.assertNotIn(("tab", "create"), [entry.args[:2] for entry in call.call_args_list])
        self.assertTrue(reporting.configuration(self.tasks)["enabled"])

    def test_reenable_preserves_an_occupied_reporter_pane(self):
        config = self.configure()
        config.update(enabled=False, pane=self.observer["pane_id"], terminal=self.observer["terminal_id"])
        reporting.write(reporting.config_path(self.tasks), config)
        with patch.object(reporting, "prepare_directory", return_value=self.directory), patch.object(
            reporting, "call", side_effect=[{"agents": [self.controller, self.author]},
                {"plugins": [{"plugin_id": "quentintorg.agent-wake", "enabled": True}]},
                {"pane": {"workspace_id": "control"}}, {"process_info": {"shell_pid": 10, "foreground_process_group_id": 99}}]
        ) as call:
            with self.assertRaisesRegex(ValueError, "no occupied pane was changed"):
                reporting.enable(self.tasks)
        self.assertNotIn(("agent", "start"), [entry.args[:2] for entry in call.call_args_list])

    def test_relaunch_timeout_reuses_the_started_agent_on_retry(self):
        config = self.configure()
        config.update(enabled=False, pane=self.observer["pane_id"], terminal=self.observer["terminal_id"])
        reporting.write(reporting.config_path(self.tasks), config)
        info = {"shell_pid": 10, "foreground_process_group_id": 10,
                "foreground_processes": [{"pid": 10, "cwd": str(self.directory)}]}
        with patch.object(reporting, "prepare_directory", return_value=self.directory), patch.object(reporting, "call") as call:
            call.side_effect = [{"agents": [self.controller, self.author]},
                {"plugins": [{"plugin_id": "quentintorg.agent-wake", "enabled": True}]},
                {"pane": {"workspace_id": "control", "terminal_id": self.observer["terminal_id"]}},
                {"process_info": info}, subprocess.TimeoutExpired("agent start", 40)]
            with self.assertRaises(subprocess.TimeoutExpired):
                reporting.enable(self.tasks)
            self.assertTrue(reporting.configuration(self.tasks)["starting"])
            launched = dict(self.observer,
                name="reporter_" + reporting.hashlib.sha256(str(self.tasks).encode()).hexdigest()[:12],
                agent_session={"agent": "codex", "kind": "id", "value": "new-conversation"})
            call.reset_mock()
            call.side_effect = [{"agents": [self.controller, launched, self.author]},
                {"plugins": [{"plugin_id": "quentintorg.agent-wake", "enabled": True}]},
                {"agent": launched}, {}, {"agents": [self.controller, launched, self.author]}]
            with patch.object(reporting, "relay"), patch.object(reporting, "relay_action"), patch.object(reporting, "_sync"):
                reporting.enable(self.tasks)
            self.assertNotIn(("agent", "start"), [entry.args[:2] for entry in call.call_args_list])
            self.assertNotIn(("tab", "create"), [entry.args[:2] for entry in call.call_args_list])
            self.assertNotIn("starting", reporting.configuration(self.tasks))
            self.assertEqual(reporting.agent_binding.load(self.directory / "binding.json")["session"]["value"], "new-conversation")

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

    def test_blocked_startup_points_to_retained_setup_tab(self):
        with patch.object(reporting, "prepare_directory", return_value=self.directory), patch.object(reporting, "call") as call:
            call.side_effect = [{"agents": self.agents}, {"plugins": [{"plugin_id": "quentintorg.agent-wake", "enabled": True}]},
                                {"root_pane": {"pane_id": "control:p2", "terminal_id": "t"}, "tab": {"tab_id": "reporter-tab"}},
                                subprocess.CalledProcessError(1, "agent start")]
            with self.assertRaisesRegex(ValueError, "Open the Status reporter tab"):
                reporting.enable(self.tasks)
            config = reporting.configuration(self.tasks)
            self.assertFalse(config["enabled"])
            self.assertEqual(config["pane"], "control:p2")

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

    def test_restored_reporter_repairs_real_hooks_and_replays_unacknowledged_notice_once(self):
        """Simulate cold-start order with real relay files, not the user's server."""
        self.configure()
        wake = reporting.relay()
        plugin = self.root / "plugin"
        plugin.mkdir()
        coordinator = {"root": str(self.tasks.parent / "wake"), "target": {"binding": str(self.tasks.parent / "controller.json")},
                       "socket": os.environ["HERDR_SOCKET_PATH"]}
        reporting.write(plugin / "config.json", {"consumers": [coordinator]})
        root = self.directory / "wake"
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
            wake, "_ensure_timer"
        ), patch.object(wake.time, "sleep"), patch.object(reporting, "relay", return_value=wake):
            reporting.sync(self.tasks, [(self.task, 0)], self.agents, self.controller)
            self.author.update(agent_status="working", state_change_seq=2)
            wake._record_event_for(root, self.author)
            self.author.update(agent_status="done", state_change_seq=3)
            wake._record_event_for(root, self.author)
            notice_path, notice = wake._documents(root / "inbox")[0]
            notice["notified"] = True  # Accepted just before the simulated reboot.
            reporting.write(notice_path, notice)

            self.observer.update(pane_id="control:p99", terminal_id="restored-terminal", name=None)
            self.agents.remove(self.controller)  # Controller has not resumed yet.
            reporting.write(plugin / "config.json", {"consumers": [coordinator]})
            reporting.sync(self.tasks, [(self.task, 0)], self.agents, None)
            self.assertEqual([entry[2] for entry in submitted], ["control:p99"])
            self.assertEqual(reporting.configuration(self.tasks)["pane"], "control:p99")
            self.assertTrue(reporting.read(notice_path)["notified"])
            self.assertIn(coordinator, reporting.read(plugin / "config.json")["consumers"])
            reporting.sync(self.tasks, [(self.task, 0)], self.agents, None)
            self.assertEqual(len(submitted), 1)

            reporting.worker_main(self.directory, ["ack", notice["id"]])
            self.author.update(agent_status="working", state_change_seq=4)
            wake._record_event_for(root, self.author)
            self.author.update(agent_status="done", state_change_seq=5)
            wake._record_event_for(root, self.author)
            wake._notify_consumer(root, {"binding": str(self.directory / "binding.json")})
            self.assertEqual([entry[2] for entry in submitted], ["control:p99", "control:p99"])


if __name__ == "__main__":
    unittest.main()
