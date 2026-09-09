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
    pr = clean(mapping(task.get("pull_request")).get("url"))
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
            "pr": pr, "action": action, "saved": age(modified, now),
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


def columns(width):
    name = min(48, width // 3)
    stage = min(36, width // 4)
    return name, stage, max(10, width - name - stage - 15)


def open_pr(url):
    # Open the recorded host, never reconstruct an Enterprise URL as github.com.
    try:
        parsed = urlsplit(url)
        if parsed.scheme == "https" and parsed.hostname and not parsed.username:
            return webbrowser.open(url, new=2)
    except (ValueError, webbrowser.Error):
        pass
    return False


def table_line(row, width):
    if width < 100:
        name_width = max(12, width // 2)
        return f"{clipped(row['label'], name_width):<{name_width}}  {row['stage']}"
    name_width, stage_width, roles_width = columns(width)
    pr_width = 9
    pr = "#" + row["pr"].rstrip("/").split("/")[-1] if row["pr"] else "—"
    return (f"{clipped(row['label'], name_width):<{name_width}}  "
            f"{clipped(row['stage'], stage_width):<{stage_width}}  "
            f"{clipped(row['roles'], roles_width):<{roles_width}}  {clipped(pr, pr_width)}")


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
               "pull_request": row["pr"], "task_directory": str(args.tasks)}
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


def compose(screen, args, row):
    path = draft_path(args, row)
    try:
        message = path.read_text() if path.exists() else ""
    except OSError:
        return "Cannot read saved draft; nothing sent."
    cursor, note = len(message), "Ctrl-G sends · Esc keeps draft and returns · Enter adds a line"
    while True:
        height, width = screen.getmaxyx()
        line_width = max(1, width - 4)
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
        visible = max(1, height - 7)
        offset = max(0, cy - visible + 1)
        screen.erase()
        content = [(0, "MESSAGE ORCHESTRATOR"), (1, "About: " + row["label"]),
                   (2, "Repository: " + row["repository"])]
        content += [(4 + i, line) for i, line in enumerate(lines[offset:offset + visible])]
        content += [(height - 2, note), (height - 1, " [ Send ]  [ Back ]")]
        for y, text in content:
            try:
                screen.addnstr(y, 1, text, max(0, width - 2))
            except curses.error:
                pass
        try:
            curses.curs_set(1)
            screen.move(min(height - 3, 4 + cy - offset), 1 + cx)
        except curses.error:
            pass
        screen.refresh()
        try:
            key = screen.get_wch()
        except curses.error:
            continue
        if key == curses.KEY_MOUSE:
            event = mouse_event()
            if event and event[0] == "select" and event[2] == height - 1:
                key = "\x07" if 2 <= event[1] <= 9 else "\x1b" if 12 <= event[1] <= 19 else key
        if key == "\x1b":
            try:
                save_draft(path, message)
            except OSError:
                note = "Cannot save draft. Copy your text before closing."
                continue
            curses.curs_set(0)
            return "Draft saved. Press m to continue."
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
        for number, color in enumerate((curses.COLOR_RED, curses.COLOR_YELLOW, curses.COLOR_GREEN), 1):
            curses.init_pair(number, color, -1)
    screen.timeout(200)
    selected, selected_id, refresh_at, rows, warnings = 0, None, 0, [], []
    notice = ""
    while True:
        if time.monotonic() >= refresh_at:
            rows, warnings = snapshot(args.tasks, args.offline)
            selected = next((i for i, row in enumerate(rows) if row["id"] == selected_id), min(selected, max(0, len(rows) - 1)))
            refresh_at = time.monotonic() + args.interval
        height, width = screen.getmaxyx()
        selected = min(selected, max(0, len(rows) - 1))
        current = rows[selected] if rows else None
        selected_id = current["id"] if current else None
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
        put(4, "    " + table_line(header, max(1, width - 6)).replace("#PR", "PR"), bold=True)
        purpose_lines = textwrap.wrap("PURPOSE: " + current["objective"], max(1, width - 4)) if current else []
        purpose_limit = max(1, height // 3)
        if len(purpose_lines) > purpose_limit:
            purpose_lines = purpose_lines[:purpose_limit]
            purpose_lines[-1] = "… Enter for full purpose."
        purpose_extra = max(0, len(purpose_lines) - 1)
        # Keep selected-task instructions visible even when the task list is long.
        visible = max(1, height - 20 - purpose_extra)
        offset = max(0, selected - visible + 1)
        for i, row in enumerate(rows[offset:offset + visible], offset):
            marker = "›" if i == selected else " "
            y = 5 + i - offset + (1 if i > selected else 0)
            put(y, f"{marker} ● {table_line(row, max(1, width - 6))}", row["color"], highlight=i == selected)
            if i == selected:
                put(y + 1, "      ↳ " + row["objective"], row["color"], highlight=True)
        if not rows:
            put(5, "No readable active tasks." if warnings else "No active tasks.")

        detail_y = 5 + visible + 2
        put(detail_y, "─" * max(0, width - 3))
        if current:
            put(detail_y + 1, current["label"], current["color"], bold=True)
            for i, line in enumerate(purpose_lines):
                put(detail_y + 2 + i, line)
            action = current["action"] or f"No action needed from you. Next: {current['next']}."
            prefix = "YOUR ACTION: " if current["action"] else "STATUS: "
            wrapped = textwrap.wrap(prefix + action, max(1, width - 4))
            for i, line in enumerate(wrapped[:3]):
                put(detail_y + 3 + purpose_extra + i, line, 1 if current["action"] else 0, bold=bool(current["action"]))
            if len(wrapped) > 3:
                put(detail_y + 5 + purpose_extra, "… Press Enter for the full task details.", bold=True)
            put(detail_y + 6 + purpose_extra, f"{current['repository']}  ·  {current['roles']}  ·  record saved {current['saved']} ago")
            put(detail_y + 7 + purpose_extra, current["pr"] or "No pull request", underline=bool(current["pr"]))
            put(detail_y + 8 + purpose_extra, "[ Message orchestrator · m ]", bold=True)
        if notice:
            put(height - 2, notice, bold=True)
        if warnings:
            put(height - 2, "! " + " | ".join(warnings), 1)
        try:
            screen.addnstr(height - 1, 0, " m: message orchestrator · Click PR: browser · Wheel / ↑↓ select · Enter details · a next action · r refresh · q close", max(0, width - 1), curses.A_DIM)
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
        elif key in (10, 13, curses.KEY_ENTER) and current:
            notice = show_details(screen, current, args) or ""
        elif key == ord("m") and current:
            notice = compose(screen, args, current)
        elif key == curses.KEY_MOUSE:
            event = mouse_event()
            if event:
                kind, x, y, delta = event
                if kind == "wheel":
                    selected = max(0, min(len(rows) - 1, selected + delta))
                else:
                    index = clicked_row(x, y, width, offset, visible, len(rows), selected)
                    is_preview = y == 6 + selected - offset
                    if index is not None:
                        selected = index
                        table_width = max(1, width - 6)
                        pr_x = 5 + sum(columns(table_width)) + 6
                        if not is_preview and table_width >= 100 and pr_x <= x < pr_x + 9 and rows[index]["pr"]:
                            if kind == "select":
                                open_pr(rows[index]["pr"])
                        elif kind == "open":
                            notice = show_details(screen, rows[index], args) or ""
                    elif current and y == detail_y + 7 + purpose_extra and 1 <= x <= min(width - 2, len(current["pr"])) and current["pr"]:
                        open_pr(current["pr"])
                    elif current and y == detail_y + 8 + purpose_extra and 1 <= x <= 28:
                        notice = compose(screen, args, current)
                    elif current and 1 <= x < width - 1 and detail_y + 1 <= y <= detail_y + 6 + purpose_extra:
                        notice = show_details(screen, current, args) or ""


def show_details(screen, row, args):
    """Keep long human-authored reasons accessible instead of silently truncating them."""
    offset = 0
    while True:
        height, width = screen.getmaxyx()
        texts = [row["label"], "PURPOSE", row["objective"], "", "YOUR ACTION" if row["action"] else "STATUS",
                 row["action"] or f"No action needed from you. Next: {row['next']}.", "",
                 row["stage"], row["roles"], row["repository"], row["pr"],
                 f"Record saved {row['saved']} ago. Workflow state is saved; runtime is observed."]
        lines = [(line, i == 10 and bool(row["pr"])) for i, text in enumerate(texts)
                 for line in (textwrap.wrap(text, max(1, width - 4)) or [""])]
        visible = max(1, height - 2)
        offset = min(offset, max(0, len(lines) - visible))
        screen.erase()
        for y, (line, link) in enumerate(lines[offset:offset + visible]):
            try:
                screen.addnstr(y, 1, line, max(0, width - 2), curses.A_UNDERLINE if link else 0)
            except curses.error:
                pass
        try:
            screen.addnstr(height - 1, 0, " [ Back ]  [ Message orchestrator · m ]  Wheel / ↑↓ scroll", max(0, width - 1), curses.A_DIM)
        except curses.error:
            pass
        screen.refresh()
        key = screen.getch()
        if key in (10, 13, 27, ord("q"), curses.KEY_ENTER):
            return
        if key == ord("m"):
            return compose(screen, args, row)
        if key in (curses.KEY_DOWN, ord("j")):
            offset += 1
        elif key in (curses.KEY_UP, ord("k")):
            offset = max(0, offset - 1)
        elif key == curses.KEY_MOUSE:
            event = mouse_event()
            if event:
                kind, x, y, delta = event
                if kind == "wheel":
                    offset = max(0, offset + delta)
                elif y == height - 1 and 1 <= x <= 8:
                    return
                elif y == height - 1 and 11 <= x <= 37:
                    return compose(screen, args, row)
                elif 0 <= y < visible and offset + y < len(lines):
                    line, link = lines[offset + y]
                    if link and 1 <= x <= len(line):
                        open_pr(row["pr"])


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
            print(f"  {row['repository']} | {row['pr'] or 'No PR'} | saved {row['saved']} ago")
    elif not sys.stdout.isatty():
        parser.error("Interactive board needs a terminal; use --once for text output")
    else:
        try:
            curses.wrapper(display, args)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
