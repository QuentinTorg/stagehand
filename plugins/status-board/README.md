# Stagehand Status Board

A read-only terminal pane beside the orchestrator conversation. It renders existing active YAML/JSON task records and refreshes Herdr workspace labels and named-agent runtime status every five seconds. Workers have no new reporting duties. The orchestrator keeps saving and reconciling task state; ordinary code handles presentation.

The board shows a compact workspace table with workflow stage, review cycle, agents, and PR number. Decisions needing you appear first, followed by completed handoffs and ongoing work; filename order is preserved within each group. Select a row to see its human action, repository, full PR URL, and record age in a fixed detail area. Green means orchestration is complete, including a finalized PR awaiting human merge. Runtime `idle` or `done` never advances workflow state. Archived/cleaned tasks are omitted, and invalid records or unavailable live state produce visible warnings.

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

Click a task row to select it; double-click or click its action panel for full details. The mouse wheel moves through tasks or scrolls details; click Back to return. Arrow keys or j/k also select a workspace; Page Up/Down page; a jumps to the next human action; Enter opens details; r refreshes; q closes. Mouse input requires terminal mouse forwarding; keyboard controls remain available. Narrow panes show fewer table columns while full details remain available. A plain-text snapshot is also available:

Click a PR number or its full URL to open the recorded HTTPS link in your default browser. Public GitHub and GitHub Enterprise URLs retain their original host. These are board mouse targets, so no OS URL-handler changes or modified-click shortcuts are needed.

```sh
python3 plugins/status-board/board.py --tasks /absolute/stagehand/.orchestrator/tasks --once
```

Add `--offline` to skip live Herdr queries. The board makes only bounded inventory reads; it never prompts agents, reads transcripts, modifies records, consumes wakes, or changes task resources. It can show stale saved progress, so the orchestrator still owns reconciliation. A saved expected role indicates the next actor, not permission to proceed.

## Validation

```sh
python3 -m unittest discover -s plugins/status-board/tests -v
```
