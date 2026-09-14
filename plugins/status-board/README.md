# Stagehand Status Board

A terminal pane beside the orchestrator conversation. It reads existing active YAML/JSON task records and refreshes Herdr workspace labels and named-agent runtime status every five seconds. Workers have no new reporting duties. The orchestrator keeps saving and reconciling task state; ordinary code handles presentation.

Two views separate task work from the orchestrator conversation. **Tasks** shows workspaces, concise workflow status, the next actor, and PR links. Selecting a row opens **Details**: purpose, next action, PR links, and technical context. Author/Reviewer or worker tabs show recent agent output when requested. **Orchestrator** provides recent output and a general message box for setup or new tasks. Red needs you, yellow is in progress, and green is handed off (including ready PRs awaiting human merge). Runtime `idle` or `done` never advances workflow state. Archived/cleaned tasks are omitted; invalid records and unavailable live state produce visible warnings.

## Setup

Requires Herdr 0.9.0+, Python 3.10+ with curses, PyYAML, and pyte. Use your existing Python environment or an isolated environment in the control workspace:

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

Click a task row to select it. Scroll conversation output with the mouse wheel or **[ / ]**; End scrolls toward the latest output. Next sizes to its labels; Status hides only when the remaining width is too small. Whole PR numbers stay visible. A clickable `+N` opens the remaining PR links in **Details** (**i**), which also preserves full workspace names and status text. Arrow keys or j/k select a workspace; Page Up/Down page. **?** opens keyboard help and update warnings. Mouse input requires terminal mouse forwarding.

Click a PR number or repo#number label to open the recorded HTTPS link in your default browser. Public GitHub and GitHub Enterprise URLs retain their original host. These are board mouse targets, so no OS URL-handler changes or modified-click shortcuts are needed.

The task list has a position indicator and clickable scroll rail. It grows automatically up to 12 rows (fewer in short panes). Drag its bottom border to show more or fewer rows, leaving space for details and messages; click **Auto**, beside the resize grip, to restore the default. Auto uses the active-tab color while automatic sizing is enabled. Manual sizing lasts for the current board session. Delayed-refresh warnings expose update health, not agent progress. **Details** shows raw workflow/agent state, record age, and workspace paths; duplicate names retain workspace IDs. The board never merges or removes workspaces. For a plain-text snapshot:

```sh
python3 plugins/status-board/board.py --tasks /absolute/stagehand/.orchestrator/tasks --once
```

Add `--offline` to skip live Herdr queries and disable messaging/navigation. The board never modifies task records, reads private session files, consumes wakes, or changes task resources. It can show stale saved progress, so the orchestrator still owns reconciliation. A saved expected role indicates the next actor, not permission to proceed.

The [common task record](../../skills/orchestrating-development/assets/task-record.yaml) uses `working` (yellow), `needs-human` (red), or `complete` (green), plus a short summary and next action where needed. That state determines the color; separate attention flags are unnecessary. Completed tasks have no next action even when their workspace is retained. Recognized older states still render; ambiguous or unknown ones get a neutral dot and reconciliation warning instead of guessed progress. Among recognized tasks, human blockers appear first, ongoing work next, and finished work last.

## Navigation and orchestrator view

- **Tasks** (**t**): select a workspace; **Open workspace** (**o**) opens its existing Herdr session for direct agent work. Selecting a row alone never navigates away.
- **Orchestrator** (**c**): view terminal output and discuss setup or new work. Arrows, **[ / ]**, Page Up/Down, and the wheel scroll. Snapshot mode additionally shows “Following latest” and a **Jump to latest** button after scrolling back.
- **Open orchestrator** (**o** in that view, or **Shift-O** anywhere) opens its native agent pane for full conversations, permissions, or setup problems. It does not approve prompts or start agents.

With no tasks, the orchestrator view and general message box remain available. General messages go unchanged to the orchestrator, without a task header, and have their own saved draft. Use them to discuss new work or finish setup. Previews show terminal content, including tool output and prompts, not a guaranteed complete or final assistant response. Keep the native session accessible. The board must already be installed; initial installation still happens outside it.

**Live preview** is the default for Author, Reviewer, worker, and Orchestrator views. While the board pane is focused, one Herdr attachment sizes the selected source terminal to the conversation panel. The source redraws and wraps naturally; pyte interprets its frames in a confined grid so cursor/erase/clipboard commands cannot affect the board's controls. Curses preserves colors, bold, italic, and underline where supported; RGB maps to the hosting palette. Images and advanced terminal-specific styling are not rendered. This is terminal context, not a summary or proof of completion.

Switching conversations, opening Details/Settings/Help, or shrinking below minimum dimensions releases the old attachment. Leaving the board pane pauses it and restores desktop sizing; returning reconnects. Focus checks run in a background worker every 500 ms with a 1.5-second query timeout. This follows Herdr session focus, not OS-level application focus. A source replacement, attachment error, or another viewer taking over stops reconnect attempts: **r** explicitly retries. The board never requests takeover, so it does not displace Heeler. The original desktop pane can render differently while attached.

The live heading distinguishes Live, Paused, Connecting, and stopped/error states. Only dimensions and deliberate scroll actions reach the source; typing, clicks, terminal responses, and approvals never do. Scroll availability depends on the source application; End scrolls toward the latest output. Messages still go through the orchestrator. Purpose and task records are unchanged.

Drag across conversation text to select it; release requests a clipboard copy through Herdr using OSC 52. The visible preview freezes during selection, while the agent continues running. Esc, a new click, scrolling, or changing views clears selection and resumes updates; resizing cancels selection. Copy preserves visible line breaks and omits trailing spaces. Clipboard delivery depends on the host terminal; Shift-drag remains available as a fallback. Buttons, task rows, and divider dragging are unchanged.

Choose **Settings → Preview: Snapshots** to leave source dimensions untouched. This also serves as the fallback when pyte is absent. Snapshot mode uses the bounded reads described above (120 lines/32 KB), only for visible conversations. `recent-unwrapped` removes soft wrapping but retains source hard breaks. Snapshot headings show last successful read age and stale/errors; live mode streams frames instead of polling conversation snapshots. Switching modes preserves drafts.

## Set tasks aside

**Set aside**, beside **Open workspace**, moves the selected task into a collapsed **Later** group. Click that group or press **l** to expand it; select a task and use **Return to active** to bring it back. These controls never stop or dispatch agents, change task YAML, or close workspaces. Main-list totals exclude set-aside tasks; their original colored dots remain visible in Later.

Preferences persist in private `board-state.json` beside the task directory, separate from message drafts. A changed task summary, status, next action, scope, PR linkage, or observed agent activity returns a task to the main list with a notice. Viewing a task, renaming a workspace, and merely rewriting YAML do not. Activity detection uses board refreshes, not a new worker protocol; a whole turn missed between refreshes or while the board is closed requires a changed saved task result to resurface it.

## Message the orchestrator

Select a task and click the message box in the bottom detail panel to type there; **m** also focuses it. The selected task and conversation keep refreshing while you write. Enter or Send submits, Ctrl-J inserts a newline (Ctrl-G also sends), and Esc or clicking another task keeps the draft. Arrow keys, Home/End, Backspace, and Delete edit text. The board adds only the workspace name and Herdr workspace ID (task ID only if no workspace exists), then sends your exact text to `workflow_orchestrator` in the same Herdr workspace. It never contacts a worker directly or treats delivery as workflow progress.

Drafts are saved per task privately under `board-drafts/` beside the configured task directory and restored when you reopen the composer. Clicking away or switching tasks never sends; **x Clear** discards only the selected task's draft. Escape leaves editing but does not close the board. Successful delivery clears the draft. Working orchestrators accept messages only when **Send while working** is enabled; blocked, unknown, or missing orchestrators leave the draft unsent. Unconfirmed delivery keeps it too: inspect the orchestrator before retrying to avoid duplicate requests. There is no automatic retry or queue. Avoid typing simultaneously in the orchestrator terminal while sending from the board, since both use its interactive input.

## Settings and activity

Open **Settings** at the top, or press **s**. Click a setting or press **1 / 2 / 3** to toggle it; Esc returns. Preferences persist alongside Later entries in private `board-state.json`, not task records.

- **Send while working** (default off): permits ordinary Enter / Send during an active turn. Enable it for agents that support mid-turn input. Delivery does not mean the message has been processed. This never bypasses permission dialogs or identity checks.
- **Animation** (default on): rotating dots in the message-box heading indicate that Herdr last reported the orchestrator working. Turn it off for a static Working label. The indicator is visible in both task and orchestrator views, including while typing. It reuses the inventory refresh, not conversation reads; stale observations stop the animation and display Status stale.

- **Preview** (default Live): use a focus-scoped live attachment, or Snapshots to avoid resizing the source. This never changes messaging permissions.

Enter / Send follows the same setting in every view. Ctrl-J inserts a newline; Shift+Enter is not used as a busy-send override because terminals do not consistently distinguish it from Enter.

## Appearance

White baselines join view tabs on their existing rows; navigation buttons remain detached. Preview failures show an error instead of an indefinite loading message.

The message box uses the pane's full interior width and grows from three to at most twelve text rows, using less height in short panes. Longer messages scroll around the cursor; Enter still sends and Ctrl-J inserts a newline. Send/Clear stay at the bottom as the editor grows upward.

Filled buttons and board PR links are clickable; source-colored or underlined text in terminal previews is not a board navigation control. Cyan marks the active view and Send when a draft has text. Magenta marks navigation away from the board; **Open workspace ↗** and **Open orchestrator ↗** sit at the right edge of their menus. Other controls are neutral; workflow colors are limited to dots, counts, and human-action alerts. Live mode preserves terminal layout; snapshot mode collapses decorative rules and repeated blank lines. Neither generates summaries.

The layout adapts to terminal cells, not physical pixels. It supports compact panes from 60 columns × 24 rows through ultrawide layouts; narrower tables hide secondary columns, and task details retain a readability width limit. Conversation previews and message input use the available width. Tiny panes show a resize hint without discarding drafts. No per-widget font-size changes are required.

Font, text/background defaults, and ANSI colors come from the hosting terminal. The board sets no fixed RGB palette or font. Herdr's separate UI palette is not exposed by its plugin API, so a custom Herdr UI theme may differ from the terminal colors. Status meaning stays human-oriented: red needs you, yellow is ongoing, green is a completed workflow handoff (not Herdr's transient unseen-response state).

## Validation

```sh
python3 -m unittest discover -s plugins/status-board/tests -v
```
