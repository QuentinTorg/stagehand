import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "agent-wake"
loader = importlib.machinery.SourceFileLoader("agent_wake", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
wake = importlib.util.module_from_spec(spec)
loader.exec_module(wake)


class WakePluginTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config_dir = self.root / "plugin-config"
        self.state_root = self.root / "wake-state"
        self.config_dir.mkdir()
        self.state_root.mkdir()
        (self.config_dir / "config.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "consumers": [
                        {"root": str(self.state_root), "target": "controller_agent"}
                    ],
                }
            )
        )
        self.environment = mock.patch.dict(
            os.environ,
            {"HERDR_PLUGIN_CONFIG_DIR": str(self.config_dir)},
            clear=False,
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def arm(self, *extra):
        args = wake._parser().parse_args(
            [
                "arm",
                "--state-root",
                str(self.state_root),
                "--key",
                "example",
                "--workspace-id",
                "w2",
                "--workspace-label",
                "example-workspace",
                "--pane",
                "w2:p1",
                "--agent",
                "example_author",
                "--metadata",
                '{"role":"author"}',
                *extra,
            ]
        )
        with mock.patch("builtins.print"):
            args.run(args)

    def command(self, *arguments):
        args = wake._parser().parse_args([*arguments, "--state-root", str(self.state_root)])
        with mock.patch("builtins.print"):
            args.run(args)

    def emit(self, status):
        event = {
            "event": "pane.agent_status_changed",
            "data": {
                "type": "pane_agent_status_changed",
                "pane_id": "w2:p1",
                "workspace_id": "w2",
                "agent_status": status,
                "agent": "example_author",
            },
        }
        with mock.patch.dict(os.environ, {"HERDR_PLUGIN_EVENT_JSON": json.dumps(event)}):
            wake._hook()

    def documents(self, name):
        directory = self.state_root / name
        return [json.loads(path.read_text()) for path in directory.glob("*.json")]

    def test_working_then_done_wakes_once(self):
        self.arm()
        prompts = []

        def herdr(*args):
            if args[:3] == ("agent", "get", "w2:p1"):
                return {
                    "result": {
                        "agent": {
                            "agent_status": "done",
                            "pane_id": "w2:p1",
                            "workspace_id": "w2",
                            "name": "example_author",
                        }
                    }
                }, None
            if args[:3] == ("agent", "get", "controller_agent"):
                return {"result": {"agent": {"agent_status": "idle"}}}, None
            if args[:3] == ("agent", "prompt", "controller_agent"):
                prompts.append(args[3])
                return {"result": {"type": "agent_prompted"}}, None
            self.fail(f"unexpected Herdr call: {args}")

        with mock.patch.object(wake, "_herdr", side_effect=herdr), mock.patch.object(
            wake.time, "sleep"
        ):
            self.emit("working")
            self.emit("done")
            self.emit("done")

        self.assertEqual(1, len(prompts))
        self.assertTrue(prompts[0].startswith("HERDR_AGENT_WAKE ["))
        self.assertTrue(self.documents("inbox")[0]["notified"])
        self.assertEqual("fired", self.documents("watches")[0]["state"])

    def test_settled_without_observed_working_is_ignored(self):
        self.arm()
        with mock.patch.object(wake, "_herdr") as herdr:
            self.emit("idle")
        herdr.assert_not_called()
        self.assertEqual([], self.documents("inbox"))
        self.assertEqual("armed", self.documents("watches")[0]["state"])

    def test_busy_target_defers_until_flush(self):
        self.arm()
        target_status = ["working", "working", "idle"]
        prompts = []

        def herdr(*args):
            if args[:3] == ("agent", "get", "w2:p1"):
                return {"result": {"agent": {"agent_status": "done"}}}, None
            if args[:3] == ("agent", "get", "controller_agent"):
                return {
                    "result": {"agent": {"agent_status": target_status.pop(0)}}
                }, None
            if args[:3] == ("agent", "prompt", "controller_agent"):
                prompts.append(args[3])
                return {"result": {"type": "agent_prompted"}}, None
            self.fail(f"unexpected Herdr call: {args}")

        with mock.patch.object(wake, "_herdr", side_effect=herdr), mock.patch.object(
            wake.time, "sleep"
        ):
            self.emit("working")
            self.emit("done")
            self.assertFalse(self.documents("inbox")[0]["notified"])
            wake._flush()

        self.assertEqual(1, len(prompts))
        self.assertTrue(self.documents("inbox")[0]["notified"])

    def test_target_settling_during_delivery_recheck_is_not_missed(self):
        self.arm()
        target_status = ["working", "idle"]
        prompts = []

        def herdr(*args):
            if args[:3] == ("agent", "get", "w2:p1"):
                return {"result": {"agent": {"agent_status": "done"}}}, None
            if args[:3] == ("agent", "get", "controller_agent"):
                return {
                    "result": {"agent": {"agent_status": target_status.pop(0)}}
                }, None
            if args[:3] == ("agent", "prompt", "controller_agent"):
                prompts.append(args[3])
                return {"result": {"type": "agent_prompted"}}, None
            self.fail(f"unexpected Herdr call: {args}")

        with mock.patch.object(wake, "_herdr", side_effect=herdr), mock.patch.object(
            wake.time, "sleep"
        ):
            self.emit("working")
            self.emit("done")

        self.assertEqual(1, len(prompts))
        self.assertTrue(self.documents("inbox")[0]["notified"])


class PersistentWakeTest(WakePluginTest):
    """Exercise successive human/agent turns without worker-side callbacks."""

    def setUp(self):
        super().setUp()
        self.source = {"pane_id": "w2:p1", "workspace_id": "w2",
                       "name": "example_author", "agent_status": "idle",
                       "agent_session": {"kind": "id", "value": "session-1"}}
        self.target_status = "idle"
        self.prompts = []
        self.prompt_fails = False
        patcher = mock.patch.object(wake, "_herdr", side_effect=self.herdr)
        patcher.start()
        self.addCleanup(patcher.stop)
        sleeper = mock.patch.object(wake.time, "sleep")
        sleeper.start()
        self.addCleanup(sleeper.stop)

    def herdr(self, *args):
        if args[:3] == ("agent", "get", "w2:p1"):
            return {"result": {"agent": self.source.copy()}}, None
        if args[:3] == ("agent", "get", "controller_agent"):
            return {"result": {"agent": {"agent_status": self.target_status}}}, None
        if args[:3] == ("agent", "prompt", "controller_agent"):
            self.prompts.append(args[3])
            if self.prompt_fails:
                return None, "transport unavailable"
            return {"result": {"type": "agent_prompted"}}, None
        self.fail(f"unexpected call: {args}")

    def turn(self, outcome="done"):
        self.source["agent_status"] = "working"
        self.emit("working")
        self.source["agent_status"] = outcome
        self.emit(outcome)

    def test_human_followup_after_ack_needs_no_rearm(self):
        self.arm("--persistent")
        watch_id = self.documents("watches")[0]["id"]
        self.turn()
        first = self.documents("inbox")[0]["id"]
        self.command("ack", "--wake", first)
        self.assertEqual(watch_id, self.documents("watches")[0]["id"])
        self.turn()
        self.assertEqual(2, len(self.prompts))
        self.assertNotEqual(first, self.documents("inbox")[0]["id"])

    def test_ack_old_notice_preserves_new_turn(self):
        self.arm("--persistent")
        self.turn()
        first = self.documents("inbox")[0]["id"]
        for _ in range(5):
            self.turn()
        self.assertEqual(2, len(self.documents("inbox")))
        self.assertEqual(1, len(self.prompts))
        self.command("ack", "--wake", first)
        self.assertEqual(1, len(self.documents("inbox")))
        self.assertNotEqual(first, self.documents("inbox")[0]["id"])
        self.assertEqual(2, len(self.prompts))

    def test_blocked_notice_never_sends_approval_and_resume_wakes(self):
        self.arm("--persistent")
        self.turn("blocked")
        self.assertIn('"status":"blocked"', self.prompts[0])
        self.command("ack", "--wake", self.documents("inbox")[0]["id"])
        self.turn()
        self.assertEqual(2, len(self.prompts))

    def test_duplicate_status_and_focus_do_not_loop(self):
        self.arm("--persistent")
        self.turn()
        self.emit("done")
        self.emit("idle")
        self.assertEqual(1, len(self.prompts))
        self.assertEqual(1, len(self.documents("inbox")))

    def test_busy_coordinator_coalesces_turns(self):
        self.arm("--persistent")
        self.target_status = "working"
        for _ in range(5):
            self.turn()
        self.assertEqual(1, len(self.documents("inbox")))
        self.assertEqual([], self.prompts)
        self.target_status = "idle"
        wake._flush()
        self.assertEqual(1, len(self.prompts))

    def test_cancel_removes_subscription_and_pending_wakes(self):
        self.arm("--persistent")
        self.turn()
        self.turn()
        self.command("cancel", "--watch", self.documents("watches")[0]["id"])
        self.assertEqual([], self.documents("watches"))
        self.assertEqual([], self.documents("inbox"))
        self.turn()
        self.assertEqual(1, len(self.prompts))

    def test_same_registration_is_idempotent(self):
        self.arm("--persistent")
        original = self.documents("watches")[0]["id"]
        self.arm("--persistent")
        self.assertEqual([original], [item["id"] for item in self.documents("watches")])

    def test_reused_name_with_new_session_cannot_complete_old_watch(self):
        self.arm("--persistent")
        self.source["agent_session"] = {"kind": "id", "value": "session-2"}
        self.turn()
        self.assertEqual([], self.documents("inbox"))
        with self.assertRaises(SystemExit):
            self.arm("--persistent")

    def test_wrong_identity_cannot_register_or_settle(self):
        self.source["name"] = "unrelated"
        with self.assertRaises(SystemExit):
            self.arm("--persistent")
        self.source["name"] = "example_author"
        self.arm("--persistent")
        self.source["workspace_id"] = "other"
        self.turn()
        self.assertEqual([], self.documents("inbox"))

    def test_registration_during_work_and_restart_flush(self):
        self.source["agent_status"] = "working"
        self.arm("--persistent")
        # No stop hook arrived; a bounded startup flush recovers settlement.
        self.source["agent_status"] = "done"
        wake._flush()
        self.assertEqual(1, len(self.prompts))

    def test_fast_stop_hook_arrives_before_working_hook(self):
        self.arm("--persistent")
        self.source["agent_status"] = "done"
        self.emit("done")
        self.emit("working")
        self.assertEqual(1, len(self.prompts))
        self.assertEqual("done", self.documents("inbox")[0]["status"])

    def test_persistent_watch_rejects_self_target_by_name_or_pane(self):
        for target in ["example_author", "w2:p1"]:
            with mock.patch.object(wake, "_configured_consumers", return_value=[
                {"root": str(self.state_root), "target": target}
            ]), self.assertRaises(SystemExit):
                self.arm("--persistent")

    def test_retry_budget_survives_new_turns(self):
        self.arm("--persistent")
        self.prompt_fails = True
        for _ in range(10):
            self.turn()
        self.assertEqual(wake.MAX_NOTIFY_ATTEMPTS, len(self.prompts))
        self.assertEqual(1, len(self.documents("inbox")))
        self.assertEqual("transport unavailable", self.documents("inbox")[0]["last_error"])


if __name__ == "__main__":
    unittest.main()
