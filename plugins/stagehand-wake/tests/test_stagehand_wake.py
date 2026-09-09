import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "stagehand-wake"
loader = importlib.machinery.SourceFileLoader("stagehand_wake", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
wake = importlib.util.module_from_spec(spec)
loader.exec_module(wake)


class WakePluginTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config_dir = self.root / "plugin-config"
        self.workspace = self.root / "stagehand"
        self.config_dir.mkdir()
        self.workspace.mkdir()
        (self.config_dir / "config.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "workspaces": [
                        {"root": str(self.workspace), "orchestrator": "workflow_orchestrator"}
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

    def arm(self):
        args = wake._parser().parse_args(
            [
                "arm",
                "--workspace",
                str(self.workspace),
                "--task",
                "example",
                "--role",
                "author",
                "--workspace-id",
                "w2",
                "--workspace-label",
                "example-workspace",
                "--pane",
                "w2:p1",
                "--agent",
                "example_author",
            ]
        )
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
        directory = self.workspace / ".orchestrator" / "wake" / name
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
            if args[:3] == ("agent", "get", "workflow_orchestrator"):
                return {"result": {"agent": {"agent_status": "idle"}}}, None
            if args[:3] == ("agent", "prompt", "workflow_orchestrator"):
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
        self.assertTrue(prompts[0].startswith("STAGEHAND_WAKE ["))
        self.assertTrue(self.documents("inbox")[0]["notified"])
        self.assertEqual("fired", self.documents("watches")[0]["state"])

    def test_settled_without_observed_working_is_ignored(self):
        self.arm()
        with mock.patch.object(wake, "_herdr") as herdr:
            self.emit("idle")
        herdr.assert_not_called()
        self.assertEqual([], self.documents("inbox"))
        self.assertEqual("armed", self.documents("watches")[0]["state"])

    def test_busy_orchestrator_defers_until_flush(self):
        self.arm()
        orchestrator_status = ["working", "idle"]
        prompts = []

        def herdr(*args):
            if args[:3] == ("agent", "get", "w2:p1"):
                return {"result": {"agent": {"agent_status": "done"}}}, None
            if args[:3] == ("agent", "get", "workflow_orchestrator"):
                return {
                    "result": {"agent": {"agent_status": orchestrator_status.pop(0)}}
                }, None
            if args[:3] == ("agent", "prompt", "workflow_orchestrator"):
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


if __name__ == "__main__":
    unittest.main()
