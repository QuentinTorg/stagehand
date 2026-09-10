# Stagehand Status Board

A terminal pane beside the orchestrator conversation. It reads existing active YAML/JSON task records and refreshes Herdr workspace labels and named-agent runtime status every five seconds. Workers have no new reporting duties. The orchestrator keeps saving and reconciling task state; ordinary code handles presentation.

Two views separate task work from the orchestrator conversation. **Tasks** shows workspaces, concise workflow status, the next actor, and PR links. Selecting a row previews recent agent output; role buttons switch between its Author/Reviewer or worker. **Details** preserves purpose, next action, PR links, and technical context. **Orchestrator** provides recent output and a general message box for setup or new tasks. Red needs you, yellow is in progress, and green is handed off (including ready PRs awaiting human merge). Runtime `idle` or `done` never advances workflow state. Archived/cleaned tasks are omitted; invalid records and unavailable live state produce visible warnings.

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

Click a task row to select it. Recent output follows the latest lines; scroll back with the mouse wheel or **[ / ]**, and press End to follow again. Narrow tables keep the next actor and whole PR numbers, omitting the status column. A clickable `+N` opens the remaining PR links in **Details** (**i**), which also preserves full workspace names and status text. Arrow keys or j/k select a workspace; Page Up/Down page. **?** opens keyboard help and update warnings. Mouse input requires terminal mouse forwarding.

Click a PR number or repo#number label to open the recorded HTTPS link in your default browser. Public GitHub and GitHub Enterprise URLs retain their original host. These are board mouse targets, so no OS URL-handler changes or modified-click shortcuts are needed.

The task list has a position indicator and clickable scroll rail. Delayed-refresh warnings expose update health, not agent progress. **Details** shows raw workflow/agent state, record age, and workspace paths; duplicate names retain workspace IDs. The board never merges or removes workspaces. For a plain-text snapshot:

```sh
python3 plugins/status-board/board.py --tasks /absolute/stagehand/.orchestrator/tasks --once
```

Add `--offline` to skip live Herdr queries and disable messaging/navigation. The board never modifies task records, reads private session files, consumes wakes, or changes task resources. It can show stale saved progress, so the orchestrator still owns reconciliation. A saved expected role indicates the next actor, not permission to proceed.

The [common task record](../../skills/orchestrating-development/assets/task-record.yaml) supplies a short status, next actor/action, and human-attention flag. Older records still render, but scope/review counters are ignored. Tasks needing you appear first, ongoing work next, and completed work last. Agent next steps are not labeled as human requests.

## Navigation and orchestrator view

- **Tasks** (**t**): select a workspace; **Open workspace** (**o**) opens its existing Herdr session for direct agent work. Selecting a row alone never navigates away.
- **Orchestrator** (**c**): read recent output and discuss setup or new work. Arrows, **[ / ]**, Page Up/Down, and the wheel scroll. **Follow latest** or End resumes following new output.
- **Open orchestrator** (**o** in that view, or **Shift-O** anywhere) opens its native agent pane for full conversations, permissions, or setup problems. It does not approve prompts or start agents.

With no tasks, the orchestrator view and general message box remain available. General messages go unchanged to the orchestrator, without a task header, and have their own saved draft. Use them to discuss new work or finish setup. The preview reads at most 120 terminal lines per background refresh, not a guaranteed complete or final assistant response; it may contain tool output. Keep the native session accessible. The board must already be installed; initial installation still happens outside it.

Workspace previews use the same agent-neutral terminal formatting, reading only the selected agent (up to 120 lines/32 KB), not every task. They are recent context, not a generated summary or proof of completion. Purpose remains saved separately under Details. Reads do not focus agents or mark them seen. Messages from either workspace view still go through the orchestrator, never directly to the previewed worker.

## Message the orchestrator

Select a task and click the message box in the bottom detail panel to type there; **m** also focuses it. The selected task stays visible while you write. Enter or Send submits, Ctrl-J inserts a newline (Ctrl-G also sends), and Esc or clicking another task keeps the draft. Arrow keys, Home/End, Backspace, and Delete edit text. The board adds only the workspace name and Herdr workspace ID (task ID only if no workspace exists), then sends your exact text to `workflow_orchestrator` in the same Herdr workspace. It never contacts a worker directly or treats delivery as workflow progress.

Drafts are saved per task privately under `board-drafts/` beside the configured task directory and restored when you reopen the composer. Clicking away or switching tasks never sends; **x Clear** discards only the selected task's draft. Escape leaves editing but does not close the board. Successful delivery clears the draft. Busy/blocked or missing orchestrators leave the draft unsent. Unconfirmed delivery keeps it too: inspect the orchestrator before retrying to avoid duplicate requests. There is no automatic retry or queue. Avoid typing simultaneously in the orchestrator terminal while sending from the board, since both use its interactive input.

## Appearance

Filled buttons and underlined PRs are clickable; other labels are information. Cyan marks the active view and Send when a draft has text. Other controls are neutral; workflow colors are limited to dots, counts, and human-action alerts. The preview highlights an existing Conversation recap heading and collapses decorative terminal rules and repeated blank lines; it does not generate summaries or hide response text.

The layout adapts to terminal cells, not physical pixels. It supports compact panes from 60 columns × 24 rows through ultrawide layouts; narrower tables hide secondary columns, and prose/editor lines stop growing on wide screens. Tiny panes show a resize hint without discarding drafts. No per-widget font-size changes are required.

Font, text/background defaults, and ANSI colors come from the hosting terminal. The board sets no fixed RGB palette or font. Herdr's separate UI palette is not exposed by its plugin API, so a custom Herdr UI theme may differ from the terminal colors. Status meaning stays human-oriented: red needs you, yellow is ongoing, green is a completed workflow handoff (not Herdr's transient unseen-response state).

## Validation

```sh
python3 -m unittest discover -s plugins/status-board/tests -v
```
