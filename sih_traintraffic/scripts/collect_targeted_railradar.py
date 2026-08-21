#!/usr/bin/env python3
"""Collect a targeted real dataset from currently running Central Line trains."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from railradar.config import load_settings  # noqa: E402
from railradar.targeted import TargetedCollector  # noqa: E402


def main() -> int:
    settings = load_settings(PROJECT_ROOT / ".env")
    duration = int(os.environ.get("NEXORA_TARGETED_MINUTES", "20"))
    collector = TargetedCollector(PROJECT_ROOT, settings, duration_minutes=duration)
    result = collector.run()
    print(f"Targeted collection status: {result['status']}")
    print(f"Augmented dataset: {result['output']}")
    print(f"Quality report: {PROJECT_ROOT / 'data' / 'reports' / (collector.run_id + '_targeted_quality_report.json')}")
    if result["status"] == "no_running_trains":
        print("No currently running candidate was available; no full targeted window was started.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
