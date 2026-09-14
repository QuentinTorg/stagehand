import asyncio
import base64
import json
import unittest
from unittest.mock import AsyncMock, Mock, patch

import live_preview as preview


def state(focus="viewer"):
    return {"focused_pane_id": focus, "focused_tab_id": "tab",
            "focused_workspace_id": "workspace", "panes": [
                {"pane_id": name, "tab_id": "tab", "workspace_id": "workspace"}
                for name in ("viewer", "source")]}


def frame(seq=1, full=True):
    return {"type": "terminal.frame", "seq": seq, "full": full, "encoding": "ansi",
            "bytes": base64.b64encode(b"\x1b[38;2;249;226;175mYellow\x1b[0m").decode()}


class PreviewTests(unittest.IsolatedAsyncioTestCase):
    def test_frame_preserves_native_color_and_cursor_bytes(self):
        self.assertEqual(preview.frame_bytes(frame(), None),
                         b"\x1b[38;2;249;226;175mYellow\x1b[0m")
        self.assertTrue(preview.frame_bytes(frame(2, False), 1))

    def test_discontinuous_invalid_and_takeover_frames_stop(self):
        for value, previous in [(frame(1, False), None), (frame(3, False), 1),
                                ({"type": "terminal.closed", "reason": "taken over"}, 1),
                                ({"type": "unknown"}, None)]:
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                preview.frame_bytes(value, previous)

    def test_focus_requires_matching_pane_tab_and_workspace(self):
        self.assertTrue(preview.focused(state(), "viewer", "source"))
        for key in ("focused_pane_id", "focused_tab_id", "focused_workspace_id"):
            value = state()
            value[key] = "elsewhere"
            self.assertFalse(preview.focused(value, "viewer", "source"))
        for target in ("viewer", "missing"):
            with self.assertRaises(RuntimeError):
                preview.focused(state(), "viewer", target)

    async def test_focus_loss_releases_without_starting_another_process(self):
        process = Mock()
        async def pending_frame():
            await asyncio.Event().wait()
        process.stdout.readline = pending_frame
        process.stderr.read = AsyncMock(return_value=b"")
        process.wait = AsyncMock(return_value=0)
        process.stdin.drain = AsyncMock()
        stop = asyncio.Event()
        with patch.object(preview, "snapshot", AsyncMock(return_value=state())), patch.object(
            preview.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)
        ) as launch, patch.object(preview, "watch_focus", AsyncMock(return_value="left pane")):
            self.assertEqual(await preview.preview("source", "viewer", stop, lambda: (80, 24), Mock()),
                             "left pane")
        launch.assert_awaited_once()
        self.assertNotIn("--takeover", launch.call_args.args)
        self.assertEqual(launch.call_args.args[-4:], ("--cols", "80", "--rows", "24"))
        process.stdin.close.assert_called_once()
        process.stdin.write.assert_not_called()
        process.wait.assert_awaited()

    async def test_resize_only_on_geometry_change_then_detach_on_blur(self):
        process = Mock()
        process.stdin.drain = AsyncMock()
        sizes = Mock(side_effect=[(100, 30), (100, 30)])
        with patch.object(preview, "snapshot", AsyncMock(side_effect=[state(), state(), state("source")])), patch.object(
            preview.asyncio, "sleep", AsyncMock()
        ):
            result = await preview.watch_focus(process, "viewer", "source", (80, 24), sizes)
        self.assertIn("detached", result)
        process.stdin.write.assert_called_once()
        command = json.loads(process.stdin.write.call_args.args[0])
        self.assertEqual(command, {"type": "terminal.resize", "cols": 100, "rows": 30})

    async def test_focus_query_failure_is_not_treated_as_still_focused(self):
        with patch.object(preview, "snapshot", AsyncMock(side_effect=OSError("unavailable"))), patch.object(
            preview.asyncio, "sleep", AsyncMock()
        ), self.assertRaises(OSError):
            await preview.watch_focus(Mock(), "viewer", "source", (80, 24), Mock())

    async def test_cancel_while_unfocused_never_attaches(self):
        stop = asyncio.Event()
        stop.set()
        with patch.object(preview, "snapshot", AsyncMock(return_value=state("source"))), patch.object(
            preview.asyncio, "create_subprocess_exec", AsyncMock()
        ) as launch:
            self.assertEqual(await preview.preview("source", "viewer", stop, Mock(), Mock()),
                             "Preview cancelled.")
        launch.assert_not_called()

    async def test_focus_failure_releases_active_attachment(self):
        process = Mock()
        async def pending_frame():
            await asyncio.Event().wait()
        process.stdout.readline = pending_frame
        process.stderr.read = AsyncMock(return_value=b"")
        process.wait = AsyncMock(return_value=0)
        with patch.object(preview, "snapshot", AsyncMock(return_value=state())), patch.object(
            preview.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)
        ), patch.object(preview, "watch_focus", AsyncMock(side_effect=OSError("unavailable"))), self.assertRaises(OSError):
            await preview.preview("source", "viewer", asyncio.Event(), lambda: (80, 24), Mock())
        process.stdin.close.assert_called_once()
        process.wait.assert_awaited()

    async def test_release_escalates_only_to_owned_child_when_it_will_not_exit(self):
        process = Mock()
        process.wait = AsyncMock(side_effect=[asyncio.TimeoutError, asyncio.TimeoutError, 0])
        await preview.release(process)
        process.stdin.close.assert_called_once()
        process.terminate.assert_called_once()
        process.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
