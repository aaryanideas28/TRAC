#!/usr/bin/env python3
"""Run the automatic, rate-limited Nexora RailRadar mini-collection."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from railradar.collection import CollectionConfig  # noqa: E402
from railradar.collector import RailRadarCollector  # noqa: E402
from railradar.config import load_settings  # noqa: E402
from railradar.corridors import CENTRAL_CORRIDOR  # noqa: E402
from railradar.exceptions import RailRadarError  # noqa: E402


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def main() -> int:
    try:
        settings = load_settings(PROJECT_ROOT / ".env")
        duration_minutes = _int_env("NEXORA_COLLECTION_MINUTES", 20)
        quota_total = _int_env("RAILRADAR_MONTHLY_QUOTA", 1000)
        config = CollectionConfig(
            duration_seconds=max(1, duration_minutes) * 60,
            quota_total=quota_total,
            safety_fraction=0.85,
            stale_threshold_seconds=_int_env("NEXORA_STALE_THRESHOLD_SECONDS", 300),
        )
        corridor = {
            "name": CENTRAL_CORRIDOR.name,
            "origin_code": CENTRAL_CORRIDOR.origin_code,
            "destination_code": CENTRAL_CORRIDOR.destination_code,
        }
        collector = RailRadarCollector(
            project_root=PROJECT_ROOT,
            settings=settings,
            config=config,
            corridor=corridor,
        )
        result = collector.run()
        metadata = result["metadata"]
        print("Collection complete.")
        print(f"Trains tracked: {metadata['selected_train_count']}")
        print(f"Observations: {metadata['total_observations']}")
        print(f"Requests: {metadata['actual_requests']} total; successful={metadata['successful_requests']}; failed={metadata['failed_requests']}")
        print(f"Retries: {metadata['retry_count']}; 429 responses: {metadata['429_count']}; stale observations: {metadata['stale_observations']}")
        print(f"Run metadata: {PROJECT_ROOT / 'data' / 'runs' / (metadata['run_id'] + '.json')}")
        print(f"Quality report: {result['report']}")
        print(f"Normalized CSV: {PROJECT_ROOT / 'data' / 'processed' / 'live_observations.csv'}")
        return 0
    except RailRadarError as error:
        print(f"Collection stopped safely: {error}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Collection stopped safely: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
