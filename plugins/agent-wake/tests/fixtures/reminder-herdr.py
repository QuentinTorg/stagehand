#!/usr/bin/env python3
"""File-backed Herdr double for isolated reminder-process tests."""

import json
import os
from pathlib import Path
import sys

state = json.loads(Path(os.environ["FAKE_HERDR_STATE"]).read_text())
args = sys.argv[1:]
with Path(os.environ["FAKE_HERDR_CALLS"]).open("a") as log:
    log.write(json.dumps(args) + "\n")
if args == ["plugin", "list", "--json"]:
    result = {"plugins": [{"plugin_id": "quentintorg.agent-wake", "enabled": state["enabled"],
                            "plugin_root": state["plugin_root"]}]}
elif args == ["api", "snapshot"]:
    result = {"snapshot": {"agents": [state["source"]]}}
elif args[:2] == ["agent", "get"]:
    result = {"agent": state["source"] if args[2] == "w2:p1" else {"agent_status": "idle"}}
elif args[:2] == ["agent", "prompt"]:
    result = {"type": "agent_prompted"}
else:
    raise SystemExit(f"Unexpected Herdr command: {args}")
print(json.dumps({"result": result}))
