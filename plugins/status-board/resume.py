"""Restore previously open boards once, without occupying new or busy panes."""

import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import uuid

PLUGIN_ID = "quentintorg.stagehand-board"


def call(*args):
    return subprocess.run([os.environ.get("HERDR_BIN_PATH", "herdr"), *args],
                          capture_output=True, text=True, check=True, timeout=5).stdout


def config_dir():
    if os.environ.get("HERDR_PLUGIN_ID") == PLUGIN_ID and os.environ.get("HERDR_PLUGIN_CONFIG_DIR"):
        return Path(os.environ["HERDR_PLUGIN_CONFIG_DIR"])
    return Path(call("plugin", "config-dir", PLUGIN_ID).strip())


@contextlib.contextmanager
def locked(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "resume.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def write(path, record):
    fd, name = tempfile.mkstemp(prefix=".resume-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(record, stream)
            stream.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def register(tasks, interval, directory=None, enabled=True):
    socket, pane = os.environ.get("HERDR_SOCKET_PATH"), os.environ.get("HERDR_PANE_ID")
    if not socket or not pane:
        raise ValueError("Herdr socket or viewer pane is unavailable")
    live = json.loads(call("pane", "get", pane))["result"]["pane"]
    if live.get("pane_id") != pane or not live.get("workspace_id"):
        raise ValueError("Cannot verify the viewer pane")
    directory = directory or config_dir()
    key = hashlib.sha256(json.dumps([socket, str(tasks)]).encode()).hexdigest()
    path = directory / ("resume-" + key + ".json")
    token = uuid.uuid4().hex
    record = {"enabled": enabled, "socket": socket, "pane": pane,
              "workspace": live["workspace_id"], "tasks": str(tasks), "token": token,
              "argv": [os.path.abspath(sys.executable), str(Path(__file__).absolute().with_name("board.py")),
                       "--tasks", str(tasks), "--interval", str(interval)]}
    with locked(directory):
        write(path, record)
    return path, token


def close(registration):
    """Only an intentional exit disables recovery, and only for this instance."""
    path, token = registration
    with locked(path.parent):
        record = json.loads(path.read_text())
        if record.get("token") == token:
            record["enabled"] = False
            write(path, record)


def running_board(info, script):
    for process in info.get("foreground_processes", []):
        argv = process.get("argv") or []
        if len(argv) < 2:
            continue
        source = Path(argv[1])
        if not source.is_absolute():
            cwd = process.get("cwd")
            if not cwd:
                continue
            source = Path(cwd) / source
        if source == Path(script):
            return True
    return False


def restore(directory=None):
    directory = directory or config_dir()
    failures = []
    with locked(directory):
        records = list(directory.glob("resume-*.json"))
        if not records:
            return []
        snapshot = json.loads(call("api", "snapshot"))["result"]["snapshot"]
        panes = {pane["pane_id"]: pane for pane in snapshot["panes"]}
        for path in records:
            try:
                record = json.loads(path.read_text())
                if not record.get("enabled") or record.get("socket") != os.environ.get("HERDR_SOCKET_PATH"):
                    continue
                pane = panes.get(record["pane"])
                if pane is None:
                    # An intentionally removed pane is not a request to create
                    # another layout. Its stale registration can be retired.
                    record.update(enabled=False, last_result="Pane no longer exists")
                    write(path, record)
                    continue
                if pane.get("workspace_id") != record["workspace"]:
                    raise ValueError("Saved pane belongs to a different workspace")
                info = json.loads(call("pane", "process-info", "--pane", record["pane"]))["result"]["process_info"]
                if info.get("pane_id") != record["pane"]:
                    raise ValueError("Process inventory did not match the saved pane")
                argv = record["argv"]
                if (not isinstance(argv, list) or len(argv) != 6 or
                        not all(isinstance(arg, str) for arg in argv) or
                        argv[2:3] != ["--tasks"] or argv[4:5] != ["--interval"] or
                        argv[3] != record["tasks"] or Path(argv[1]).name != "board.py"):
                    raise ValueError("Invalid saved board command")
                if running_board(info, argv[1]):
                    continue  # Live handoff or repeated startup: keep the running board.
                if not info.get("shell_pid") or info.get("foreground_process_group_id") != info["shell_pid"] or pane.get("agent"):
                    raise ValueError("Saved viewer pane is occupied; nothing was sent")
                tasks = Path(record["tasks"])
                if not all(Path(arg).is_absolute() and Path(arg).is_file() for arg in argv[:2]) or not tasks.is_absolute() or not tasks.parent.is_dir():
                    raise ValueError("Saved Python, board, or control directory is missing")
                terminal = pane.get("terminal_id")
                if not terminal:
                    raise ValueError("Viewer terminal identity is unavailable")
                if record.get("attempted_terminal") == terminal:
                    continue  # Never silently repeat a failed or uncertain launch.
                record.update(attempted_terminal=terminal, last_result="Launch requested")
                write(path, record)
                # Preserve the venv interpreter; never replay --controller or
                # inherited binding overrides against a possibly replaced agent.
                command = shlex.join(["env", "-u", "STAGEHAND_CONTROLLER_PANE", *argv])
                call("pane", "run", record["pane"], command)
                for _ in range(10):
                    time.sleep(.25)
                    started = json.loads(call("pane", "process-info", "--pane", record["pane"]))["result"]["process_info"]
                    if running_board(started, argv[1]):
                        break
                else:
                    raise ValueError("Board did not start; inspect its pane for the launch error")
                record["last_result"] = "Board process started"
                write(path, record)
            except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
                failures.append(f"{path.name}: {error}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        try:
            call("notification", "show", "Stagehand viewer recovery needs attention",
                 "--body", "A dashboard could not be restored. Inspect the Stagehand plugin log; no occupied pane was replaced.", "--sound", "none")
        except (OSError, subprocess.SubprocessError):
            pass  # The startup log remains available even without a client.
    return failures


if __name__ == "__main__":
    try:
        if os.environ.get("HERDR_ENV") != "1":
            raise ValueError("Viewer recovery requires Herdr")
        sys.exit(1 if restore() else 0)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"Stagehand viewer recovery failed: {error}", file=sys.stderr)
        sys.exit(1)
