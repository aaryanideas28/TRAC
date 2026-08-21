"""Append-only raw response storage for reproducible observations."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RawResponseStore:
    """Write each captured response to a unique date-partitioned JSON file."""

    def __init__(self, root: str | Path = "data/raw") -> None:
        self.root = Path(root)

    def save(
        self,
        *,
        endpoint: str,
        response: Any,
        http_status: int = 200,
        train_number: str | None = None,
        collected_at: datetime | None = None,
    ) -> Path:
        timestamp = collected_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        day_dir = self.root / timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)

        safe_endpoint = re.sub(r"[^A-Za-z0-9]+", "-", endpoint).strip("-").lower() or "response"
        safe_train = re.sub(r"[^A-Za-z0-9]+", "-", str(train_number)).strip("-") if train_number else ""
        suffix = f"-{safe_train}" if safe_train else ""
        filename = f"{timestamp.astimezone(timezone.utc).strftime('%H%M%S-%f')}-{safe_endpoint}{suffix}-{uuid.uuid4().hex[:8]}.json"
        path = day_dir / filename
        document = {
            "collection_timestamp": timestamp.astimezone(timezone.utc).isoformat(),
            "endpoint": endpoint,
            "train_number": train_number,
            "http_status": http_status,
            "response": response,
        }
        path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    def save_run(
        self,
        *,
        run_id: str,
        train_number: str,
        timestamp: datetime,
        endpoint: str,
        response: Any,
        http_status: int = 200,
    ) -> Path:
        """Save one response under the collector's run/train partition."""

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        directory = (
            self.root
            / timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d")
            / re.sub(r"[^A-Za-z0-9_.-]+", "-", run_id)
            / re.sub(r"[^A-Za-z0-9_.-]+", "-", str(train_number))
        )
        directory.mkdir(parents=True, exist_ok=True)
        filename = f"{timestamp.astimezone(timezone.utc).strftime('%H%M%S-%f')}.json"
        path = directory / filename
        document = {
            "collection_timestamp": timestamp.astimezone(timezone.utc).isoformat(),
            "endpoint": endpoint,
            "train_number": train_number,
            "http_status": http_status,
            "response": response,
        }
        path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path
