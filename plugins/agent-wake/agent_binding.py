"""Explicit agent identity shared by the board and wake relay; names are labels."""

import json
import fcntl
import os
from pathlib import Path
import tempfile
import subprocess
import shutil


def herdr_binary():
    # A running server can retain a replaced executable and export a nonexistent
    # "(deleted)" path. Recover only the binary; inherit the same session routing.
    configured = os.environ.get("HERDR_BIN_PATH")
    if configured and (os.path.exists(configured) or shutil.which(configured)):
        return configured
    return shutil.which("herdr") or configured or "herdr"


class ControllerUnavailable(ValueError):
    """The saved conversation may still be resuming; never substitute a neighbor."""


def native_session(agent):
    session = agent.get("agent_session") or {}
    if session.get("value") and session.get("kind") and session.get("agent"):
        return {key: session[key] for key in ("agent", "kind", "value")}
    return None


def process_identity(agent):
    result = subprocess.run([herdr_binary(), "pane", "process-info", "--pane", agent["pane_id"]],
                            capture_output=True, text=True, check=True, timeout=5)
    info = json.loads(result.stdout)["result"]["process_info"]
    group = info.get("foreground_process_group_id")
    if info.get("pane_id") != agent["pane_id"] or not group or group == info.get("shell_pid"):
        raise ValueError("Controller frontend is not running")
    return group


def capture(agent):
    socket = os.environ.get("HERDR_SOCKET_PATH")
    if not socket or not all(agent.get(key) for key in ("workspace_id", "pane_id", "terminal_id")):
        raise ValueError("Cannot bind an agent without its Herdr socket, workspace, pane, and terminal identity")
    return {"version": 1, "socket": socket, "workspace_id": agent["workspace_id"],
            "pane_id": agent["pane_id"], "terminal_id": agent["terminal_id"],
            "session": native_session(agent),
            "process_group": None if native_session(agent) else process_identity(agent)}


def validate(binding):
    if (not isinstance(binding, dict) or binding.get("version") != 1
            or not all(isinstance(binding.get(key), str) and binding[key]
                       for key in ("socket", "workspace_id", "pane_id", "terminal_id"))):
        raise ValueError("Invalid controller binding; explicitly bind the intended controller")
    session = binding.get("session")
    if session is not None and (not isinstance(session, dict) or
            not all(isinstance(session.get(key), str) and session[key] for key in ("agent", "kind", "value"))):
        raise ValueError("Invalid controller session identity")
    if session is None and type(binding.get("process_group")) is not int:
        raise ValueError("Controller without a native session needs a live process anchor")
    return binding


def load(path):
    try:
        return validate(json.loads(Path(path).read_text()))
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot load controller binding {path}: {error}") from error


def save(path, binding, replace=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _save_locked(path, binding, replace)


def _save_locked(path, binding, replace):
    path = Path(path)
    validate(binding)
    if path.exists() and not replace:
        previous = load(path)
        # Restarted terminals get new IDs. The same native conversation does
        # not require a transfer of ownership; a different one does.
        same = (previous["socket"] == binding["socket"] and
                previous["workspace_id"] == binding["workspace_id"] and
                ((previous.get("session") and previous["session"] == binding.get("session")) or
                 previous == binding))
        if not same:
            raise ValueError("Controller already bound; use --replace-controller only for an authorized handover")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".controller-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(binding, stream)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def resolve(binding, agents):
    validate(binding)
    if binding["socket"] != os.environ.get("HERDR_SOCKET_PATH"):
        raise ValueError("Controller belongs to a different Herdr session; explicitly rebind it")
    matches = [agent for agent in agents or [] if agent.get("workspace_id") == binding["workspace_id"]
               and ((native_session(agent) == binding["session"]) if binding.get("session") else
                    (agent.get("terminal_id") == binding["terminal_id"] and agent.get("pane_id") == binding["pane_id"]))]
    if not matches:
        raise ControllerUnavailable("Waiting for the bound controller to resume; explicitly rebind for a different session")
    if len(matches) != 1 or not matches[0].get("pane_id"):
        raise ValueError("Bound controller is missing or ambiguous; resume its session or explicitly rebind")
    if not binding.get("session"):
        try:
            if process_identity(matches[0]) != binding["process_group"]:
                raise ValueError("Controller process changed; explicitly rebind it")
        except (OSError, KeyError, subprocess.SubprocessError) as error:
            raise ValueError("Cannot verify the bound controller process") from error
    return matches[0]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pane", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--replace-controller", action="store_true")
    args = parser.parse_args()
    try:
        if os.environ.get("HERDR_ENV") != "1" or not args.output.is_absolute():
            raise ValueError("Binding requires Herdr and an absolute output path")
        result = subprocess.run([herdr_binary(), "agent", "get", args.pane],
                                capture_output=True, text=True, check=True, timeout=5)
        agent = json.loads(result.stdout)["result"]["agent"]
        if agent.get("pane_id") != args.pane:
            raise ValueError("--pane must be an explicit pane ID")
        save(args.output, capture(agent), replace=args.replace_controller)
        print(f"Controller bound: {args.output}")
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        parser.exit(1, f"{error}\n")
