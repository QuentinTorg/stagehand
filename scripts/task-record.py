#!/usr/bin/env python3
"""Portable entrypoint for validated orchestration recovery notes."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/status-board"))
from task_records import main

main()
