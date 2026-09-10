#!/usr/bin/env python3
"""Show saved task progress and route human messages to the orchestrator."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import curses
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import time
from urllib.parse import urlsplit
import webbrowser

import yaml


COMPLETE = {"ready-for-team-review", "review-complete", "delegated-complete", "merged", "closed"}
ROLES = ("author", "reviewer", "worker", "workspace_agent")


def mapping(value):
    return value if isinstance(value, dict) else {}


def clean(value):
    # Task text is data: never let terminal control characters affect the display.
    return " ".join("".join(c for c in str(value or "") if c.isprintable() or c.isspace()).split())


def read_tasks(directory):
    tasks, warnings = [], []
    if not directory.is_dir():
        return [], [f"Task directory unavailable: {directory}"]
    try:
        paths = sorted(directory.iterdir())
    except OSError as error:
        return [], [f"Cannot list task directory: {clean(error)}"]
    for path in paths:
        if path.suffix not in {".yaml", ".yml", ".json"} or not path.is_file():
            continue
        try:
            task = yaml.safe_load(path.read_text())
            if not isinstance(task, dict) or not task.get("task_id") or not isinstance(task.get("state"), dict):
                raise ValueError("expected task_id and state mapping")
            if task["state"].get("name") == "cleaned":
                continue
            tasks.append((task, path.stat().st_mtime))
        except (OSError, ValueError, yaml.YAMLError) as error:
            # A partial save must be visible, not silently presented as no tasks.
            warnings.append(f"Cannot read {path.name}: {clean(error)}")
    return tasks, warnings


def inventory():
    if os.environ.get("HERDR_ENV") != "1":
        return None, None, ["Live state unavailable: not running inside Herdr"]
    try:
        result = []
        for group, key in (("workspace", "workspaces"), ("agent", "agents")):
            reply = subprocess.run(
                [os.environ.get("HERDR_BIN_PATH", "herdr"), group, "list"],
                capture_output=True, text=True, timeout=3, check=True,
            )
            rows = json.loads(reply.stdout)["result"][key]
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise ValueError("invalid inventory response")
            result.append(rows)
        return *result, []
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        return None, None, [f"Live state unavailable: {clean(error)}"]


def age(timestamp, now):
    seconds = max(0, int(now - timestamp))
    return f"{seconds}s" if seconds < 60 else f"{seconds // 60}m" if seconds < 3600 else f"{seconds // 3600}h"


def pr_links(task):
    links = []

    def collect(value):
        if isinstance(value, dict):
            if "url" in value:
                collect(value["url"])
            else:
                for child in value.values():
                    collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
        elif isinstance(value, str):
            try:
                parsed = urlsplit(value)
                parts = parsed.path.rstrip("/").split("/")
                if parsed.scheme == "https" and parsed.hostname and len(parts) >= 5 and parts[-2] == "pull" and parts[-1].isdigit() and value not in links:
                    links.append(value)
            except ValueError:
                pass

    # Read PR collections, not historical URLs embedded in decisions or event logs.
    for field in ("pull_request", "pull_requests", "follow_up_pull_requests", "stacked_pull_request"):
        collect(task.get(field))
    return links


def task_summary(task, modified, workspaces, agents, now):
    state = task["state"]
    stage = clean(state.get("name", "unknown"))
    workspace = mapping(task.get("workspace"))
    workspace_id = workspace.get("id")
    live = next((w for w in workspaces or [] if w.get("workspace_id") == workspace_id), None)
    label = clean((live or {}).get("label") or workspace.get("label") or task.get("display_name") or task["task_id"])
    if live and sum(w.get("label") == live.get("label") for w in workspaces) > 1:
        label += f" ({workspace_id})"
    if workspace_id and workspaces is not None and live is None:
        label += " [workspace missing]"
    elif not workspace_id:
        label += " [workspace not created]"
    color = 3 if stage in COMPLETE else 1 if state.get("attention_required") else 2
    review = mapping(task.get("review"))
    rounds = review.get("rounds_this_scope", 0)
    scope = mapping(task.get("scope")).get("version", 1)
    details = stage.replace("-", " ")
    if review:
        details += f" · r{rounds} done"
        if isinstance(rounds, int) and stage == "reviewing":
            details += f" · reviewing r{rounds + 1}"
        elif stage == "resolving":
            details += f" · fixing r{rounds}"
    if scope != 1:
        details += f" · scope {scope}"
    expected = mapping(task.get("event_recovery")).get("expected_role")
    next_actor = "you" if state.get("attention_required") or stage == "ready-candidate" else None if stage in COMPLETE else expected
    role_text = []
    for role in ROLES:
        identity = mapping(task.get("agents")).get(role)
        if not identity:
            continue
        # Names can be reused elsewhere; require the recorded workspace as well.
        found = next((a for a in agents or [] if a.get("name") == identity and a.get("workspace_id") == workspace_id), None)
        status = clean(found.get("agent_status", "unknown")) if found else "unavailable" if agents is None else "missing"
        role_text.append(f"{role.replace('_', ' ').title()} {status}")
    roles = "; ".join(role_text) or "No managed roles"
    if next_actor:
        roles += f" → {clean(next_actor)}"
    repository = clean(mapping(task.get("repository")).get("name"))
    prs = pr_links(task)
    pr = prs[0] if prs else ""
    action = None
    if state.get("attention_required"):
        action = clean(state.get("attention_reason")) or "Human decision needed; ask the orchestrator."
    elif stage == "ready-candidate":
        action = "Authorize reviewer finalization."
    elif stage == "ready-for-team-review":
        action = "Review the ready PR on GitHub; merge when satisfied."
    return {"id": str(task["task_id"]), "label": label, "color": color,
            "phase": stage, "rounds": rounds,
            "location": clean(mapping((live or {}).get("worktree")).get("checkout_path")),
            "objective": clean(task.get("objective")) or "No objective recorded.",
            "workspace_id": workspace_id,
            "stage": details, "roles": roles, "repository": repository,
            "pr": pr, "prs": prs, "action": action, "saved": age(modified, now),
            "next": clean(next_actor) or ("Complete" if stage in COMPLETE else "Awaiting workflow update")}


def snapshot(directory, offline=False):
    tasks, warnings = read_tasks(directory)
    workspaces, agents, live_warnings = (None, None, ["Saved records only; live state not queried"]) if offline else inventory()
    warnings.extend(live_warnings)
    now = time.time()
    rows = [task_summary(task, modified, workspaces, agents, now) for task, modified in tasks]
    # Surface decisions first without changing saved workflow state or task order on disk.
    rows.sort(key=lambda row: (0 if row["action"] and row["color"] != 3 else 1 if row["action"] else 2))
    return rows, warnings


def herdr_call(*arguments):
    return subprocess.run([os.environ.get("HERDR_BIN_PATH", "herdr"), *arguments],
                          capture_output=True, text=True, timeout=3, check=True).stdout


def controller_identity():
    agent = json.loads(herdr_call("agent", "get", "workflow_orchestrator"))["result"]["agent"]
    workspace = os.environ.get("HERDR_WORKSPACE_ID")
    if not workspace or agent.get("workspace_id") != workspace or not agent.get("pane_id"):
        raise ValueError("Orchestrator is not in this control workspace")
    return agent


def controller_snapshot(offline=False):
    if offline or os.environ.get("HERDR_ENV") != "1":
        return {"status": "offline", "output": "Live orchestrator output is unavailable in offline mode."}
    try:
        agent = controller_identity()
        # Read a bounded terminal preview, not private session files or a model summary.
        output = herdr_call("agent", "read", agent["pane_id"], "--source", "recent-unwrapped", "--lines", "120")
        return {"status": clean(agent.get("agent_status", "unknown")), "output": output[-32000:]}
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        return {"status": "unavailable", "output": f"Cannot read orchestrator: {clean(error)}\nOpen its native session to check setup or permissions."}


def board_snapshot(directory, offline=False):
    rows, warnings = snapshot(directory, offline)
    return rows, warnings, controller_snapshot(offline)


def open_target(args, row=None):
    if args.offline or os.environ.get("HERDR_ENV") != "1":
        return "Navigation requires a live Herdr session."
    try:
        if row is None:
            agent = controller_identity()
            herdr_call("agent", "focus", agent["pane_id"])
            return "Opened orchestrator."
        target = row.get("workspace_id")
        if not target:
            return "This task has no workspace yet."
        workspace = json.loads(herdr_call("workspace", "get", target))["result"]["workspace"]
        if workspace.get("workspace_id") != target:
            raise ValueError("Workspace identity changed")
        herdr_call("workspace", "focus", target)
        return f"Opened {row['label']}."
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        return f"Could not open target: {clean(error)}"


def controller_lines(controller, width):
    width = min(width, 124)
    status = controller["status"]
    hint = {"blocked": "Needs you — open orchestrator for its permission or question dialog.",
            "working": "Working — messages can be sent when it is ready.",
            "idle": "Ready for a message, setup question, or new task.",
            "done": "Ready for a message, setup question, or new task."}.get(status, "Open orchestrator to check its state.")
    content = [hint, "Recent terminal output (may include tools or omit earlier responses):", ""]
    # Preserve line breaks/indentation without allowing terminal control characters.
    content += ["".join(c for c in line.expandtabs(4) if c.isprintable())
                for line in controller["output"].splitlines()]
    lines = []
    for line in content:
        color = 0
        # Style the terminal's own recap; do not infer or generate a new summary.
        if line.strip(" ─━-_").casefold() == "conversation recap":
            line, color = "CONVERSATION RECAP", 10
        # Repeated terminal rules crowd out prose in the smaller preview panel.
        if line.strip() and set(line.strip()) <= set("─━-_"):
            wrapped = [""]
        else:
            wrapped = textwrap.wrap(line, max(1, width - 4), replace_whitespace=False) or [""]
        for text in wrapped:
            if text or not lines or lines[-1][0]:
                lines.append((text, color, []))
    return lines


def help_lines(width, warnings):
    text = ["Tasks: select a workspace to see its next action, purpose, and PRs.",
            "Orchestrator: discuss setup or new work, and read recent agent output.",
            "", "Open workspace / Open orchestrator switches to the native Herdr session.",
            "Use the native session for direct agent work, permissions, or the full transcript.",
            "", "m or click the box: write a message. All messages go to the orchestrator.",
            "Enter: send. Ctrl-J: newline. Esc or click away: save without sending.",
            "Clear removes only the current draft. Task and general drafts stay separate.",
            "", "t / c: Tasks / Orchestrator. o: open the current workspace or orchestrator.",
            "Up/Down or wheel: select tasks or scroll output. [ / ]: scroll task details.",
            "Page Up/Down: page. End / Follow latest: follow orchestrator output.",
            "a: next task needing you. i: task info. r: refresh. q: close this board."]
    if warnings:
        text += ["", "UPDATE WARNINGS", *warnings]
    return [(line, 0, []) for paragraph in text
            for line in (textwrap.wrap(paragraph, max(1, min(width - 4, 110))) or [""])]


def clipped(text, width):
    return text if len(text) <= width else text[:max(0, width - 1)] + "…"


def columns(width, pr_width=9):
    budget = max(1, width - pr_width - 6)
    name, stage = min(48, budget // 2), min(30, budget // 3)
    return name, stage, min(20, max(1, budget - name - stage))


def pr_labels(row):
    return [("#" + urlsplit(url).path.rstrip("/").split("/")[-1], url) for url in row.get("prs", [])]


def task_stage(row):
    phase = row.get("phase", "")
    label = {"ready-candidate": "Ready to finalize", "ready-for-team-review": "Ready on GitHub",
             "decision-required": "Needs a decision", "delegated-complete": "Work complete",
             "review-complete": "Review complete", "implementation-ready": "Ready for review",
             "reviewing": "In review", "resolving": "Fixing findings"}.get(phase, phase.replace("-", " ").capitalize())
    rounds = row.get("rounds", 0)
    if isinstance(rounds, int) and phase in {"reviewing", "resolving"}:
        label += f" · round {rounds + 1 if phase == 'reviewing' else rounds}"
    return label or row["stage"]


def task_next(row):
    if row["color"] == 3:
        return "GitHub review" if row.get("phase") == "ready-for-team-review" else "—"
    if row["action"]:
        return "You"
    actor = row["next"]
    return actor.replace("_", " ").capitalize() if actor not in {"Awaiting workflow update", "Complete"} else "Agents"


def open_pr(url):
    # Open the recorded host, never reconstruct an Enterprise URL as github.com.
    try:
        parsed = urlsplit(url)
        if parsed.scheme == "https" and parsed.hostname and not parsed.username:
            return webbrowser.open(url, new=2)
    except (ValueError, webbrowser.Error):
        pass
    return False


def table_line(row, width, pr_width=9):
    if width < 100:
        name_width = max(12, width // 2)
        return f"{clipped(row['label'], name_width):<{name_width}}  {row['stage']}"
    name_width, stage_width, roles_width = columns(width, pr_width)
    pr = ", ".join(label for label, _ in pr_labels(row)) or row.get("pr") or "—"
    return (f"{clipped(row['label'], name_width):<{name_width}}  "
            f"{clipped(row['stage'], stage_width):<{stage_width}}  "
            f"{clipped(row['roles'], roles_width):<{roles_width}}  {clipped(pr, pr_width)}")


def detail_lines(row, width, info=False):
    width = min(width, 114)
    action = row["action"] or ("Work is handed off; no action is required here." if row["color"] == 3 else f"No action needed from you. Waiting on {task_next(row).lower()}.")
    entries = [("NEXT: " + action, 1 if row["action"] and row["color"] != 3 else 0, None),
               ("", 0, None), (row["objective"], 0, None), ("", 0, None)]
    if info:
        entries += [(row["stage"] + " · " + row["roles"], 0, None),
                    (row["repository"] + " · record saved " + row["saved"] + " ago", 0, None)]
    if info and row.get("location"):
        entries.append((f"WORKSPACE: {row['workspace_id']} · {row['location']}", 0, None))
    lines = [(line, color, []) for text, color, _ in entries
             for line in (textwrap.wrap(text, max(1, width - 4)) or [""])]
    text, links = "PRs: ", []
    for url in row["prs"]:
        parts = urlsplit(url).path.rstrip("/").split("/")
        label = parts[-3] + "#" + parts[-1]
        if links:
            text += ", "
        links.append((len(text), len(text) + len(label), url))
        text += label
    # Retain exact URL targets and character spans when compact labels wrap.
    offset = 0
    for line in textwrap.wrap(text if links else "No pull request", max(1, width - 4)):
        start = text.find(line, offset) if links else 0
        end = start + len(line)
        spans = [(max(left, start) - start, min(right, end) - start, url)
                 for left, right, url in links if left < end and right > start]
        lines.append((line, 0, spans))
        offset = end
    return lines


def mouse_event():
    """Translate terminal mouse reports; unsupported mouse input leaves keys usable."""
    try:
        _, x, y, _, buttons = curses.getmouse()
    except curses.error:
        return None
    if buttons & curses.BUTTON4_PRESSED:
        return ("wheel", x, y, -1)
    if buttons & getattr(curses, "BUTTON5_PRESSED", 0):
        return ("wheel", x, y, 1)
    if buttons & curses.BUTTON1_DOUBLE_CLICKED:
        return ("open", x, y, 0)
    if buttons & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED):
        return ("select", x, y, 0)
    return None


def clicked_row(x, y, width, offset, visible, count, expanded=None):
    line = y - 5
    if expanded is not None and offset <= expanded < offset + visible and line > expanded - offset:
        line -= 1  # The selected objective belongs to the same task as its heading.
    index = offset + line
    if 1 <= x < width - 1 and 0 <= line < visible and 0 <= index < count:
        return index
    return None


def draft_path(args, row):
    if row is None:
        return args.tasks.parent / "board-drafts" / "orchestrator.txt"
    identity = hashlib.sha256(row["id"].encode()).hexdigest()
    return args.tasks.parent / "board-drafts" / (identity + ".txt")


def save_draft(path, text):
    # Atomic private drafts survive a display restart without touching task records.
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def send_message(args, row, message):
    if args.offline or os.environ.get("HERDR_ENV") != "1":
        return False, "Sending requires a live Herdr session. Draft kept."
    # The controller already owns the task record; send identity, not a duplicate brief.
    prompt = message
    if row is not None:
        target = row['workspace_id'] or f"task: {row['id']}"
        prompt = f"Human message about {row['label']} ({target}):\n\n{message}"
    command = [os.environ.get("HERDR_BIN_PATH", "herdr"), "agent"]
    try:
        result = subprocess.run(command + ["get", "workflow_orchestrator"],
                                capture_output=True, text=True, timeout=5, check=True)
        agent = json.loads(result.stdout)["result"]["agent"]
        if not os.environ.get("HERDR_WORKSPACE_ID") or agent.get("workspace_id") != os.environ["HERDR_WORKSPACE_ID"]:
            return False, "Orchestrator is not in this control workspace. Draft kept."
        if agent.get("agent_status") not in {"idle", "done"}:
            return False, "Orchestrator is busy or blocked. Draft kept; send when it is ready."
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return False, "Cannot verify the orchestrator. Nothing sent; draft kept."
    try:
        # No automatic retry: a timeout may occur after Herdr has delivered the input.
        result = subprocess.run(command + ["prompt", "workflow_orchestrator", prompt],
                                capture_output=True, text=True, timeout=10, check=True)
        if json.loads(result.stdout)["result"]["type"] == "agent_prompted":
            return True, "Delivered to orchestrator (not yet processed)."
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        pass
    return False, "Delivery unconfirmed. Check orchestrator before retrying; draft kept."


def draw_message_box(screen, row, message, active=False, can_send=None):
    height, width = screen.getmaxyx()
    top, inner = max(0, height - 8), max(1, min(120, width - 6))
    preview = textwrap.wrap(clean(message), inner)[:3] if message else []
    title = "Message orchestrator · " + (row["label"] if row else "General / new task")
    lines = ["┌ " + clipped(title, max(1, width - 8)) + " ",
             *["│ " + (preview[i] if i < len(preview) else "") for i in range(3)],
             "│ [ Send ] [ x Clear ]  " + ("Enter sends · Ctrl-J newline · Esc saves" if active else "m / click to write"),
             "└" + "─" * max(0, width - 4) + "┘"]
    if not message and not active:
        lines[1] = "│ " + ("Tell the orchestrator what you need for this workspace…" if row else "Ask a question, finish setup, or start a new task…")
    box_width = max(4, width - 3)
    heading = clipped(title, max(1, box_width - 4))
    lines[0] = "┌ " + heading + " " + "─" * max(0, box_width - len(heading) - 4) + "┐"
    for i in range(1, 5):
        lines[i] = "│ " + clipped(lines[i][2:], box_width - 4).ljust(box_width - 4) + " │"
    lines[-1] = "└" + "─" * (box_width - 2) + "┘"
    for i, text in enumerate(lines):
        try:
            screen.move(top + i, 0)
            screen.clrtoeol()
            screen.addnstr(top + i, 1, clipped(text, max(1, width - 3)), max(0, width - 2))
        except curses.error:
            pass
    draw_button(screen, top + 4, 3, "  Send  ", active=bool(message.strip()) if can_send is None else can_send)
    draw_button(screen, top + 4, 12, "  x Clear  ")


def compose(screen, args, row, inline=False, send_now=False, clear_now=False):
    path = draft_path(args, row)
    try:
        message = path.read_text() if path.exists() else ""
    except OSError:
        return "Cannot read saved draft; nothing sent."
    if clear_now:
        try:
            save_draft(path, "")
            return "Draft cleared; nothing sent."
        except OSError:
            return "Cannot clear saved draft; nothing sent."
    cursor, note = len(message), "Enter sends · Ctrl-J newline · Esc keeps draft and returns"
    while True:
        height, width = screen.getmaxyx()
        line_width = max(1, min(120, width - (6 if inline else 4)))
        lines, positions = [""], []
        for character in message:
            positions.append((len(lines) - 1, len(lines[-1])))
            if character == "\n":
                lines.append("")
            else:
                lines[-1] += character
                if len(lines[-1]) >= line_width:
                    lines.append("")
        positions.append((len(lines) - 1, len(lines[-1])))
        cy, cx = positions[cursor]
        input_y = max(1, height - 7) if inline else 4
        input_x = 3 if inline else 1
        visible = 3 if inline else max(1, height - 7)
        offset = max(0, cy - visible + 1)
        if inline:
            # Editing stays in the bottom panel; leave the selected task visible above.
            draw_message_box(screen, row, "", active=True, can_send=bool(message.strip()))
            content = []
        else:
            screen.erase()
            content = [(0, "MESSAGE ORCHESTRATOR"), (1, "About: " + (row["label"] if row else "General / new task")),
                       (2, "Repository: " + (row["repository"] if row else "Not task-specific"))]
        content += [(height - 2, note), (height - 1, " Click outside / Esc to return" if inline else " [ Send ]  [ Back ]")]
        for y, text in content:
            try:
                screen.move(y, 0)
                screen.clrtoeol()
                screen.addnstr(y, 1, text, max(0, width - 2))
            except curses.error:
                pass
        for i, line in enumerate(lines[offset:offset + visible]):
            try:
                screen.addnstr(input_y + i, input_x, line, line_width)
            except curses.error:
                pass
        try:
            curses.curs_set(1)
            screen.move(min(height - 3, input_y + cy - offset), input_x + cx)
        except curses.error:
            pass
        screen.refresh()
        if send_now:
            key, send_now = "\x07", False
        else:
            try:
                key = screen.get_wch()
            except curses.error:
                continue
        if key == curses.KEY_MOUSE:
            event = mouse_event()
            if inline and event and event[0] == "select":
                _, x, y, _ = event
                if y == height - 4 and 3 <= x <= 10:
                    key = "\x07"
                elif y == height - 4 and 12 <= x <= 22:
                    try:
                        save_draft(path, "")
                    except OSError:
                        note = "Cannot clear saved draft."
                        continue
                    message, cursor = "", 0
                    note = "Draft cleared; nothing sent."
                elif input_y <= y < input_y + visible:
                    target_y, target_x = offset + y - input_y, max(0, x - input_x)
                    cursor = min(range(len(positions)), key=lambda i: (abs(positions[i][0] - target_y), abs(positions[i][1] - target_x)))
                elif not (1 <= x < width - 2 and height - 8 <= y < height - 2):
                    try:
                        save_draft(path, message)
                    except OSError:
                        note = "Could not leave editor; draft remains here."
                        continue
                    # Hand the click back directly; do not synthesize terminal input.
                    return ("Draft saved; nothing sent.", event)
            elif event and event[0] == "select" and event[2] == height - 1:
                key = "\x07" if 2 <= event[1] <= 9 else "\x1b" if 12 <= event[1] <= 19 else key
        if key == "\x1b":
            try:
                save_draft(path, message)
            except OSError:
                note = "Cannot save draft. Copy your text before closing."
                continue
            curses.curs_set(0)
            return "Draft saved. Click the message box to continue."
        if key in ("\r", curses.KEY_ENTER, "\x07"):
            if not message.strip():
                note = "Write a message before sending."
                continue
            try:
                save_draft(path, message)
            except OSError:
                note = "Cannot save draft. Nothing sent."
                continue
            try:
                screen.move(height - 2, 0)
                screen.clrtoeol()
                screen.addnstr(height - 2, 1, "Sending to orchestrator…", max(0, width - 2))
                screen.refresh()
            except curses.error:
                pass
            success, note = send_message(args, row, message)
            if success:
                try:
                    path.unlink()
                except OSError:
                    note += " Saved copy remains; do not resend."
                curses.curs_set(0)
                return note
            continue
        if key in (curses.KEY_BACKSPACE, "\x7f", "\b") and cursor:
            message, cursor = message[:cursor - 1] + message[cursor:], cursor - 1
        elif key == curses.KEY_DC:
            message = message[:cursor] + message[cursor + 1:]
        elif key == curses.KEY_LEFT:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_RIGHT:
            cursor = min(len(message), cursor + 1)
        elif key in (curses.KEY_UP, curses.KEY_DOWN):
            target_y = max(0, cy + (-1 if key == curses.KEY_UP else 1))
            cursor = min(range(len(positions)), key=lambda i: (abs(positions[i][0] - target_y), abs(positions[i][1] - cx)))
        elif key == curses.KEY_HOME:
            cursor = message.rfind("\n", 0, cursor) + 1
        elif key == curses.KEY_END:
            end = message.find("\n", cursor)
            cursor = len(message) if end < 0 else end
        elif isinstance(key, str) and (key.isprintable() or key == "\n"):
            message, cursor = message[:cursor] + key + message[cursor:], cursor + len(key)
        else:
            continue
        try:
            save_draft(path, message)
        except OSError:
            note = "Draft save failed; keep this window open until saved."


def draw_task_frame(screen, width, visible, selected, count, caption):
    # Reserve the outer columns for the frame, independent of table content.
    right, bottom = width - 2, 6 + visible
    if right < 3:
        return
    title = clipped(" " + caption + " ", right - 1)
    top = "┌" + title + "─" * (right - 1 - len(title)) + "┐"
    thumb = 5 + round(selected * visible / max(1, count - 1)) if count > visible else None
    try:
        screen.addnstr(3, 0, top, right + 1)
        for y in range(4, bottom):
            screen.addnstr(y, 0, "│", 1)
            screen.addnstr(y, right, "█" if y == thumb else "│", 1)
        screen.addnstr(bottom, 0, "└" + "─" * (right - 1) + "┘", right + 1)
    except curses.error:
        pass  # A resize may invalidate the frame dimensions mid-draw.


def draw_button(screen, y, x, text, active=False):
    style = curses.A_REVERSE | curses.A_BOLD
    try:
        if curses.has_colors():
            style = curses.color_pair(8 if active else 9) | curses.A_BOLD
    except curses.error:
        pass  # Monochrome/test terminals still get a filled button.
    try:
        height, width = screen.getmaxyx()
        if y >= height - 1 or x + len(text) > width - 1:
            return False
        screen.addnstr(y, x, text, len(text), style)
        return True
    except curses.error:
        return False


def draw_actions(screen, top, width, actions, active=None):
    hits, x, y = [], 1, top
    for action, label in actions:
        text = "  " + label + "  "
        if x > 1 and x + len(text) > width - 1:
            x, y = 1, y + 1
        if len(text) > width - 2:
            continue
        if draw_button(screen, y, x, text, action == active):
            hits.append((y, x, x + len(text), action))
        x += len(text) + 2
    return hits, y + 1


def display(screen, args):
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="board-refresh")
    try:
        return display_loop(screen, args, executor)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def display_loop(screen, args, executor):
    # Preserve Enter (CR) separately from Ctrl-J (LF) for send versus newline.
    curses.nonl()
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    curses.mousemask(curses.BUTTON1_PRESSED | curses.BUTTON4_PRESSED | getattr(curses, "BUTTON5_PRESSED", 0))
    curses.mouseinterval(0)
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        for number, color in enumerate((curses.COLOR_RED, curses.COLOR_YELLOW, curses.COLOR_GREEN, curses.COLOR_WHITE), 1):
            curses.init_pair(number, color, -1)
        for number, color in enumerate((curses.COLOR_RED, curses.COLOR_YELLOW, curses.COLOR_GREEN), 5):
            curses.init_pair(number, curses.COLOR_WHITE, color)
        # Cyan denotes controls; red/yellow/green remain workflow status.
        curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(10, curses.COLOR_CYAN, -1)
    screen.timeout(200)
    selected, selected_id, refresh_at, rows, warnings = 0, None, 0, [], []
    notice, pending, queued_mouse = "", None, None
    refresh_started = None
    detail_offset, detail_task = 0, None
    general, info, show_help = False, False, False
    controller_offset = None
    controller = {"status": "loading", "output": "Waiting for live inventory…"}
    while True:
        # Preserve click coordinates until a blur event is handled; a refresh may
        # otherwise reorder the task rows between leaving the editor and selection.
        if pending is not None and pending.done() and queued_mouse is None:
            selected_id = rows[min(selected, len(rows) - 1)]["id"] if rows else None
            try:
                rows, warnings, controller = pending.result()
            except Exception as error:
                warnings = [f"Refresh failed; showing previous snapshot: {clean(error)}"]
            selected = next((i for i, row in enumerate(rows) if row["id"] == selected_id), min(selected, max(0, len(rows) - 1)))
            refresh_at = time.monotonic() + args.interval
            pending = None
        if pending is None and time.monotonic() >= refresh_at:
            pending = executor.submit(board_snapshot, args.tasks, args.offline)
            refresh_started = time.monotonic()
        height, width = screen.getmaxyx()
        screen.erase()

        def put(y, text, color=0, bold=False, highlight=False, underline=False):
            if not 0 <= y < height - 1:
                return
            style = curses.color_pair(color) if curses.has_colors() else 0
            style |= curses.A_BOLD if bold else 0
            style |= curses.A_REVERSE if highlight else 0
            style |= curses.A_UNDERLINE if underline else 0
            try:
                text = clipped(text, max(1, width - 3))
                if highlight:
                    text = text.ljust(max(1, width - 3))
                screen.addnstr(y, 1, text, max(0, width - 2), style)
            except curses.error:
                pass

        # Avoid overlapping controls on a transient tiny resize. No input is sent.
        if width < 60 or height < 24:
            put(0, "STAGEHAND — enlarge this pane to at least 60 × 24.")
            put(2, "Your drafts are saved. q closes the board.")
            screen.refresh()
            if screen.getch() == ord("q"):
                return
            continue

        selected = min(selected, max(0, len(rows) - 1))
        current = rows[selected] if rows else None
        viewing_controller = general or current is None
        message_target = None if viewing_controller else current
        selected_id = current["id"] if current else None
        if selected_id != detail_task:
            detail_offset, detail_task = 0, selected_id
            info = False

        health = " · Offline" if args.offline else ""
        if pending and time.monotonic() - refresh_started > 2:
            health = " · Updates delayed"
        put(0, "STAGEHAND" + health, bold=True)
        actions, _ = draw_actions(screen, 1, width,
                                 [("task", "Tasks"), ("controller", "Orchestrator"), ("help", "?")],
                                 "help" if show_help else "controller" if viewing_controller else "task")
        legend_x = 1
        for color, label in ((1, "need you"), (2, "in progress"), (3, "handed off")):
            text = f"● {sum(row['color'] == color for row in rows)} {label}"
            try:
                screen.addnstr(2, legend_x, text, max(0, width - legend_x - 1),
                               curses.color_pair(color) if curses.has_colors() else 0)
            except curses.error:
                pass
            legend_x += len(text) + 3

        table_links, detail_links = {}, {}
        visible = max(1, min(12, len(rows), (height - 20) // 2))
        offset = max(0, selected - visible + 1)
        show_tasks = not (viewing_controller or show_help)
        if show_tasks:
            header = {"label": "WORKSPACE", "stage": "STATUS", "roles": "NEXT", "pr": "PR"}
            pr_width = max(9, min(width // 3, max((len(", ".join(label for label, _ in pr_labels(row))) for row in rows), default=9)))
            put(4, "    " + table_line(header, width - 8, pr_width), bold=True)
            for i, row in enumerate(rows[offset:offset + visible], offset):
                marker, y = ("›" if i == selected else " "), 5 + i - offset
                summary = dict(row, stage=task_stage(row), roles=task_next(row))
                # Color only the dot on unselected rows; a long red/yellow row
                # competes with the selected task and its requested action.
                put(y, f"{marker} ● {table_line(summary, width - 8, pr_width)}",
                    highlight=i == selected)
                try:
                    style = curses.color_pair(row["color"]) if curses.has_colors() else 0
                    screen.addnstr(y, 3, "●", 1, style | (curses.A_REVERSE if i == selected else 0))
                except curses.error:
                    pass
                if width - 8 >= 100 and row["prs"]:
                    pr_x = 5 + sum(columns(width - 8, pr_width)) + 6
                    end = min(pr_x + pr_width, width - 2)
                    for label, url in pr_labels(row):
                        length = min(len(label), end - pr_x)
                        if length <= 0:
                            break
                        try:
                            style = curses.A_UNDERLINE | (curses.A_REVERSE if i == selected else 0)
                            screen.addnstr(y, pr_x, label, length, style)
                            table_links.setdefault(y, []).append((pr_x, pr_x + length, url))
                        except curses.error:
                            pass
                        pr_x += len(label) + 2
            draw_task_frame(screen, width, visible, selected, len(rows),
                            f"Workspaces {offset + 1}–{min(len(rows), offset + visible)} of {len(rows)}")
            detail_y = 7 + visible
        else:
            detail_y = 3

        if show_help:
            context_actions = [("help", "Back")]
        elif viewing_controller:
            context_actions = [("open-controller", "Open orchestrator"), ("latest", "Follow latest")]
        else:
            context_actions = [("workspace", "Open workspace"), ("info", "Hide info" if info else "Info")]
        context_hits, title_y = draw_actions(screen, detail_y, width, context_actions)
        actions += context_hits
        detail_height = max(1, height - 9 - (title_y + 1))
        if show_help:
            details = help_lines(width, warnings)
            title, color = "Help · buttons and underlined PRs are clickable", 10
        elif viewing_controller:
            details = controller_lines(controller, width)
            status = {"idle": "Ready for you", "done": "Ready for you", "blocked": "Needs you — open native session",
                      "working": "Working", "unavailable": "Unavailable — check native session"}.get(controller["status"], controller["status"].capitalize())
            title, color = f"Orchestrator · {status}", 1 if controller["status"] in {"blocked", "unavailable"} else 10
        else:
            details = detail_lines(current, width, info)
            title, color = current["label"], 10
        detail_offset = max(0, min(detail_offset, len(details) - detail_height))
        if viewing_controller and not show_help:
            active_offset = max(0, len(details) - detail_height) if controller_offset is None else max(0, min(controller_offset, len(details) - detail_height))
        else:
            active_offset = detail_offset
        scroll_hint = f" · {active_offset + 1}–{min(len(details), active_offset + detail_height)}/{len(details)}" if len(details) > detail_height else ""
        put(title_y, title + scroll_hint, color, bold=True)
        for i, (line, color, links) in enumerate(details[active_offset:active_offset + detail_height]):
            y = title_y + 1 + i
            put(y, line, color, bold=bool(color))
            detail_links[y] = [(left + 1, right + 1, url) for left, right, url in links]
            for left, right, _ in links:
                try:
                    screen.addnstr(y, left + 1, line[left:right], right - left, curses.A_UNDERLINE)
                except curses.error:
                    pass
        try:
            path = draft_path(args, message_target)
            draft = path.read_text() if path.exists() else ""
            draw_message_box(screen, message_target, draft)
        except OSError:
            put(height - 7, "Cannot read saved draft.", 1)
        if warnings:
            put(height - 2, f"Updates need attention ({len(warnings)}) · ? for details", 1)
        elif notice:
            put(height - 2, notice, bold=True)
        try:
            screen.addnstr(height - 1, 0, " m Message · t Tasks · c Orchestrator · ? Help · q Close", width - 1, curses.A_DIM)
        except curses.error:
            pass
        screen.refresh()
        key = curses.KEY_MOUSE if queued_mouse else screen.getch()
        action = None
        if key == ord("q"):
            return
        if key in (ord("r"), curses.KEY_RESIZE):
            refresh_at = 0
        elif key in (ord("t"), ord("c"), ord("?")):
            action = {ord("t"): "task", ord("c"): "controller", ord("?"): "help"}[key]
        elif key == 27:
            show_help = False
        elif key in (ord("o"), ord("O")):
            action = "open-controller" if key == ord("O") or viewing_controller else "workspace"
        elif key == ord("i") and not viewing_controller:
            action = "info"
        elif key == ord("m"):
            notice = compose(screen, args, message_target, inline=True)
        elif key in (curses.KEY_UP, curses.KEY_DOWN, ord("j"), ord("k"), curses.KEY_PPAGE, curses.KEY_NPAGE, ord("["), ord("]")):
            delta = -1 if key in (curses.KEY_UP, ord("k"), curses.KEY_PPAGE, ord("[")) else 1
            if key in (curses.KEY_PPAGE, curses.KEY_NPAGE):
                delta *= detail_height if viewing_controller or show_help else visible
            if viewing_controller and not show_help:
                controller_offset = max(0, active_offset + delta)
            elif show_help or key in (ord("["), ord("]")):
                detail_offset = max(0, active_offset + delta)
            else:
                selected = max(0, min(len(rows) - 1, selected + delta))
        elif key == curses.KEY_END and viewing_controller:
            controller_offset = None
        elif key == ord("a") and rows:
            selected = next((i % len(rows) for i in range(selected + 1, selected + len(rows) + 1) if rows[i % len(rows)]["color"] == 1), selected)
            general, show_help = False, False
        elif key == curses.KEY_MOUSE:
            event, queued_mouse = queued_mouse or mouse_event(), None
            if event:
                kind, x, y, delta = event
                action = next((name for line, left, right, name in actions if y == line and left <= x < right), None) if kind == "select" else None
                if kind == "wheel":
                    if show_tasks and 3 <= y <= 6 + visible:
                        selected = max(0, min(len(rows) - 1, selected + delta))
                    elif viewing_controller and not show_help:
                        controller_offset = max(0, active_offset + delta)
                    else:
                        detail_offset = max(0, active_offset + delta)
                elif kind == "select" and action:
                    pass
                elif kind == "select" and show_tasks and x == width - 2 and 5 <= y <= 5 + visible:
                    selected = round((y - 5) * (len(rows) - 1) / visible)
                elif kind == "select" and height - 8 <= y < height - 2:
                    notice = compose(screen, args, message_target, inline=True,
                                     send_now=y == height - 4 and 3 <= x <= 10,
                                     clear_now=y == height - 4 and 12 <= x <= 22)
                elif kind == "select":
                    index = clicked_row(x, y, width, offset, visible, len(rows)) if show_tasks else None
                    if index is not None:
                        selected = index
                        for left, right, url in table_links.get(y, []):
                            if left <= x < right:
                                open_pr(url)
                                break
                    else:
                        for left, right, url in detail_links.get(y, []):
                            if left <= x < right:
                                open_pr(url)
                                break
        if action == "task":
            general, show_help, detail_offset = False, False, 0
        elif action == "controller":
            general, show_help, controller_offset = True, False, None
        elif action == "help":
            show_help, detail_offset = not show_help, 0
        elif action == "info":
            info, detail_offset = not info, 0
        elif action == "latest":
            controller_offset = None
        elif action == "workspace":
            notice = open_target(args, current) if current else "Select a task workspace first."
        elif action == "open-controller":
            notice = open_target(args)
        if isinstance(notice, tuple):
            notice, queued_mouse = notice
        try:
            curses.curs_set(0)
        except curses.error:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, default=os.environ.get("STAGEHAND_TASKS_DIR"), help="Explicit active task-record directory (or STAGEHAND_TASKS_DIR)")
    parser.add_argument("--once", action="store_true", help="Print one plain-text snapshot")
    parser.add_argument("--offline", action="store_true", help="Read records without Herdr calls")
    parser.add_argument("--interval", type=float, default=5, help="Refresh seconds, minimum 2")
    args = parser.parse_args()
    if args.tasks is None or not args.tasks.is_absolute():
        parser.error("Provide an absolute --tasks path or STAGEHAND_TASKS_DIR; the board never guesses ownership")
    if not 2 <= args.interval <= 3600:
        parser.error("--interval must be between 2 and 3600 seconds")
    if args.once:
        rows, warnings = snapshot(args.tasks, args.offline)
        for warning in warnings:
            print("! " + warning)
        for row in rows:
            print(f"● {row['label']} | {row['stage']} | {row['roles']}")
            print(f"  PURPOSE: {row['objective']}")
            if row["action"]:
                print(f"  YOUR ACTION: {row['action']}")
            print(f"  {row['repository']} | {', '.join(row['prs']) or 'No PR'} | saved {row['saved']} ago")
    elif not sys.stdout.isatty():
        parser.error("Interactive board needs a terminal; use --once for text output")
    else:
        try:
            curses.wrapper(display, args)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
