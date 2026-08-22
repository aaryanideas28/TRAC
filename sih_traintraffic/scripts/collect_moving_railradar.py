#!/usr/bin/env python3
"""Collect only from verified active Central Line trains."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from railradar.config import load_settings  # noqa: E402
from railradar.moving import MovingCollector  # noqa: E402


def main() -> int:
    settings = load_settings(PROJECT_ROOT / ".env")
    duration = int(os.environ.get("NEXORA_MOVING_MINUTES", "60"))
    result = MovingCollector(PROJECT_ROOT, settings, duration_minutes=duration, fresh_quota=True).run()
    print(f"Moving collection status: {result['status']}")
    print(f"Moving-train dataset: {result['output']}")
    print(f"Quality report run: {result['report'].get('run_id')}")
    if result["status"] == "insufficient_active_trains":
        print("No verified active trains were found; no full polling window was started.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

