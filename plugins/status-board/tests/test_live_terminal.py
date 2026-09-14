import asyncio
import base64
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import live_terminal as terminal


def frame(text="hello", seq=1, full=True, cols=20, rows=5):
    return {"type": "terminal.frame", "encoding": "ansi", "seq": seq,
            "full": full, "width": cols, "height": rows,
            "bytes": base64.b64encode(text.encode()).decode()}


def snapshot():
    return {"focused_pane_id": "viewer", "focused_tab_id": "tab", "focused_workspace_id": "workspace",
            "panes": [{"pane_id": "viewer", "tab_id": "tab", "workspace_id": "workspace"}],
            "agents": [{"name": "author", "workspace_id": "workspace", "pane_id": "source",
                        "terminal_id": "terminal", "agent_status": "idle"}]}


@unittest.skipIf(terminal.pyte is None, "Install board requirements for terminal-renderer tests")
class TerminalTests(unittest.IsolatedAsyncioTestCase):
    def test_grid_tracks_cursor_edits_and_preserves_colors(self):
        grid = terminal.TerminalGrid()
        grid.feed(frame("first\r\n\x1b[38;2;249;226;175mYellow"))
        cells = grid.feed(frame("\x1b[1;1Hnew\x1b[K", 2, False))
        self.assertEqual("".join(cell.data for cell in cells[0]).strip(), "new")
        self.assertEqual(cells[1][0].fg, "f9e2af")
        cells = grid.feed(frame("wide", 3, True, 80, 24))
        self.assertEqual((len(cells[0]), len(cells)), (80, 24))

    def test_erase_clipboard_queries_and_cursor_cannot_escape_grid(self):
        grid = terminal.TerminalGrid()
        cells = grid.feed(frame("\x1b]52;c;c2VjcmV0\x07\x1b[2J\x1b[999;999H!"))
        self.assertEqual(len(cells), 5)
        self.assertTrue(all(len(row) == 20 for row in cells))
        self.assertTrue(all(all(c.isprintable() for c in cell.data) for row in cells for cell in row))

    def test_wide_and_combining_cells_retain_positions(self):
        cells = terminal.TerminalGrid().feed(frame("界e\u0301"))
        self.assertEqual(cells[0][0].data, "界")
        self.assertEqual(cells[0][1].data, "")
        self.assertEqual(cells[0][2].data, "é")

    def test_invalid_frames_fail_closed(self):
        for value in (frame(full=False), frame(cols=1000000), frame(seq=-1),
                      dict(frame(), encoding="unknown"), {"type": "terminal.closed", "reason": "taken over"}):
            with self.subTest(value=value), self.assertRaises((RuntimeError, ValueError)):
                terminal.TerminalGrid().feed(value)
        grid = terminal.TerminalGrid()
        grid.feed(frame())
        with self.assertRaises(ValueError):
            grid.feed(frame(seq=3, full=False))

    def test_identity_requires_unique_workspace_match_and_no_self_attach(self):
        value = snapshot()
        self.assertEqual(terminal.source_identity(value, ("author", "workspace"), "viewer")["pane_id"], "source")
        for target, viewer in ((("author", "other"), "viewer"), (("author", "workspace"), "source")):
            with self.assertRaises(ValueError):
                terminal.source_identity(value, target, viewer)
        value["agents"].append(value["agents"][0])
        with self.assertRaises(ValueError):
            terminal.source_identity(value, ("author", "workspace"), "viewer")

    async def test_view_switch_focus_loss_and_takeover_release_without_retry_loop(self):
        view = terminal.LivePreview()
        view.viewer, view.available = "viewer", False
        state, children = snapshot(), []

        def launch(*args, **kwargs):
            child = Mock()
            child.stdout, child.stderr = asyncio.StreamReader(), asyncio.StreamReader()
            child.stdout.feed_data((json.dumps(frame()) + "\n").encode())
            child.stderr.feed_eof()
            child.stdin.drain = AsyncMock()
            child.stdin.close.side_effect = child.stdout.feed_eof
            child.wait = AsyncMock(return_value=0)
            children.append(child)
            return child

        async def until(predicate):
            deadline = time.monotonic() + 3
            while not predicate():
                if time.monotonic() > deadline:
                    self.fail("Terminal worker did not reach expected state")
                await asyncio.sleep(.02)

        with patch.object(terminal, "read_snapshot", AsyncMock(side_effect=lambda: state)), patch.object(
            terminal.asyncio, "create_subprocess_exec", AsyncMock(side_effect=launch)
        ) as start:
            runner = asyncio.create_task(view._run())
            try:
                view.update(("author", "workspace"), (20, 5))
                await until(lambda: view.state["status"] == "live")
                self.assertNotIn("--takeover", start.call_args.args)
                state["focused_pane_id"] = "elsewhere"
                await until(lambda: view.state["status"] == "paused")
                children[0].stdin.close.assert_called_once()
                state["focused_pane_id"] = "viewer"
                await until(lambda: len(children) == 2 and view.state["status"] == "live")
                children[1].stdout.feed_data(b'{"type":"terminal.closed","reason":"taken over"}\n')
                await until(lambda: view.state["status"] == "unavailable")
                await asyncio.sleep(.7)
                self.assertEqual(len(children), 2)
                view.retry()
                await until(lambda: len(children) == 3 and view.state["status"] == "live")
                view.update(None, (20, 5))
                await until(lambda: children[2].stdin.close.called)
                self.assertTrue(all(not child.stdin.write.called for child in children))
            finally:
                view.stopping.set()
                await runner

    def test_switch_clears_old_frame_and_scroll_commands(self):
        view = terminal.LivePreview()
        view.available = False
        view.state = {"cells": ("old",), "status": "live"}
        view.scroll(100000)
        self.assertEqual(view.scroll_delta, 1000)
        self.assertEqual(view.update(("new", "workspace"), (80, 20))["cells"], ())
        self.assertEqual(view.scroll_delta, 0)


if __name__ == "__main__":
    unittest.main()
