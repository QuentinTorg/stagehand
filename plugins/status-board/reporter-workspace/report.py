#!/usr/bin/env python3
"""Expose reporting operations, not orchestration controls, in the private workspace."""
import json
import os
from pathlib import Path
import sys

connection = json.loads(Path("connection.json").read_text())
if os.environ.get("HERDR_SOCKET_PATH") not in (None, connection["socket"]):
    raise SystemExit("Reporter is attached to a different Herdr session")
# Daemon-backed agent tools can lose frontend environment; this installation-
# owned connection scopes recovery without guessing another session's socket.
os.environ.setdefault("HERDR_SOCKET_PATH", connection["socket"])
os.environ["HERDR_ENV"] = "1"
sys.path.insert(0, connection["package"])
from reporting import worker_main

worker_main(Path.cwd(), sys.argv[1:])
