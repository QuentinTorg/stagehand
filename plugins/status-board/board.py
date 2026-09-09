#!/usr/bin/env python3
"""Render saved coordination state without becoming another workflow controller."""

import argparse
import curses
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import time

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


def table_line(row, width):
    if width < 100:
        name_width = max(12, width // 2)
        return f"{clipped(row['label'], name_width):<{name_width}}  {row['stage']}"
    name_width = min(48, width // 3)
    stage_width = min(36, width // 4)
    pr_width = 9
    roles_width = max(10, width - name_width - stage_width - pr_width - 6)
    pr = "#" + row["pr"].rstrip("/").split("/")[-1] if row["pr"] else "—"
    return (f"{clipped(row['label'], name_width):<{name_width}}  "
            f"{clipped(row['stage'], stage_width):<{stage_width}}  "
            f"{clipped(row['roles'], roles_width):<{roles_width}}  {clipped(pr, pr_width)}")


def display(screen, args):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        for number, color in enumerate((curses.COLOR_RED, curses.COLOR_YELLOW, curses.COLOR_GREEN), 1):
            curses.init_pair(number, color, -1)
    screen.timeout(200)
    selected, selected_id, refresh_at, rows, warnings = 0, None, 0, [], []
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

        def put(y, text, color=0, bold=False, highlight=False):
            if not 0 <= y < height - 1:
                return
            style = curses.color_pair(color) if curses.has_colors() else 0
            style |= curses.A_BOLD if bold else 0
            style |= curses.A_REVERSE if highlight else 0
            try:
                screen.addnstr(y, 1, clipped(text, max(1, width - 3)), max(0, width - 2), style)
            except curses.error:
                pass  # A resize or wide glyph can exhaust the last cell.

        attention = sum(bool(row["action"]) for row in rows)
        put(0, "STAGEHAND  /  WORKSPACE STATUS", bold=True)
        put(1, f"{attention} need your attention   ·   {sum(r['color'] == 2 for r in rows)} in progress   ·   {sum(r['color'] == 3 for r in rows)} complete", bold=True)
        put(2, "Red: needs you   Yellow: ongoing   Green: handoff complete", color=0)
        header = {"label": "WORKSPACE", "stage": "WORKFLOW", "roles": "AGENTS / NEXT", "pr": "PR"}
        put(4, "    " + table_line(header, max(1, width - 6)).replace("#PR", "PR"), bold=True)
        # Keep selected-task instructions visible even when the task list is long.
        visible = max(1, height - 17)
        offset = max(0, selected - visible + 1)
        for i, row in enumerate(rows[offset:offset + visible], offset):
            marker = "›" if i == selected else " "
            put(5 + i - offset, f"{marker} ● {table_line(row, max(1, width - 6))}", row["color"], highlight=i == selected)
        if not rows:
            put(5, "No readable active tasks." if warnings else "No active tasks.")

        detail_y = min(5 + visible + 1, max(6, height - 10))
        put(detail_y, "─" * max(0, width - 3))
        if current:
            put(detail_y + 1, current["label"], current["color"], bold=True)
            action = current["action"] or f"No action needed from you. Next: {current['next']}."
            prefix = "YOUR ACTION: " if current["action"] else "STATUS: "
            wrapped = textwrap.wrap(prefix + action, max(1, width - 4))
            for i, line in enumerate(wrapped[:3]):
                put(detail_y + 2 + i, line, 1 if current["action"] else 0, bold=bool(current["action"]))
            if len(wrapped) > 3:
                put(detail_y + 4, "… Press Enter for the full task details.", bold=True)
            put(detail_y + 5, f"{current['repository']}  ·  {current['roles']}  ·  record saved {current['saved']} ago")
            put(detail_y + 6, current["pr"] or "No pull request")
        if warnings:
            put(height - 2, "! " + " | ".join(warnings), 1)
        try:
            screen.addnstr(height - 1, 0, " ↑↓ select · Enter details · a next action · r refresh · q close", max(0, width - 1), curses.A_DIM)
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
            show_details(screen, current)


def show_details(screen, row):
    """Keep long human-authored reasons accessible instead of silently truncating them."""
    offset = 0
    while True:
        height, width = screen.getmaxyx()
        texts = [row["label"], "", "YOUR ACTION" if row["action"] else "STATUS",
                 row["action"] or f"No action needed from you. Next: {row['next']}.", "",
                 row["stage"], row["roles"], row["repository"], row["pr"],
                 f"Record saved {row['saved']} ago. Workflow state is saved; runtime is observed."]
        lines = [line for text in texts for line in (textwrap.wrap(text, max(1, width - 4)) or [""])]
        visible = max(1, height - 2)
        offset = min(offset, max(0, len(lines) - visible))
        screen.erase()
        for y, line in enumerate(lines[offset:offset + visible]):
            try:
                screen.addnstr(y, 1, line, max(0, width - 2))
            except curses.error:
                pass
        try:
            screen.addnstr(height - 1, 0, " ↑↓ scroll · Enter / Esc back", max(0, width - 1), curses.A_DIM)
        except curses.error:
            pass
        screen.refresh()
        key = screen.getch()
        if key in (10, 13, 27, ord("q"), curses.KEY_ENTER):
            return
        if key in (curses.KEY_DOWN, ord("j")):
            offset += 1
        elif key in (curses.KEY_UP, ord("k")):
            offset = max(0, offset - 1)


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
