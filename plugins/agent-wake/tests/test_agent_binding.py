import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import agent_binding as binding


class BindingTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, HERDR_SOCKET_PATH="/test/session.sock")
        env.start()
        self.addCleanup(env.stop)
        anchor = patch.object(binding, "process_identity", return_value=123)
        anchor.start()
        self.addCleanup(anchor.stop)
        self.agent = {"workspace_id": "control", "pane_id": "control:p1", "terminal_id": "old-terminal",
                      "agent_session": {"agent": "claude", "kind": "id", "value": "conversation"}}
        self.binding = binding.capture(self.agent)

    def test_restored_session_needs_no_name_or_original_terminal(self):
        restored = dict(self.agent, pane_id="control:p2", terminal_id="new-terminal")
        self.assertEqual(binding.resolve(self.binding, [restored]), restored)
        self.assertEqual(binding.resolve(self.binding, [dict(restored, name="different")])["pane_id"], "control:p2")

    def test_reused_pane_wrong_workspace_and_duplicate_session_do_not_route(self):
        for agents in ([], [dict(self.agent, workspace_id="other")],
                       [dict(self.agent, agent_session={"agent": "claude", "kind": "id", "value": "other"})],
                       [self.agent, dict(self.agent, pane_id="control:p2")]):
            with self.subTest(agents=agents), self.assertRaises(ValueError):
                binding.resolve(self.binding, agents)
        with patch.dict(os.environ, HERDR_SOCKET_PATH="/test/other.sock"), self.assertRaises(ValueError):
            binding.resolve(self.binding, [self.agent])

    def test_unresumable_agent_only_matches_its_existing_terminal(self):
        agent = dict(self.agent, agent_session=None)
        saved = binding.capture(agent)
        self.assertEqual(binding.resolve(saved, [agent]), agent)
        with patch.object(binding, "process_identity", return_value=456), self.assertRaises(ValueError):
            binding.resolve(saved, [agent])
        with self.assertRaises(binding.ControllerUnavailable):
            binding.resolve(saved, [dict(agent, terminal_id="replacement")])

    def test_binding_survives_reload_and_requires_explicit_handover(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "controller.json"
            binding.save(path, self.binding)
            binding.save(path, binding.capture(dict(self.agent, terminal_id="restored")))
            replacement = binding.capture(dict(self.agent, agent_session=None))
            with self.assertRaises(ValueError):
                binding.save(path, replacement)
            self.assertEqual(binding.load(path)["session"], self.binding["session"])
            binding.save(path, replacement, replace=True)
            self.assertEqual(binding.load(path), replacement)

    def test_invalid_or_missing_configuration_fails_closed(self):
        for value in (None, {}, dict(self.binding, session={"value": "incomplete"})):
            with self.assertRaises(ValueError):
                binding.resolve(value, [self.agent])
        with tempfile.TemporaryDirectory() as root, self.assertRaises(ValueError):
            binding.load(Path(root) / "missing.json")

    def resumed(self):
        session = {"agent": "codex", "kind": "id", "value": "01a10c9b-357a-7240-9507-1fa934f4ba12"}
        original = dict(self.agent, agent="codex", agent_session=session)
        saved = binding.capture(original)
        live = dict(original, terminal_id="new-terminal", agent_session=None)
        info = {"pane_id": live["pane_id"], "foreground_process_group_id": 20, "shell_pid": 10,
                "foreground_processes": [{"pid": 20, "argv": ["/installed/bin/codex", "resume", session["value"]]}]}
        return saved, live, info

    def test_missing_metadata_recovers_only_the_exact_foreground_conversation(self):
        saved, live, info = self.resumed()
        with patch.object(binding.subprocess, "run", return_value=Mock(stdout=json.dumps({"result": {"process_info": info}}))) as run:
            recovered = binding.resolve(saved, [live])
        self.assertEqual(binding.native_session(recovered), saved["session"])
        self.assertEqual(recovered["terminal_id"], "new-terminal")
        self.assertIsNone(live["agent_session"])
        self.assertEqual(run.call_args.args[0][-2:], ["--pane", live["pane_id"]])

    def test_missing_metadata_never_adopts_a_neighbor_or_conflicting_session(self):
        saved, live, _ = self.resumed()
        alternatives = [dict(live, pane_id="control:p2"), dict(live, workspace_id="other"),
                        dict(live, agent_session=dict(saved["session"], value="other-conversation"))]
        for agent in alternatives:
            with self.subTest(agent=agent), patch.object(binding.subprocess, "run") as run, self.assertRaises(ValueError):
                binding.resolve(saved, [agent])
            run.assert_not_called()

    def test_resume_fallback_rejects_shells_unrelated_commands_and_ambiguous_processes(self):
        saved, live, info = self.resumed()
        wrong = dict(info, foreground_processes=[{"argv": ["codex", "resume", "another-id"]}])
        alternatives = [dict(info, foreground_process_group_id=10), dict(info, pane_id="other:p1"), wrong,
                        dict(info, foreground_processes=[{"argv": ["codex", "resume", "--last"]}]),
                        dict(info, foreground_processes=[{"argv": ["echo", "resume", saved["session"]["value"]]}]),
                        dict(info, foreground_processes=info["foreground_processes"] * 2)]
        for process_info in alternatives:
            with self.subTest(info=process_info), patch.object(binding.subprocess, "run", return_value=Mock(
                    stdout=json.dumps({"result": {"process_info": process_info}}))), self.assertRaises(ValueError):
                binding.resolve(saved, [live])

    def test_resume_inspection_failure_preserves_binding_and_stays_unavailable(self):
        saved, live, _ = self.resumed()
        before = dict(saved)
        with patch.object(binding.subprocess, "run", side_effect=PermissionError("denied")), self.assertRaises(binding.ControllerUnavailable):
            binding.resolve(saved, [live])
        self.assertEqual(saved, before)
        with patch.object(binding.subprocess, "run", side_effect=PermissionError("denied")), self.assertRaises(binding.ControllerUnavailable):
            binding.resolve(saved, [dict(live, agent_session=saved["session"])])

    def test_misattributed_reporter_metadata_cannot_redirect_to_the_orchestrator(self):
        saved, live, info = self.resumed()
        neighbor = dict(live, pane_id="control:p2", agent_session=saved["session"])
        other_info = dict(info, pane_id="control:p2", foreground_processes=[{
            "argv": ["codex", "resume", "01a0f284-2ec9-7ec1-8ed1-10a1da64170b"]}])
        def process(*args, **kwargs):
            current = other_info if args[0][-1] == neighbor["pane_id"] else info
            return Mock(stdout=json.dumps({"result": {"process_info": current}}))
        with patch.object(binding.subprocess, "run", side_effect=process):
            resolved = binding.resolve(saved, [neighbor, live])
            self.assertEqual(resolved["pane_id"], live["pane_id"])
            with self.assertRaises(binding.ControllerUnavailable):
                binding.resolve(saved, [neighbor])

    def test_retained_metadata_never_sends_wakes_to_a_shell_or_unrelated_command(self):
        saved, live, info = self.resumed()
        live["agent_session"] = saved["session"]
        alternatives = [dict(info, foreground_process_group_id=10),
                        dict(info, foreground_processes=[{"argv": ["less", "notes.md"]}])]
        for current in alternatives:
            with self.subTest(info=current), patch.object(binding.subprocess, "run", return_value=Mock(
                    stdout=json.dumps({"result": {"process_info": current}}))), self.assertRaises(binding.ControllerUnavailable):
                binding.resolve(saved, [live])
