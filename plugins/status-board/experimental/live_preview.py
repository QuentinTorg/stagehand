#!/usr/bin/env python3
"""Opt-in, whole-pane terminal preview. No agent input or automatic takeover."""

import argparse
import asyncio
import base64
import json
import os
import signal
import sys
import termios
import tty


HERDR = os.environ.get("HERDR_BIN_PATH", "herdr")
MAX_FRAME = 16 * 1024 * 1024


async def snapshot():
    process = await asyncio.create_subprocess_exec(
        HERDR, "api", "snapshot", stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    try:
        output, error = await asyncio.wait_for(process.communicate(), 1.5)
        if process.returncode:
            raise RuntimeError(error.decode(errors="replace").strip())
        return json.loads(output)["result"]["snapshot"]
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


def focused(state, viewer, target):
    """Uncertain ownership must not keep a hidden preview's size lease alive."""
    panes = {pane["pane_id"]: pane for pane in state["panes"]}
    if viewer == target or viewer not in panes or target not in panes:
        raise RuntimeError("Viewer and source must be distinct existing panes.")
    pane = panes[viewer]
    return (state.get("focused_pane_id") == viewer
            and state.get("focused_tab_id") == pane["tab_id"]
            and state.get("focused_workspace_id") == pane["workspace_id"])


def frame_bytes(frame, previous):
    # Deltas only make sense against the preceding frame. Never show a corrupt
    # screen as live after a missing frame or an unexpected protocol response.
    if frame.get("type") == "terminal.closed":
        raise RuntimeError(frame.get("reason", "Terminal attachment ended."))
    if (frame.get("type") != "terminal.frame" or frame.get("encoding") != "ansi"
            or type(frame.get("seq")) is not int
            or (previous is None and frame.get("full") is not True)
            or (previous is not None and frame["seq"] != previous + 1)):
        raise RuntimeError("Invalid or discontinuous terminal frame stream.")
    return base64.b64decode(frame["bytes"], validate=True)


async def frames(process, write):
    previous = None
    while True:
        line = await asyncio.wait_for(process.stdout.readline(), 5 if previous is None else None)
        if not line:
            return "Terminal attachment ended; no automatic reconnect."
        frame = json.loads(line)
        write(frame_bytes(frame, previous))
        previous = frame["seq"]


async def resize(process, size):
    columns, rows = size
    process.stdin.write((json.dumps({"type": "terminal.resize", "cols": columns,
                                    "rows": rows}) + "\n").encode())
    await process.stdin.drain()


async def watch_focus(process, viewer, target, size, get_size):
    while True:
        await asyncio.sleep(0.25)
        if not focused(await snapshot(), viewer, target):
            return "Preview detached because you left its pane."
        current = get_size()
        if current != size:
            await resize(process, current)
            size = current


async def release(process):
    # Closing stdin asks Herdr to detach. Bound shutdown and reap only the CLI
    # child we own; the source terminal and its foreground agent remain alive.
    process.stdin.close()
    try:
        await asyncio.wait_for(process.wait(), 1)
    except asyncio.TimeoutError:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), 1)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()


async def preview(target, viewer, stop, get_size, write):
    # A no-focus launch can wait safely without attaching or resizing anything.
    while not focused(await snapshot(), viewer, target):
        if stop.is_set():
            return "Preview cancelled."
        await asyncio.sleep(0.25)
    if stop.is_set():
        return "Preview cancelled."
    columns, rows = get_size()
    process = await asyncio.create_subprocess_exec(
        HERDR, "terminal", "session", "control", target,
        "--cols", str(columns), "--rows", str(rows),
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, limit=MAX_FRAME)
    tasks = [asyncio.create_task(frames(process, write)),
             asyncio.create_task(watch_focus(process, viewer, target,
                                             (columns, rows), get_size)),
             asyncio.create_task(stop.wait()),
             asyncio.create_task(process.stderr.read(65536))]
    try:
        # stderr is drained separately but cannot decide lifecycle; a refusal
        # arrives through the frame stream or process exit, not an empty pipe.
        done, _ = await asyncio.wait(tasks[:3], return_when=asyncio.FIRST_COMPLETED)
        for task in tasks[:3]:
            if task in done:
                result = task.result()
                return result if isinstance(result, str) else "Preview closed."
    finally:
        await release(process)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="Exact source pane ID (not the preview pane)")
    args = parser.parse_args()
    viewer = os.environ.get("HERDR_PANE_ID")
    if os.environ.get("HERDR_ENV") != "1" or not viewer or not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("Run inside a dedicated Herdr terminal pane.")
    if args.target == viewer:
        parser.error("Cannot preview this pane itself.")
    descriptor = sys.stdin.fileno()
    original = termios.tcgetattr(descriptor)

    def write(data):
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

    async def run():
        loop = asyncio.get_running_loop()
        stop = asyncio.Event()

        def keyboard():
            # This is a viewer, not a remote-control terminal. No keystrokes,
            # terminal responses, pastes, or approval answers reach the source.
            data = os.read(descriptor, 4096)
            if not data or any(key in data for key in (b"q", b"\x03", b"\x1b")):
                stop.set()

        loop.add_reader(descriptor, keyboard)
        for sig in (signal.SIGTERM, signal.SIGHUP):
            loop.add_signal_handler(sig, stop.set)
        try:
            return await preview(args.target, viewer, stop,
                                 lambda: os.get_terminal_size(sys.stdout.fileno()), write)
        finally:
            loop.remove_reader(descriptor)
            for sig in (signal.SIGTERM, signal.SIGHUP):
                loop.remove_signal_handler(sig)

    try:
        tty.setraw(descriptor)
        write(b"\x1b[?1049h\x1b[2J\x1b[HFocus this pane to preview. q / Esc exits. No input is forwarded.\r\n")
        result = asyncio.run(run())
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        result = f"Preview stopped: {error}"
    finally:
        try:
            write(b"\x1b[?2026l\x1b[0m\x1b[?25h\x1b[?1049l")
        finally:
            termios.tcsetattr(descriptor, termios.TCSADRAIN, original)
    print(result)


if __name__ == "__main__":
    main()
