#!/usr/bin/env python3
"""Show saved task progress and route human messages to the orchestrator."""

import argparse
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


def clipped(text, width):
    return text if len(text) <= width else text[:max(0, width - 1)] + "…"


def columns(width, pr_width=9):
    name = min(48, width // 3)
    stage = min(36, width // 4)
    return name, stage, max(10, width - name - stage - pr_width - 6)


def pr_labels(row):
    return [("#" + urlsplit(url).path.rstrip("/").split("/")[-1], url) for url in row.get("prs", [])]


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


def detail_lines(row, width):
    action = row["action"] or f"Nothing needed from you. Next: {row['next']}."
    entries = [("PURPOSE: " + row["objective"], 0, None),
               ("YOUR ACTION: " + action, 1 if row["action"] else 0, None),
               (row["stage"] + " · " + row["roles"], 0, None),
               (row["repository"] + " · record saved " + row["saved"] + " ago", 0, None)]
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
    context = {"task": row["id"], "workspace": row["label"],
               "workspace_id": row["workspace_id"], "repository": row["repository"],
               "pull_request": row["pr"], "pull_requests": row["prs"], "task_directory": str(args.tasks)}
    prompt = ("Human message from the Stagehand board. Interpret the human request using your normal workflow; "
              "routing context is not evidence of a workflow transition.\n"
              + "Routing context: " + json.dumps(context, ensure_ascii=False)
              + "\n\nHuman request:\n" + message)
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


def draw_message_box(screen, row, message, active=False):
    height, width = screen.getmaxyx()
    top, inner = max(0, height - 8), max(1, width - 6)
    preview = textwrap.wrap(clean(message), inner)[:3] if message else []
    title = "Message orchestrator · " + row["label"]
    lines = ["┌ " + clipped(title, max(1, width - 8)) + " ",
             *["│ " + (preview[i] if i < len(preview) else "") for i in range(3)],
             "│ [ Send ]  " + ("Ctrl-G sends · Esc keeps draft" if active else "Click inside to type"),
             "└" + "─" * max(0, width - 4) + "┘"]
    if not message and not active:
        lines[1] = "│ Tell the orchestrator what you need for this workspace…"
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


def compose(screen, args, row, inline=False, send_now=False):
    path = draft_path(args, row)
    try:
        message = path.read_text() if path.exists() else ""
    except OSError:
        return "Cannot read saved draft; nothing sent."
    cursor, note = len(message), "Ctrl-G sends · Esc keeps draft and returns · Enter adds a line"
    while True:
        height, width = screen.getmaxyx()
        line_width = max(1, width - (6 if inline else 4))
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
            draw_message_box(screen, row, "", active=True)
            content = []
        else:
            screen.erase()
            content = [(0, "MESSAGE ORCHESTRATOR"), (1, "About: " + row["label"]),
                       (2, "Repository: " + row["repository"])]
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
                elif input_y <= y < input_y + visible:
                    target_y, target_x = offset + y - input_y, max(0, x - input_x)
                    cursor = min(range(len(positions)), key=lambda i: (abs(positions[i][0] - target_y), abs(positions[i][1] - target_x)))
                elif y < height - 8:
                    try:
                        save_draft(path, message)
                        curses.ungetmouse((0, x, y, 0, curses.BUTTON1_CLICKED))
                    except (OSError, curses.error):
                        note = "Could not leave editor; draft remains here."
                        continue
                    curses.curs_set(0)
                    return "Draft saved."
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
        if key == "\x07":
            if not message.strip():
                note = "Write a message before sending."
                continue
            try:
                save_draft(path, message)
            except OSError:
                note = "Cannot save draft. Nothing sent."
                continue
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
        elif isinstance(key, str) and (key.isprintable() or key in ("\n", "\r")):
            key = "\n" if key == "\r" else key
            message, cursor = message[:cursor] + key + message[cursor:], cursor + len(key)
        else:
            continue
        try:
            save_draft(path, message)
        except OSError:
            note = "Draft save failed; keep this window open until saved."


def display(screen, args):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    # Request ordinary terminal mouse reporting; Herdr retains its own pane chrome.
    curses.mousemask(curses.ALL_MOUSE_EVENTS)
    curses.mouseinterval(150)
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        for number, color in enumerate((curses.COLOR_RED, curses.COLOR_YELLOW, curses.COLOR_GREEN, curses.COLOR_WHITE), 1):
            curses.init_pair(number, color, -1)
        for number, color in enumerate((curses.COLOR_RED, curses.COLOR_YELLOW, curses.COLOR_GREEN), 5):
            curses.init_pair(number, curses.COLOR_WHITE, color)
    screen.timeout(200)
    selected, selected_id, refresh_at, rows, warnings = 0, None, 0, [], []
    notice = ""
    detail_offset, detail_task = 0, None
    while True:
        if time.monotonic() >= refresh_at:
            rows, warnings = snapshot(args.tasks, args.offline)
            selected = next((i for i, row in enumerate(rows) if row["id"] == selected_id), min(selected, max(0, len(rows) - 1)))
            refresh_at = time.monotonic() + args.interval
        height, width = screen.getmaxyx()
        selected = min(selected, max(0, len(rows) - 1))
        current = rows[selected] if rows else None
        selected_id = current["id"] if current else None
        if selected_id != detail_task:
            detail_offset, detail_task = 0, selected_id
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
                pass  # A resize or wide glyph can exhaust the last cell.

        attention = sum(bool(row["action"]) for row in rows)
        put(0, "STAGEHAND  /  WORKSPACE STATUS", bold=True)
        put(1, f"{attention} need your attention   ·   {sum(r['color'] == 2 for r in rows)} in progress   ·   {sum(r['color'] == 3 for r in rows)} complete", bold=True)
        legend_x = 1
        for label, color in (("● Needs you", 1), ("● Ongoing", 2), ("● Handoff complete", 3)):
            try:
                screen.addnstr(2, legend_x, label, max(0, width - legend_x - 1),
                               curses.color_pair(color) if curses.has_colors() else 0)
            except curses.error:
                pass
            legend_x += len(label) + 3
        header = {"label": "WORKSPACE", "stage": "WORKFLOW", "roles": "AGENTS / NEXT", "pr": "PR"}
        # Share column widths across rows while reserving room for individual PR links.
        pr_width = max(9, min(width // 3, max((len(", ".join(label for label, _ in pr_labels(row))) for row in rows), default=9)))
        put(4, "    " + table_line(header, max(1, width - 6), pr_width), bold=True)
        table_links = {}
        # Keep selected-task instructions visible even when the task list is long.
        visible = max(1, (height - 17) // 2)
        offset = max(0, selected - visible + 1)
        for i, row in enumerate(rows[offset:offset + visible], offset):
            marker = "›" if i == selected else " "
            y = 5 + i - offset + (1 if i > selected else 0)
            put(y, f"{marker} ● {table_line(row, max(1, width - 6), pr_width)}", row["color"], highlight=i == selected)
            if width - 6 >= 100 and row["prs"]:
                pr_x = 5 + sum(columns(width - 6, pr_width)) + 6
                end = min(pr_x + pr_width, width - 2)
                for label, url in pr_labels(row):
                    length = min(len(label), end - pr_x)
                    if length <= 0:
                        break
                    try:
                        style = curses.A_UNDERLINE | (curses.color_pair(row["color"]) if curses.has_colors() else 0)
                        if i == selected:
                            style |= curses.A_REVERSE
                        screen.addnstr(y, pr_x, label, length, style)
                        table_links.setdefault(y, []).append((pr_x, pr_x + length, url))
                    except curses.error:
                        pass
                    pr_x += len(label) + 2
            if i == selected:
                put(y + 1, ("      ↳ " + row["objective"]).ljust(max(1, width - 3)), color=4 + row["color"])
        if not rows:
            put(5, "No readable active tasks." if warnings else "No active tasks.")

        detail_y = 5 + visible + 2
        put(detail_y, "─" * max(0, width - 3))
        detail_height = max(1, height - 9 - (detail_y + 2))
        details = detail_lines(current, width) if current else []
        detail_offset = max(0, min(detail_offset, len(details) - detail_height))
        detail_links = {}
        if current:
            scroll_hint = f" · {detail_offset + 1}–{min(len(details), detail_offset + detail_height)}/{len(details)} · wheel or [ ] to scroll" if len(details) > detail_height else ""
            put(detail_y + 1, current["label"] + scroll_hint, current["color"], bold=True)
            for i, (line, color, links) in enumerate(details[detail_offset:detail_offset + detail_height]):
                y = detail_y + 2 + i
                put(y, line, color, bold=bool(color))
                detail_links[y] = [(left + 1, right + 1, url) for left, right, url in links]
                for left, right, _ in links:
                    try:
                        screen.addnstr(y, left + 1, line[left:right], right - left, curses.A_UNDERLINE)
                    except curses.error:
                        pass
            try:
                path = draft_path(args, current)
                draft = path.read_text() if path.exists() else ""
                draw_message_box(screen, current, draft)
            except OSError:
                put(height - 7, "Cannot read saved draft.", 1)
        if notice:
            put(height - 2, notice, bold=True)
        if warnings:
            put(height - 2, "! " + " | ".join(warnings), 1)
        try:
            screen.addnstr(height - 1, 0, " Click message box to type · Click PR: open links · ↑↓ select · [ ] scroll details · a next action · r refresh · q close", max(0, width - 1), curses.A_DIM)
        except curses.error:
            pass
        screen.refresh()
        key = screen.getch()
        if key in (ord("q"), 27):
            return
        if key in (ord("r"), curses.KEY_RESIZE):
            refresh_at = 0
        elif key in (curses.KEY_DOWN, ord("j")):
            selected += 1
        elif key in (curses.KEY_UP, ord("k")):
            selected = max(0, selected - 1)
        elif key == curses.KEY_NPAGE:
            selected += visible
        elif key == curses.KEY_PPAGE:
            selected = max(0, selected - visible)
        elif key == ord("a") and rows:
            selected = next((i % len(rows) for i in range(selected + 1, selected + len(rows) + 1) if rows[i % len(rows)]["action"]), selected)
        elif key in (ord("["), ord("]")):
            detail_offset += -1 if key == ord("[") else 1
        elif key == ord("m") and current:
            notice = compose(screen, args, current, inline=True)
        elif key == curses.KEY_MOUSE:
            event = mouse_event()
            if event:
                kind, x, y, delta = event
                if kind == "wheel":
                    if detail_y <= y < height - 8:
                        detail_offset += delta
                    else:
                        selected = max(0, min(len(rows) - 1, selected + delta))
                elif current and height - 8 <= y < height - 2:
                    notice = compose(screen, args, current, inline=True,
                                     send_now=y == height - 4 and 3 <= x <= 10)
                else:
                    index = clicked_row(x, y, width, offset, visible, len(rows), selected)
                    is_preview = y == 6 + selected - offset
                    if index is not None:
                        selected = index
                        if not is_preview and kind == "select":
                            for left, right, url in table_links.get(y, []):
                                if left <= x < right:
                                    open_pr(url)
                                    break
                    elif kind == "select":
                        for left, right, url in detail_links.get(y, []):
                            if left <= x < right:
                                open_pr(url)
                                break


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
