#!/usr/bin/env python3
"""One-shot, safe RailRadar connectivity and normalization check."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from railradar.client import RailRadarClient  # noqa: E402
from railradar.config import load_settings  # noqa: E402
from railradar.corridors import CENTRAL_CORRIDOR  # noqa: E402
from railradar.exceptions import (  # noqa: E402
    AuthenticationError,
    ConfigurationError,
    InvalidJsonError,
    NotFoundError,
    RateLimitError,
    RailRadarError,
    RequestTimeoutError,
    UpstreamServiceError,
)
from railradar.normalizer import (  # noqa: E402
    normalize_live_status,
    normalize_station_directory,
    normalize_trains_between,
)
from railradar.storage import RawResponseStore  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-code", default=CENTRAL_CORRIDOR.origin_code)
    parser.add_argument("--to-code", default=CENTRAL_CORRIDOR.destination_code)
    parser.add_argument("--date", help="Journey date in YYYY-MM-DD; omit for the API default")
    parser.add_argument("--limit", type=int, default=5, help="Number of trains to display")
    parser.add_argument("--skip-live", action="store_true", help="Stop after train discovery")
    return parser


def _friendly_error(error: RailRadarError) -> str:
    if isinstance(error, ConfigurationError):
        return f"Configuration problem: {error}"
    if isinstance(error, AuthenticationError):
        return "Authentication failed (HTTP 401): check the API key in .env."
    if isinstance(error, NotFoundError):
        return "Resource not found (HTTP 404): check the station or train identifier."
    if isinstance(error, RateLimitError):
        return "Rate limit exceeded (HTTP 429): try again later or check the plan quota."
    if isinstance(error, UpstreamServiceError):
        return f"RailRadar service temporarily unavailable: {error}"
    if isinstance(error, RequestTimeoutError):
        return f"RailRadar request timed out: {error}"
    if isinstance(error, InvalidJsonError):
        return f"RailRadar returned malformed JSON: {error}"
    return f"RailRadar request failed: {error}"


def main() -> int:
    args = _parser().parse_args()
    store = RawResponseStore(PROJECT_ROOT / "data" / "raw")

    try:
        settings = load_settings(PROJECT_ROOT / ".env")
        client = RailRadarClient(settings)

        station_payload = client.get_station_directory()
        station_path = store.save(endpoint="/v1/lookup/stations", response=station_payload)
        stations = {station.code: station.name for station in normalize_station_directory(station_payload)}
        print(f"Authentication: successful; station directory entries: {len(stations)}")
        print(f"Origin: {args.from_code} ({stations.get(args.from_code, 'name not returned')})")
        print(f"Destination: {args.to_code} ({stations.get(args.to_code, 'name not returned')})")
        print(f"Saved station response: {station_path.relative_to(PROJECT_ROOT)}")

        trains_payload = client.get_trains_between(
            args.from_code,
            args.to_code,
            date=args.date,
        )
        trains_path = store.save(
            endpoint=f"/v1/trains/between/{args.from_code}/{args.to_code}",
            response=trains_payload,
        )
        trains = normalize_trains_between(trains_payload)
        print(f"Discovered trains: {len(trains)}")
        for train in trains[: max(args.limit, 0)]:
            train_type = f"; type={train.train_type}" if train.train_type else ""
            print(f"  {train.number} — {train.name}{train_type}")
        print(f"Saved discovery response: {trains_path.relative_to(PROJECT_ROOT)}")

        if args.skip_live or not trains:
            if not trains:
                print("No train number was returned, so live status was not requested.")
            return 0

        selected = trains[0]
        live_payload = client.get_live_train_status(selected.number, date=args.date)
        live_path = store.save(
            endpoint=f"/v1/trains/{selected.number}/live",
            train_number=selected.number,
            response=live_payload,
        )
        status = normalize_live_status(live_payload)
        print("Normalized live status:")
        print(f"  train_number: {status.train_number}")
        print(f"  train_name: {status.train_name}")
        print(f"  status: {status.status}")
        print(f"  current_station: {status.current_station.code if status.current_station else None}")
        print(f"  next_station: {status.next_station.code if status.next_station else None}")
        print(f"  latitude: {status.latitude}")
        print(f"  longitude: {status.longitude}")
        print(f"  speed_kmh: {status.speed_kmh}")
        print(f"  bearing_degrees: {status.bearing_degrees}")
        print(f"  segment_progress: {status.segment_progress}")
        print(f"  delay_minutes: {status.delay_minutes}")
        print(f"  timestamp: {status.timestamp}")
        print(f"  source: {status.source}")
        print(f"Saved live response: {live_path.relative_to(PROJECT_ROOT)}")
        return 0
    except RailRadarError as error:
        print(_friendly_error(error), file=sys.stderr)
        return 2
    except (OSError, ValueError) as error:
        print(f"Local setup problem: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
