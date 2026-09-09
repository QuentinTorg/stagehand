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


def task_lines(task, modified, workspaces, agents, now):
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
    details = stage
    if review:
        details += f" · {rounds} reviews completed"
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
    lines = [(f"● {label}", color), (f"  {details} | {roles}", 0)]
    lines.append((f"  {repository or 'Repository unspecified'} · record saved {age(modified, now)} ago", 0))
    if pr:
        lines.append((f"  {pr}", 0))
    action = None
    if state.get("attention_required"):
        action = clean(state.get("attention_reason")) or "Human decision needed; ask the orchestrator."
    elif stage == "ready-candidate":
        action = "Authorize reviewer finalization."
    elif stage == "ready-for-team-review":
        action = "Review the ready PR on GitHub; merge when satisfied."
    return lines, (f"{label}: {action}" if action else None)


def snapshot(directory, offline=False):
    tasks, warnings = read_tasks(directory)
    workspaces, agents, live_warnings = (None, None, ["Saved records only; live state not queried"]) if offline else inventory()
    warnings.extend(live_warnings)
    lines = [("Stagehand · red: needs you · yellow: in progress · green: complete", 0)]
    lines.append(("Saved workflow + observed runtime; idle/done does not prove success.", 0))
    lines.extend((warning, 1) for warning in warnings)
    actions = []
    now = time.time()
    for task, modified in tasks:
        rows, action = task_lines(task, modified, workspaces, agents, now)
        lines.append(("", 0))
        lines.extend(rows)
        if action:
            actions.append(action)
    if not tasks:
        lines.append(("No readable active tasks." if warnings else "No active tasks.", 0))
    lines.extend([("", 0), ("Needs your attention", 1 if actions else 0)])
    lines.extend((action, 0) for action in actions or ["None."])
    return lines


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
    offset, refresh_at, lines = 0, 0, []
    while True:
        if time.monotonic() >= refresh_at:
            lines = snapshot(args.tasks, args.offline)
            refresh_at = time.monotonic() + args.interval
        height, width = screen.getmaxyx()
        wrapped = [(part, color) for text, color in lines for part in (textwrap.wrap(text, max(1, width - 2)) or [""])]
        visible = max(1, height - 1)
        offset = min(offset, max(0, len(wrapped) - visible))
        screen.erase()
        for y, (text, color) in enumerate(wrapped[offset:offset + visible]):
            try:
                screen.addnstr(y, 0, text, max(0, width - 1), curses.color_pair(color) if curses.has_colors() else 0)
            except curses.error:
                pass  # Terminal resize and wide glyphs may exhaust the last cell.
        try:
            screen.addnstr(height - 1, 0, "↑↓ scroll · PgUp/PgDn · r refresh · q close board", max(0, width - 1), curses.A_DIM)
        except curses.error:
            pass
        screen.refresh()
        key = screen.getch()
        if key in (ord("q"), 27):
            return
        if key in (ord("r"), curses.KEY_RESIZE):
            refresh_at = 0
        elif key in (curses.KEY_DOWN, ord("j")):
            offset += 1
        elif key in (curses.KEY_UP, ord("k")):
            offset = max(0, offset - 1)
        elif key == curses.KEY_NPAGE:
            offset += visible
        elif key == curses.KEY_PPAGE:
            offset = max(0, offset - visible)


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
        for text, _ in snapshot(args.tasks, args.offline):
            print(text)
    elif not sys.stdout.isatty():
        parser.error("Interactive board needs a terminal; use --once for text output")
    else:
        try:
            curses.wrapper(display, args)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
