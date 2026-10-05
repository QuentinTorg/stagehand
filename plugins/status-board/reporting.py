"""Optional observer: isolated workspace, independent relay inbox, display-only reports."""

import argparse
import builtins
import contextlib
import fcntl
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from types import SimpleNamespace

import agent_binding

PACKAGE = Path(__file__).resolve().parent
DEFAULTS = {"enabled": False, "kind": "codex", "model": "gpt-6-luna", "reasoning": "medium", "arguments": ""}
FIELDS = ("summary", "recent_work", "review_coverage", "next_actor", "next_action", "human_action")


def read(path, default=None):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Shared atomic writer; reports must never leave a half-written dashboard row.
    from resume import write as atomic_write
    atomic_write(path, value)


def config_path(tasks):
    return tasks.parent / "reporter.json"


def configuration(tasks):
    saved = read(config_path(tasks), {})
    if not isinstance(saved, dict):
        raise ValueError("Invalid reporter configuration")
    config = dict(DEFAULTS, **saved)
    if type(config["enabled"]) is not bool or any(not isinstance(config[key], str) for key in DEFAULTS if key != "enabled"):
        raise ValueError("Invalid reporter launch settings")
    if config["enabled"] and not all(isinstance(config.get(key), str) and config[key] for key in ("directory", "socket")):
        raise ValueError("Enabled reporter has no workspace/session binding")
    return config


@contextlib.contextmanager
def locked(tasks):
    tasks.parent.mkdir(parents=True, exist_ok=True)
    with (tasks.parent / "reporter.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def call(*args, timeout=5):
    result = subprocess.run([agent_binding.herdr_binary(), *args], capture_output=True,
                            text=True, check=True, timeout=timeout)
    return json.loads(result.stdout)["result"]


def relay():
    # Reuse lifecycle identity, coalescing, and retry handling instead of inventing
    # a second worker protocol. Each reporter is a separate relay consumer.
    loader = importlib.machinery.SourceFileLoader("reporter_wake", str(PACKAGE.parent / "agent-wake" / "agent-wake"))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    # This module runs inside the board plugin or an agent, whose config-dir
    # environment is not necessarily the wake plugin's. Never configure another
    # plugin's directory by inheriting that environment.
    def config_directory():
        result = subprocess.run([agent_binding.herdr_binary(), "plugin", "config-dir", module.PLUGIN_ID],
                                capture_output=True, text=True, check=True, timeout=5)
        return Path(result.stdout.strip())
    module._config_dir = config_directory
    # CLI JSON output is not needed here. Suppress it only in this module,
    # without redirecting stdout used by the board's other rendering threads.
    def diagnostic_print(*args, **kwargs):
        if kwargs.get("file") is not None:
            builtins.print(*args, **kwargs)
    module.print = diagnostic_print
    return module


def relay_action(module, operation, **arguments):
    if operation == "_remove":
        acknowledge = arguments.pop("acknowledge")
        return module._remove(SimpleNamespace(**arguments), acknowledge)
    return getattr(module, operation)(SimpleNamespace(**arguments))


def scoped_sources(tasks, agents, controller):
    """No sibling workspace or reporter activity belongs in this consumer."""
    sources = [("controller", "orchestrator", controller)]
    for task, _ in tasks:
        workspace = task.get("workspace", {}).get("id")
        for role, name in task.get("agents", {}).items():
            recorded = (task.get("role_sessions") or {}).get(role) or {}
            matches = [agent for agent in agents if agent.get("name") == name and
                       agent.get("workspace_id") == workspace and
                       (not recorded.get("pane_id", recorded.get("pane")) or
                        recorded.get("pane_id", recorded.get("pane")) == agent.get("pane_id")) and
                       (not recorded.get("native_session_id", recorded.get("session_id")) or
                        recorded.get("native_session_id", recorded.get("session_id")) ==
                        (agent.get("agent_session") or {}).get("value"))]
            if len(matches) == 1:
                sources.append((str(task["task_id"]), role, matches[0]))
    return sources


def fingerprint(task, sources):
    identities = [(role, agent.get("pane_id"), agent.get("terminal_id"),
                   agent_binding.native_session(agent), agent.get("state_change_seq"))
                  for key, role, agent in sources if key == str(task["task_id"])]
    return hashlib.sha256(json.dumps([task, sorted(identities)], sort_keys=True).encode()).hexdigest()


def sync(tasks_directory, tasks, agents, controller):
    if not configuration(tasks_directory)["enabled"]:
        return
    with locked(tasks_directory):
        _sync(tasks_directory, tasks, agents, controller)


def _sync(tasks_directory, tasks, agents, controller):
    config = configuration(tasks_directory)
    if not config["enabled"]:
        return
    directory = Path(config["directory"])
    if config.get("socket") != os.environ.get("HERDR_SOCKET_PATH"):
        raise ValueError("Reporter belongs to another Herdr session")
    target = agent_binding.resolve(agent_binding.load(directory / "binding.json"), agents)
    sources = scoped_sources(tasks, agents, controller)
    wake = relay()
    root = directory / "wake"
    registrations = list(wake._documents(root / "watches"))
    wanted = {(key, role, agent["pane_id"]): agent for key, role, agent in sources
              if agent["pane_id"] != target["pane_id"]}
    # Cancel only reporter-owned subscriptions. The coordinator's inbox and
    # task-record watch IDs are untouched, including during fallback.
    retained = set()
    for _, watch in registrations:
        identity = (watch["key"], watch.get("metadata", {}).get("role"), watch["pane_id"])
        if identity in wanted and wake._same_source(watch, wanted[identity]):
            retained.add(identity)
        else:
            relay_action(wake, "_remove", state_root=str(root), watch=watch["id"], acknowledge=False)
    for (key, role, pane), agent in wanted.items():
        if (key, role, pane) in retained:
            continue
        relay_action(wake, "_arm", state_root=str(root), key=key,
                     workspace_id=agent["workspace_id"], workspace_label=key,
                     pane=pane, agent=agent.get("name"), metadata=json.dumps({"role": role}),
                     persistent=True, observed_working=False)


def launch_arguments(config):
    arguments = shlex.split(config.get("arguments", ""))
    if config["kind"] == "codex":
        if not config["model"] or not config["reasoning"]:
            raise ValueError("Choose a Codex model and reasoning effort")
        arguments = ["--model", config["model"], "-c",
                     "model_reasoning_effort=" + json.dumps(config["reasoning"]), *arguments]
    elif config.get("model") or config.get("reasoning"):
        raise ValueError("For other harnesses, clear Model/Reasoning and supply native launch arguments")
    return arguments


def prepare_directory(tasks, config):
    key = hashlib.sha256(str(tasks.resolve()).encode()).hexdigest()[:12]
    directory = Path(config.get("directory") or
                     Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) /
                     "stagehand/reporters" / key).expanduser().resolve()
    # A tab does not isolate inherited instructions. Keep the reporter outside
    # the source checkout and reject other repository/AGENTS ancestors.
    if (directory / ".git").exists() or directory.is_relative_to(PACKAGE.parents[1]) or any(
            (parent / ".git").exists() or (parent / "AGENTS.md").exists()
            for parent in directory.parents if parent != Path.home()):
        raise ValueError("Choose a reporter directory outside repositories and their AGENTS.md ancestors")
    directory.mkdir(parents=True, exist_ok=True)
    previous = read(directory / "connection.json", {})
    if previous and (previous.get("tasks") != str(tasks) or previous.get("socket") != os.environ.get("HERDR_SOCKET_PATH")):
        raise ValueError("Reporter directory is already assigned to another workspace/session")
    for name in ("AGENTS.md", "report.py"):
        text = (PACKAGE / "reporter-workspace" / name).read_text()
        if name == "report.py":
            text = text.replace("#!/usr/bin/env python3", "#!" + sys.executable, 1)
        destination = directory / name
        if destination.exists() and destination.read_text() != text:
            raise ValueError(f"Preserving modified reporter instructions: {destination}")
        destination.write_text(text)
    (directory / "report.py").chmod(0o755)
    candidates = [PACKAGE.parents[1] / path for path in (".agents/skills/herdr", ".codex/skills/herdr", ".local/skills/herdr")]
    installed = next((path for path in candidates if (path / "SKILL.md").is_file()), candidates[0])
    skill = Path(config.get("herdr_skill") or installed).expanduser().resolve()
    if not (skill / "SKILL.md").is_file():
        raise ValueError("Configure an installed Herdr skill directory before enabling the reporter")
    for parent in (".agents", ".codex"):
        link = directory / parent / "skills/herdr"
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink() and link.resolve() == skill:
            continue
        if link.exists() or link.is_symlink():
            raise ValueError(f"Preserving existing skill installation: {link}")
        link.symlink_to(skill, target_is_directory=True)
    write(directory / "connection.json", {"tasks": str(tasks), "package": str(PACKAGE),
          "socket": os.environ.get("HERDR_SOCKET_PATH")})
    return directory


def enable(tasks):
    with locked(tasks):
        return _enable(tasks)


def _enable(tasks):
    config = configuration(tasks)
    if config.get("enabled"):
        return "Background reporter already enabled."
    if os.environ.get("HERDR_ENV") != "1":
        raise ValueError("Reporter launch requires Herdr")
    arguments = launch_arguments(config)
    agents = call("agent", "list")["agents"]
    controller = agent_binding.resolve(agent_binding.load(tasks.parent / "controller.json"), agents)
    plugins = call("plugin", "list", "--json")["plugins"]
    if not any(p.get("plugin_id") == "quentintorg.agent-wake" and p.get("enabled") for p in plugins):
        raise ValueError("Enable the Agent Wake Relay before launching the reporter")
    directory = prepare_directory(tasks, config)
    config.update(directory=str(directory), socket=os.environ["HERDR_SOCKET_PATH"])
    name = "reporter_" + hashlib.sha256(str(tasks).encode()).hexdigest()[:12]
    # Save the pane before launching: a startup timeout may leave a live process.
    # Re-enabling never blindly creates another tab or replays agent start.
    if config.get("pane"):
        agent = call("agent", "get", config["pane"])["agent"]
        if agent.get("agent_status") in {"working", "blocked"}:
            raise ValueError("Inspect the existing reporter tab and let its current turn/setup finish before enabling")
        binding = directory / "binding.json"
        if not binding.exists():
            # Explicit retry after startup/permission failure may adopt only the
            # exact agent in the terminal we created, never a pane replacement.
            if (agent.get("pane_id") != config["pane"] or agent.get("terminal_id") != config["terminal"]
                    or agent.get("workspace_id") != controller["workspace_id"] or agent.get("name") != name):
                raise ValueError("Cannot verify the reporter from the saved startup attempt; inspect its tab")
            agent_binding.save(binding, agent_binding.capture(agent))
        agent_binding.resolve(agent_binding.load(binding), [agent])
    else:
        tab = call("tab", "create", "--workspace", controller["workspace_id"], "--cwd", str(directory),
                   "--label", "Status reporter", "--no-focus")
        config.update(pane=tab["root_pane"]["pane_id"], tab=tab["tab"]["tab_id"],
                      terminal=tab["root_pane"]["terminal_id"])
        write(config_path(tasks), config)
        try:
            agent = call("agent", "start", name, "--kind", config["kind"], "--pane", config["pane"],
                         "--", *arguments, timeout=40)["agent"]
        except subprocess.CalledProcessError as error:
            # First-run harness setup belongs to the human, not an auto-approval.
            raise ValueError("Reporter startup needs attention. Open the Status reporter tab to finish setup, "
                             "then enable reporting again; its saved pane will be reused.") from error
        agent_binding.save(directory / "binding.json", agent_binding.capture(agent))
    wake = relay()
    relay_action(wake, "_configure", state_root=str(directory / "wake"),
                 target=None, target_binding=str(directory / "binding.json"), reminder_minutes=0)
    # Bootstrap first, then subscribe. An ambiguous send remains inspectable;
    # it is not automatically retried or converted into a replacement agent.
    call("agent", "prompt", agent["pane_id"],
         "Read ./AGENTS.md to initialize this read-only status reporter. Run ./report.py context, "
         "summarize the current tasks, publish the reports, and stop. Future HERDR_AGENT_WAKE notices "
         "refer to your independent inbox; handle and acknowledge them there.", timeout=10)
    config["enabled"] = True
    write(config_path(tasks), config)
    from board import read_tasks
    try:
        _sync(tasks, read_tasks(tasks)[0], call("agent", "list")["agents"], controller)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError, SystemExit):
        _disable(tasks)
        raise
    return "Background reporter enabled; its separate tab is available for inspection."


def disable(tasks):
    with locked(tasks):
        return _disable(tasks)


def _disable(tasks):
    config = configuration(tasks)
    if config.get("socket") and config["socket"] != os.environ.get("HERDR_SOCKET_PATH"):
        raise ValueError("Reporter belongs to another Herdr session")
    config["enabled"] = False
    write(config_path(tasks), config)
    if config.get("directory"):
        root = Path(config["directory"]) / "wake"
        wake = relay()
        for _, watch in wake._documents(root / "watches"):
            relay_action(wake, "_remove", state_root=str(root), watch=watch["id"], acknowledge=False)
    return "Original reporting restored. Reporter tab retained; no agents interrupted."


def context(directory):
    connection = read(directory / "connection.json")
    if connection["socket"] != os.environ.get("HERDR_SOCKET_PATH"):
        raise ValueError("Reporter context belongs to a different Herdr session")
    tasks_directory = Path(connection["tasks"])
    from board import read_tasks, pr_links
    tasks, warnings = read_tasks(tasks_directory)
    agents = call("agent", "list")["agents"]
    controller = agent_binding.resolve(agent_binding.load(tasks_directory.parent / "controller.json"), agents)
    sources = scoped_sources(tasks, agents, controller)
    briefs = []
    for task, _ in tasks:
        briefs.append({"task_id": task["task_id"], "objective": task.get("objective"),
                       "mode": task.get("mode"), "workspace": task.get("workspace"), "state": task["state"],
                       "repository": task.get("repository"), "development_target": task.get("development_target"),
                       "intent_ref": task.get("intent_ref"), "handoff": task.get("handoff"),
                       "result": task.get("result"), "review": task.get("review"),
                       "pull_requests": pr_links(task),
                       "fingerprint": fingerprint(task, sources),
                       "roles": [{"role": role, **{key: agent.get(key) for key in
                                  ("pane_id", "name", "agent_status", "agent_session", "state_change_seq")}}
                                 for key, role, agent in sources if key == str(task["task_id"])]})
    notices = [notice for _, notice in relay()._documents(directory / "wake/inbox")]
    result = {"tasks": briefs, "controller_pane": controller["pane_id"], "notices": notices,
              "warnings": warnings, "report_format": {"task_id": "from task", "fingerprint": "from task",
                  "status": "working | needs-human | complete | unknown", **{field: "short text" for field in FIELDS},
                  "evidence": ["pane/artifact/head supporting your conclusion"]}}
    # Capture the evidence used by this turn. A late publish cannot claim it read
    # a newer turn just because its file was written recently.
    write(directory / "context.json", {str(task["task_id"]): fingerprint(task, sources) for task, _ in tasks})
    return result


def publish(directory, records):
    if not isinstance(records, list):
        raise ValueError("Reports must be a JSON array")
    expected = read(directory / "context.json", {})
    validated = {}
    for record in records:
        if (not isinstance(record, dict) or not isinstance(record.get("task_id"), str)
                or record.get("fingerprint") != expected.get(record["task_id"]) or not record.get("fingerprint")):
            raise ValueError("Report does not match the captured task context")
        if record.get("status") not in {"working", "needs-human", "complete", "unknown"}:
            raise ValueError("Invalid report status")
        if any(not isinstance(record.get(key), str) or len(record[key]) > 700 for key in FIELDS):
            raise ValueError("Report fields must be short text (at most 700 characters each)")
        if len(record["summary"]) > 100 or len(record["next_actor"]) > 40:
            raise ValueError("Keep the table summary and next actor compact")
        if not isinstance(record.get("evidence"), list) or len(record["evidence"]) > 6 or any(
                not isinstance(value, str) or len(value) > 500 for value in record["evidence"]):
            raise ValueError("Supply at most six concise evidence references")
        if any(any(not character.isprintable() and not character.isspace() for character in value)
               for value in [*(record[key] for key in FIELDS), *record["evidence"]]):
            raise ValueError("Report text must not contain terminal controls")
        validated[record["task_id"]] = {key: record[key] for key in ("task_id", "fingerprint", "status", *FIELDS, "evidence")}
    reports = read(directory / "reports.json", {})
    if not isinstance(reports, dict):
        raise ValueError("Invalid report file")
    now = time.time()
    reports.update({key: dict(value, updated_at=now) for key, value in validated.items()})
    write(directory / "reports.json", reports)


def decorate(tasks_directory, tasks, agents, controller, rows):
    """Attach explanations without changing task records or baseline status."""
    config = configuration(tasks_directory)
    if not config["enabled"]:
        return
    directory = Path(config["directory"])
    reports = read(directory / "reports.json", {})
    if not isinstance(reports, dict):
        raise ValueError("Invalid report file")
    available = True
    try:
        observer = agent_binding.resolve(agent_binding.load(directory / "binding.json"), agents)
        available = observer.get("agent_status") != "blocked"
    except ValueError:
        available = False
    sources = scoped_sources(tasks, agents, controller)
    task_map = {str(task["task_id"]): task for task, _ in tasks}
    for row in rows:
        report = reports.get(row["id"])
        if not report:
            row["reporter_note"] = "Reporter has not summarized this task; showing ordinary status."
            continue
        if (not isinstance(report, dict) or any(not isinstance(report.get(key), str) for key in FIELDS)
                or report.get("status") not in {"working", "needs-human", "complete", "unknown"}
                or not isinstance(report.get("updated_at"), (int, float))
                or not isinstance(report.get("evidence"), list)
                or any(not isinstance(value, str) for value in report["evidence"])):
            row["reporter_note"] = "Invalid reporter summary; showing ordinary status."
            continue
        from board import clean
        report = dict(report, **{key: clean(report[key]) for key in FIELDS},
                      evidence=[clean(value) for value in report["evidence"]])
        row["report"] = report
        row["report_fresh"] = available and report.get("fingerprint") == fingerprint(task_map[row["id"]], sources)
        row["reporter_note"] = "" if row["report_fresh"] else "Previous reporter summary; current status uses the ordinary dashboard."


def apply_display(row):
    report = row.get("report")
    if not report or not row.get("report_fresh"):
        return
    # Explicit native blockers/activity stay authoritative. Fresh explanations
    # can clarify a settled result without treating idle as a successful review.
    runtime = set(row.get("runtime_states", {}).values())
    status = report["status"]
    if "blocked" in runtime:
        status = "needs-human"
    elif "working" in runtime:
        status = "working"
    actor = "you" if status == "needs-human" else report["next_actor"]
    action = report["human_action"] if status == "needs-human" else report["next_action"]
    summary = report["summary"]
    if status != report["status"]:
        # Keep the live next actor/action together with its color: a yellow row
        # must not inherit an obsolete "you" or "finished" explanation.
        summary = row["summary"]
        row["reporter_note"] = "Live activity takes precedence over this reporter explanation."
        actor = "you" if status == "needs-human" else next(role for role, value in row["runtime_states"].items() if value == "working")
        action = row["action"]
    row.update(summary=summary, stage=summary, next=actor,
               action=action,
               status=None if status == "unknown" else status,
               color={"needs-human": 1, "working": 2, "complete": 3}.get(status, 0))
    row["runtime_overlay"] = True
    row["roles"] = row["roles"].split(" → ")[0] + (" → " + actor if actor else "")


def worker_main(directory, arguments):
    parser = argparse.ArgumentParser(description="Read context and publish private dashboard reports")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("context")
    output = commands.add_parser("publish")
    output.add_argument("file", type=Path)
    ack = commands.add_parser("ack")
    ack.add_argument("ids", nargs="+")
    args = parser.parse_args(arguments)
    if args.command == "context":
        print(json.dumps(context(directory), indent=2))
    elif args.command == "publish":
        publish(directory, read(args.file))
        print("Reports published")
    else:
        for identifier in args.ids:
            relay_action(relay(), "_remove", state_root=str(directory / "wake"), wake=identifier, acknowledge=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("command", choices=("configure", "enable", "disable"))
    for key in ("kind", "model", "reasoning", "arguments", "directory", "herdr_skill"):
        parser.add_argument("--" + key.replace("_", "-"))
    args = parser.parse_args()
    try:
        if not args.tasks.is_absolute():
            raise ValueError("--tasks must be absolute")
        if args.command == "configure":
            config = configuration(args.tasks)
            if config["enabled"]:
                raise ValueError("Disable reporting before changing its launch configuration")
            config.update({key: value for key, value in vars(args).items()
                           if key not in {"tasks", "command"} and value is not None})
            write(config_path(args.tasks), config)
            print(json.dumps(config, indent=2))
        else:
            print(enable(args.tasks) if args.command == "enable" else disable(args.tasks))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Reporter: {error}\n")
