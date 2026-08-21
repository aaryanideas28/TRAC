"""Environment-backed configuration for the RailRadar client."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values

from .exceptions import ConfigurationError


DEFAULT_BASE_URL = "https://api.railradar.in/v1"
DEFAULT_TIMEOUT = 15.0
DEFAULT_RETRY_COUNT = 2
DEFAULT_RETRY_DELAY = 1.0


@dataclass(frozen=True)
class Settings:
    """Runtime settings needed by the RailRadar client."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    retry_count: int = DEFAULT_RETRY_COUNT
    retry_delay: float = DEFAULT_RETRY_DELAY


def _as_float(values: Mapping[str, str], name: str, default: float) -> float:
    raw = values.get(name)
    if raw in (None, ""):
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"{name} must be a number") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero")
    return value


def _as_int(values: Mapping[str, str], name: str, default: int) -> int:
    raw = values.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value < 0:
        raise ConfigurationError(f"{name} must not be negative")
    return value


def load_settings(env_file: str | Path = ".env", environ: Mapping[str, str] | None = None) -> Settings:
    """Load settings from ``.env`` and the process environment.

    Explicit process environment values take precedence over values in the
    dotenv file. The API key is only held in memory and is never printed.
    """

    values = {key: value for key, value in dotenv_values(env_file).items() if value is not None}
    values.update(dict(os.environ if environ is None else environ))

    api_key = str(values.get("RAILRADAR_API_KEY", "")).strip()
    if not api_key:
        raise ConfigurationError("RAILRADAR_API_KEY is not configured")

    base_url = str(values.get("RAILRADAR_API_BASE_URL", DEFAULT_BASE_URL)).strip().rstrip("/")
    if not base_url.startswith("https://"):
        raise ConfigurationError("RAILRADAR_API_BASE_URL must use HTTPS")

    return Settings(
        api_key=api_key,
        base_url=base_url,
        timeout=_as_float(values, "RAILRADAR_TIMEOUT", DEFAULT_TIMEOUT),
        retry_count=_as_int(values, "RAILRADAR_RETRY_COUNT", DEFAULT_RETRY_COUNT),
        retry_delay=_as_float(values, "RAILRADAR_RETRY_DELAY", DEFAULT_RETRY_DELAY),
    )
