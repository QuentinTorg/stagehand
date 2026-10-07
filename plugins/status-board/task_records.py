"""Validate recovery notes without constraining their task-specific evidence."""

import argparse
from pathlib import Path
import sys

import yaml

from resume import write


def validate(task, canonical=False):
    if not isinstance(task, dict) or not isinstance(task.get("task_id"), str) or not task["task_id"].strip():
        raise ValueError("expected a nonempty task_id; use task_id, not id")
    if not isinstance(task.get("state"), dict):
        raise ValueError("expected state mapping")
    if not isinstance(task["state"].get("name"), str) or not task["state"]["name"].strip():
        raise ValueError("expected state.name text")
    for key in ("workspace", "agents", "role_sessions"):
        if key in task and not isinstance(task[key], dict):
            raise ValueError(f"expected {key} mapping")
    if "agent" in task:
        raise ValueError("use agents: {worker: <name>} and role_sessions, not a singular agent field")
    for role, name in task.get("agents", {}).items():
        if not isinstance(role, str) or not role or not isinstance(name, str) or not name:
            raise ValueError("agents must map role names to exact live agent names")
    for role, session in task.get("role_sessions", {}).items():
        if not isinstance(role, str) or not isinstance(session, dict):
            raise ValueError("role_sessions must map role names to identity mappings")
        for key in ("pane", "pane_id", "native_session_id", "session_id"):
            if key in session and (not isinstance(session[key], str) or not session[key]):
                raise ValueError(f"role_sessions.{role}.{key} must be nonempty text")
    if "pull_requests" in task:
        collection = task["pull_requests"]
        if not isinstance(collection, (list, dict)) or (isinstance(collection, list) and
                any(not isinstance(item, (str, dict)) for item in collection)):
            raise ValueError("pull_requests must be a collection of URLs or PR mappings")
    if canonical:
        for alias, field in (("id", "task_id"), ("agent_sessions", "role_sessions")):
            if alias in task:
                raise ValueError(f"use {field}, not {alias}")
        if task["state"].get("name") not in {"working", "needs-human", "complete"}:
            raise ValueError("state.name must be working, needs-human, or complete")
        action = task["state"].get("next_action")
        if task["state"]["name"] == "needs-human" and (not isinstance(action, str) or not action.strip()):
            raise ValueError("needs-human requires state.next_action")
        if set(task.get("role_sessions", {})) - set(task.get("agents", {})):
            raise ValueError("each role_sessions role must also have an agents entry")
        if task.get("agents") and not isinstance(task.get("workspace", {}).get("id"), str):
            raise ValueError("assigned agents require workspace.id for scoped live matching")
    return task


def load(path, canonical=False):
    return validate(yaml.safe_load(path.read_text()), canonical)


def save(path, source):
    task = load(source, canonical=True)
    if path.suffix not in {".json", ".yaml", ".yml"}:
        raise ValueError("task record must have a .json, .yaml, or .yml extension")
    if path.exists():
        previous = yaml.safe_load(path.read_text())
        if not isinstance(previous, dict) or previous.get("task_id", previous.get("id")) != task["task_id"]:
            raise ValueError("preserving destination: task identity differs or cannot be established")
    path.parent.mkdir(parents=True, exist_ok=True)
    # JSON is also valid YAML. Share the atomic writer with reporting rather
    # than risking a partial note or discarding flexible evidence fields.
    write(path, task)


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Validate a task file or all task files in a directory")
    check.add_argument("path", type=Path)
    output = commands.add_parser("save", help="Validate a complete candidate and atomically save it")
    output.add_argument("path", type=Path)
    output.add_argument("--input", required=True, type=Path)
    args = parser.parse_args(arguments)
    try:
        if args.command == "save":
            save(args.path, args.input)
            print(f"Saved {args.path}")
        else:
            paths = sorted(p for p in args.path.iterdir() if p.suffix in {".json", ".yaml", ".yml"} and p.is_file()) if args.path.is_dir() else [args.path]
            failures = []
            for path in paths:
                try:
                    load(path, canonical=True)
                except (OSError, ValueError, yaml.YAMLError) as error:
                    failures.append(f"{path}: {error}")
            if failures:
                raise ValueError("\n".join(failures))
            print(f"Validated {len(paths)} task record(s)")
    except (OSError, ValueError, yaml.YAMLError) as error:
        parser.exit(1, f"Task record: {error}\n")


if __name__ == "__main__":
    main()
