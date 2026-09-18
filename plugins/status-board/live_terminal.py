"""One focus-scoped Herdr terminal attachment, rendered into a confined grid."""

import asyncio
import base64
import json
import os
import threading
import time
from collections import namedtuple
import agent_binding
from preview_links import LinkStream

try:
    import pyte
except ImportError:
    pyte = None


MAX_FRAME = 16 * 1024 * 1024


if pyte is not None:
    LinkChar = namedtuple("LinkChar", (*pyte.screens.Char._fields, "hyperlink"), defaults=(None,))

    class LinkScreen(pyte.Screen):
        hyperlink = None

        def set_link(self, value):
            self.hyperlink = value

        def reset(self):
            self.hyperlink = None
            super().reset()

        def draw(self, data):
            # Store the target on the cells themselves: edits, wrapping, and
            # scrolling then move links with their text, not stale coordinates.
            self.cursor.attrs = LinkChar(*self.cursor.attrs[:len(pyte.screens.Char._fields)], self.hyperlink)
            try:
                super().draw(data)
            finally:
                # Erased spaces must not inherit a previously drawn link.
                self.cursor.attrs = self.cursor.attrs._replace(hyperlink=None)


class TerminalGrid:
    """Interpret terminal operations in memory, never against the board terminal."""

    def __init__(self):
        self.screen, self.stream, self.sequence = None, None, None

    def feed(self, frame):
        if frame.get("type") == "terminal.closed":
            raise RuntimeError(frame.get("reason", "Attachment closed"))
        if frame.get("type") != "terminal.frame" or frame.get("encoding") != "ansi":
            raise ValueError("Unexpected terminal frame")
        cols, rows, seq = frame["width"], frame["height"], frame["seq"]
        if (any(type(n) is not int or n < 1 for n in (cols, rows, seq))
                or cols > 1000 or rows > 500 or cols * rows > 100000):
            raise ValueError("Invalid terminal dimensions or sequence")
        resized = self.screen is None or (self.screen.columns, self.screen.lines) != (cols, rows)
        if ((resized and frame.get("full") is not True)
                or (self.sequence is not None and seq != self.sequence + 1)):
            raise ValueError("Discontinuous terminal frames")
        if resized or frame.get("full"):
            self.screen = LinkScreen(cols, rows)
            stream = pyte.Stream(self.screen)
            self.stream = LinkStream(stream.feed, self.screen.set_link)
        self.stream.feed(base64.b64decode(frame["bytes"], validate=True))
        self.sequence = seq
        # Immutable cells cross the thread boundary; partial frames stay local.
        return tuple(tuple(self.screen.buffer[y][x] for x in range(cols)) for y in range(rows))


def source_identity(snapshot, target, viewer):
    if isinstance(target, dict):
        agent = agent_binding.resolve(target, snapshot["agents"])
    else:
        name, workspace = target
        matches = [agent for agent in snapshot["agents"]
                   if agent.get("name") == name and agent.get("workspace_id") == workspace]
        if len(matches) != 1:
            raise ValueError("Agent no longer uniquely matches this workspace")
        agent = matches[0]
    if not agent.get("pane_id") or agent["pane_id"] == viewer or not agent.get("terminal_id"):
        raise ValueError("Missing source terminal or attempted self-preview")
    return agent


async def read_snapshot():
    process = await asyncio.create_subprocess_exec(
        os.environ.get("HERDR_BIN_PATH", "herdr"), "api", "snapshot",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        output, error = await asyncio.wait_for(process.communicate(), 1.5)
        if process.returncode:
            raise RuntimeError(error.decode(errors="replace").strip() or "Herdr unavailable")
        return json.loads(output)["result"]["snapshot"]
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


class LivePreview:
    """UI calls never block on Herdr; the worker exclusively owns its CLI child."""

    def __init__(self):
        self.available = pyte is not None and os.environ.get("HERDR_ENV") == "1" and bool(os.environ.get("HERDR_PANE_ID"))
        self.viewer = os.environ.get("HERDR_PANE_ID")
        self.lock, self.stopping = threading.Lock(), threading.Event()
        self.target, self.size, self.generation, self.scroll_delta = None, (1, 1), 0, 0
        self.state = {"status": "paused", "message": "Select a conversation", "cells": ()}
        self.thread = None
        self.input_epoch, self.interacting, self.pending_input = 0, None, ""

    def end_input(self):
        with self.lock:
            self.interacting, self.pending_input = None, ""

    def begin_input(self):
        with self.lock:
            if self.state["status"] != "live":
                return None
            self.interacting = self.input_epoch
            return self.input_epoch

    def send_input(self, text, epoch):
        with self.lock:
            # Consent belongs to this attachment, never its replacement or a
            # newly selected agent. Never replay input after a reconnect.
            if (epoch != self.interacting or epoch != self.input_epoch
                    or self.state["status"] != "live" or len(self.pending_input) + len(text) > 65536):
                return False
            self.pending_input += text
            return True

    def _invalidate_input(self):
        self.input_epoch += 1
        self.interacting, self.pending_input = None, ""

    def update(self, target, size):
        with self.lock:
            if target != self.target:
                self._invalidate_input()
                self.target, self.scroll_delta = target, 0
                self.generation += 1
                self.state = {"status": "connecting", "message": "Connecting…", "cells": ()}
            self.size = size
            state = self.state
        if target is not None and self.available and self.thread is None:
            self.thread = threading.Thread(target=lambda: asyncio.run(self._run()), name="board-live-terminal", daemon=True)
            self.thread.start()
        return state

    def retry(self):
        with self.lock:
            self._invalidate_input()
            self.generation += 1

    def scroll(self, delta):
        with self.lock:
            self.scroll_delta = max(-1000, min(1000, self.scroll_delta + delta))

    def close(self):
        self.stopping.set()
        if self.thread is not None:
            self.thread.join(timeout=5)

    def _publish(self, generation, **state):
        with self.lock:
            if generation == self.generation:
                if state.get("status") in {"paused", "connecting", "unavailable"}:
                    self._invalidate_input()
                self.state = dict(self.state, **state, input_epoch=self.input_epoch)

    async def _run(self):
        process = reading = errors = None
        active_generation, identity, grid = -1, None, None
        failed, focused, next_check, started, sent_size = False, False, 0, 0, None

        async def detach():
            nonlocal process, reading, errors, identity, grid
            if process is not None:
                # EOF on control stdin releases the size lease. Never stop the
                # source agent; bounded termination concerns only our CLI child.
                process.stdin.close()
                try:
                    await asyncio.wait_for(process.wait(), 1)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                for task in (reading, errors):
                    if task is not None:
                        task.cancel()
                await asyncio.gather(*(task for task in (reading, errors) if task is not None), return_exceptions=True)
            process = reading = errors = identity = grid = None

        async def command(value):
            process.stdin.write((json.dumps(value) + "\n").encode())
            await asyncio.wait_for(process.stdin.drain(), .5)

        try:
            while not self.stopping.is_set():
                with self.lock:
                    generation, target, size = self.generation, self.target, self.size
                    scroll, self.scroll_delta = self.scroll_delta, 0
                try:
                    if generation != active_generation:
                        await detach()
                        active_generation, failed, focused, next_check = generation, False, False, 0
                        self._publish(generation, status="connecting", message="Connecting…", cells=())
                    if target is None or failed:
                        await asyncio.sleep(.05)
                        continue
                    if time.monotonic() >= next_check:
                        snapshot = await read_snapshot()
                        # Selection may change while a slow query is in flight.
                        with self.lock:
                            if generation != self.generation:
                                continue
                        agent = source_identity(snapshot, target, self.viewer)
                        panes = {pane["pane_id"]: pane for pane in snapshot["panes"]}
                        viewer = panes.get(self.viewer, {})
                        focused = (snapshot.get("focused_pane_id") == self.viewer
                                   and snapshot.get("focused_tab_id") == viewer.get("tab_id")
                                   and snapshot.get("focused_workspace_id") == viewer.get("workspace_id"))
                        current_identity = (agent["pane_id"], agent["terminal_id"],
                                            (agent.get("agent_session") or {}).get("value"))
                        if identity is not None and identity != current_identity:
                            raise ValueError("Source agent changed")
                        self._publish(generation, agent_status=agent.get("agent_status", "unknown"),
                                      agent_kind=agent.get("agent"))
                        if not focused:
                            await detach()
                            self._publish(generation, status="paused", message="Paused · focus this pane for live output")
                        elif process is None:
                            cols, rows = size
                            if cols < 1 or rows < 1 or cols * rows > 100000:
                                raise ValueError("Preview area is outside supported dimensions")
                            process = await asyncio.create_subprocess_exec(
                                os.environ.get("HERDR_BIN_PATH", "herdr"), "terminal", "session", "control",
                                agent["pane_id"], "--cols", str(cols), "--rows", str(rows),
                                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE, limit=MAX_FRAME)
                            identity, grid, started, sent_size = current_identity, TerminalGrid(), time.monotonic(), size
                            reading = asyncio.create_task(process.stdout.readline())
                            errors = asyncio.create_task(process.stderr.read(65536))
                            self._publish(generation, status="connecting", message="Connecting…", cells=())
                        next_check = time.monotonic() + .5
                    if process is not None:
                        if size != sent_size:
                            await command({"type": "terminal.resize", "cols": size[0], "rows": size[1]})
                            sent_size = size
                        if scroll:
                            # Mouse navigation remains local; only explicit
                            # interaction mode may forward human keystrokes.
                            await command({"type": "terminal.scroll", "direction": "up" if scroll < 0 else "down",
                                           "lines": abs(scroll), "source": "wheel", "column": 0, "row": 0})
                        with self.lock:
                            text, self.pending_input = self.pending_input, ""
                            if (text and generation == self.generation
                                    and self.interacting == self.input_epoch):
                                # Write while holding the identity lock so a UI
                                # view switch cannot redirect queued input.
                                process.stdin.write((json.dumps({"type": "terminal.input", "text": text}) + "\n").encode())
                            else:
                                text = ""
                        if text:
                            await asyncio.wait_for(process.stdin.drain(), .5)
                        if reading.done():
                            line = reading.result()
                            if not line:
                                reason = errors.result().decode(errors="replace").strip() if errors.done() else "Attachment ended"
                                raise RuntimeError(reason or "Attachment ended")
                            frame = json.loads(line)
                            cells = grid.feed(frame)
                            self._publish(generation, status="live", message="Live", cells=cells,
                                          size=(frame["width"], frame["height"]), received_at=time.monotonic(),
                                          cursor=None if grid.screen.cursor.hidden else
                                          (grid.screen.cursor.x, grid.screen.cursor.y))
                            reading = asyncio.create_task(process.stdout.readline())
                        elif grid.sequence is None and time.monotonic() - started > 5:
                            raise TimeoutError("No terminal frame received")
                    await asyncio.sleep(.02)
                except agent_binding.ControllerUnavailable as error:
                    await detach()
                    self._publish(generation, status="connecting", message=str(error), cells=())
                    next_check = time.monotonic() + 1
                except (OSError, ValueError, KeyError, TypeError, RuntimeError, asyncio.TimeoutError) as error:
                    await detach()
                    failed = True
                    self._publish(generation, status="unavailable", cells=(),
                                  message=f"Live preview stopped: {error}. Press Ctrl-P then r to retry or use Snapshots in Settings.")
        finally:
            await detach()
