# Stagehand Status Board

A terminal pane beside the orchestrator conversation. It reads existing active YAML/JSON task records and refreshes Herdr workspace labels and named-agent runtime status every five seconds. Workers have no new reporting duties. The orchestrator keeps saving and reconciling task state; ordinary code handles presentation.

The board shows a compact workspace table with workflow stage, review cycle, agents, and PR number. Only the selected workspace expands an indented objective preview, highlighted together with its heading; details show the complete purpose. Decisions needing you appear first, followed by completed handoffs and ongoing work; filename order is preserved within each group. Select a row to see its human action, repository, full PR URL, and record age in a fixed detail area. Green means orchestration is complete, including a finalized PR awaiting human merge. Runtime `idle` or `done` never advances workflow state. Archived/cleaned tasks are omitted, and invalid records or unavailable live state produce visible warnings.

## Setup

Requires Herdr 0.8.2+, Python 3.10+ with curses, and PyYAML. Use your existing Python environment or an isolated environment in the control workspace:

```sh
python3 -m venv /absolute/stagehand/.local/board-venv
/absolute/stagehand/.local/board-venv/bin/pip install -r /absolute/stagehand/plugins/status-board/requirements.txt
herdr plugin link /absolute/stagehand/plugins/status-board
herdr plugin enable quentintorg.stagehand-board
```

Inspect the current layout and reuse an existing board before opening another. Keep the orchestrator conversation in place and open the board below it (or to its right when preferred). Substitute its exact pane ID and the configured task directory:

```sh
herdr plugin pane open --plugin quentintorg.stagehand-board --entrypoint board \
  --placement split --target-pane <orchestrator-pane-id> --direction down --no-focus \
  --env STAGEHAND_TASKS_DIR=/absolute/stagehand/.orchestrator/tasks \
  --env PATH="/absolute/stagehand/.local/board-venv/bin:$PATH"
```

The explicit task directory scopes the board to this controller; it never discovers other control workspaces. Herdr installation is per-user, but this command opens a pane only in the selected workspace. No startup hook creates panes automatically. Closing the board stops only its display process.

Click a task row to select it. The lower panel contains its full details; scroll there with the mouse wheel or **[ / ]**. There is no separate detail screen. Arrow keys or j/k select a workspace; Page Up/Down page; a jumps to the next human action; r refreshes; q closes. Underlined PR links open GitHub, including Enterprise hosts. Multiple PRs appear as comma-separated, individually clickable numbers. The lower panel shows their full URLs, including any that do not fit in the table. Narrow panes hide table columns, but the lower panel retains all PR links. Mouse input requires terminal mouse forwarding. A plain-text snapshot is also available:

Click a PR number or its full URL to open the recorded HTTPS link in your default browser. Public GitHub and GitHub Enterprise URLs retain their original host. These are board mouse targets, so no OS URL-handler changes or modified-click shortcuts are needed.

```sh
python3 plugins/status-board/board.py --tasks /absolute/stagehand/.orchestrator/tasks --once
```

Add `--offline` to skip live Herdr queries and disable messaging. The board never modifies task records, reads transcripts, consumes wakes, or changes task resources. It can show stale saved progress, so the orchestrator still owns reconciliation. A saved expected role indicates the next actor, not permission to proceed.

## Message the orchestrator

Select a task and click the message box in the bottom detail panel to type there; **m** also focuses it. The selected task stays visible while you write. Enter adds a line, Ctrl-G or Send submits, and Esc or clicking another task keeps the draft. Arrow keys, Home/End, Backspace, and Delete edit text. The board attaches the selected task ID, workspace, repository, and PR links as routing context, then sends your exact text to `workflow_orchestrator` in the same Herdr workspace. It never contacts a worker directly or treats delivery as workflow progress.

Drafts are saved privately under `board-drafts/` beside the configured task directory and restored when you reopen the composer. Successful delivery clears the draft. Busy/blocked or missing orchestrators leave the draft unsent. Unconfirmed delivery keeps it too: inspect the orchestrator before retrying to avoid duplicate requests. There is no automatic retry or queue. Avoid typing simultaneously in the orchestrator terminal while sending from the board, since both use its interactive input.

## Appearance

Font, text/background defaults, and ANSI colors come from the hosting terminal. The board sets no fixed RGB palette or font. Herdr's separate UI palette is not exposed by its plugin API, so a custom Herdr UI theme may differ from the terminal colors. Status meaning stays human-oriented: red needs you, yellow is ongoing, green is a completed workflow handoff (not Herdr's transient unseen-response state).

## Validation

```sh
python3 -m unittest discover -s plugins/status-board/tests -v
```
