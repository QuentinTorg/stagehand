# Live terminal experiment

Isolated proof of native wrapping, colors, and attachment ownership. It does not
replace the board, install hooks, or change agent instructions. Requires Herdr
0.9.0 with `terminal session control`, Python 3.10+, and a Unix terminal.

From a **dedicated preview pane**, run:

```sh
python3 /absolute/stagehand/plugins/status-board/experimental/live_preview.py <source-pane-id>
```

Focus the preview pane to attach. The source terminal redraws at the preview's
dimensions; Herdr streams its rendered ANSI frames directly to the host terminal.
No text rewrapping, snapshot parser, or additional rendering dependency is used.
This is a whole-pane experiment, not yet an embedded conversation panel.

- No keystrokes are sent to the source. **q / Esc / Ctrl-C** exits.
- Leaving the preview pane releases the attachment and exits. Herdr restores
  desktop sizing. The focus check runs every 250 ms, with a 1.5-second query
  timeout; loss of reliable focus information also ends the attachment.
- The experiment never requests `--takeover`. An existing phone/terminal
  attachment wins. If Heeler takes over afterward, this preview exits instead
  of reconnecting. Run it again explicitly when wanted.
- Only the selected source is resized; the source agent is not restarted.
  Source rendering in its desktop pane can look different while attached.
- Herdr's session focus is the authority. Multiple desktop clients may change
  that focus; losing it conservatively detaches. Desktop application focus
  outside Herdr is not currently monitored.

Start with disposable sample terminals. Validate narrow/wide resizing, colors,
focus-loss detachment, restored source dimensions, and phone coexistence before
considering board integration. The normal board and its local drafts remain
unchanged. Embedding this stream needs a confined terminal surface; do not write
whole-screen frames directly over the curses board.

`sample_terminal.py` provides a disposable resize/color source (Ctrl-C stops it).
On Herdr 0.9.0, a live transport check exercised 80×24, 50×15, and 120×30 frames,
true-color ANSI, restored desktop dimensions, and yielding to a second control
attachment using `--takeover`. Focus-loss and query-failure cleanup have automated
coverage. Actual Heeler phone coexistence and embedded rendering remain untested.

```sh
python3 -m unittest discover -s plugins/status-board/experimental -p 'test_*.py' -v
```
