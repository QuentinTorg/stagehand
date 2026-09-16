import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

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
