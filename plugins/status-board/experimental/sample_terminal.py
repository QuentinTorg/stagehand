#!/usr/bin/env python3
"""Disposable resize/color target; no agent, files, or network access."""

import os
import signal
import textwrap


def draw(*_):
    columns, rows = os.get_terminal_size()
    # Redraw from source geometry, as a native agent TUI does on SIGWINCH.
    text = "This sample wraps at the source terminal width, not in the preview. " * 5
    print("\x1b[2J\x1b[H", end="")
    print(f"Source terminal: {columns} columns x {rows} rows")
    print("\x1b[1mBold\x1b[0m  \x1b[38;2;249;226;175mYellow\x1b[0m  "
          "\x1b[38;2;137;180;250mBlue\x1b[0m")
    print(textwrap.fill(text, max(1, columns - 1)), flush=True)


if __name__ == "__main__":
    signal.signal(signal.SIGWINCH, draw)
    draw()
    while True:
        signal.pause()
