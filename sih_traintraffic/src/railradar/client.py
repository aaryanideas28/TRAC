"""Small, reusable HTTP client for the documented RailRadar v1 API."""

from __future__ import annotations

import time
from typing import Any, Callable
from urllib.parse import quote

import requests

from .config import Settings
from .exceptions import (
    ApiError,
    AuthenticationError,
    InvalidJsonError,
    NotFoundError,
    RateLimitError,
    RequestTimeoutError,
    UnexpectedResponseError,
    UpstreamServiceError,
)


RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def _safe_text(value: Any, api_key: str) -> str:
    """Remove credential-shaped text before it can reach an exception message."""

    text = str(value)
    if api_key:
        text = text.replace(api_key, "[REDACTED]")
    return text.replace("Authorization: Bearer ", "Authorization: Bearer [REDACTED]")


class RailRadarClient:
    """Authenticated GET client with bounded retries for temporary failures."""

    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        before_request: Callable[[int], None] | None = None,
    ) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self._sleeper = sleeper
        self._before_request = before_request

    def _url(self, path: str) -> str:
        return f"{self.settings.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _parse_json(self, response: requests.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except (ValueError, requests.exceptions.JSONDecodeError) as exc:
            raise InvalidJsonError(
                f"RailRadar returned invalid JSON (HTTP {response.status_code})"
            ) from exc
        if not isinstance(payload, dict):
            raise UnexpectedResponseError("RailRadar returned a non-object JSON response")
        return payload

    def _error_message(self, payload: dict[str, Any] | None, status_code: int) -> str:
        if payload:
            error = payload.get("error")
            if isinstance(error, dict):
                code = error.get("code")
                message = error.get("message")
                if code and message:
                    return _safe_text(f"{code}: {message}", self.settings.api_key)
                if message:
                    return _safe_text(message, self.settings.api_key)
        return f"RailRadar returned HTTP {status_code}"

    def _retry_delay(self, response: requests.Response | None, attempt: int) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return max(0.0, min(float(retry_after), 60.0))
                except ValueError:
                    pass
        return min(self.settings.retry_delay * (2**attempt), 60.0)

    def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.settings.api_key}",
        }

        for attempt in range(self.settings.retry_count + 1):
            try:
                if self._before_request is not None:
                    self._before_request(attempt)
                response = self.session.get(
                    self._url(path),
                    params=params,
                    headers=headers,
                    timeout=self.settings.timeout,
                )
            except requests.exceptions.Timeout as exc:
                if attempt < self.settings.retry_count:
                    self._sleeper(self._retry_delay(None, attempt))
                    continue
                raise RequestTimeoutError(
                    f"RailRadar request timed out after {self.settings.timeout:g}s"
                ) from exc
            except requests.exceptions.ConnectionError as exc:
                if attempt < self.settings.retry_count:
                    self._sleeper(self._retry_delay(None, attempt))
                    continue
                raise UpstreamServiceError("Could not connect to RailRadar") from exc

            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt < self.settings.retry_count:
                    self._sleeper(self._retry_delay(response, attempt))
                    continue
                payload = None
                try:
                    payload = self._parse_json(response)
                except (InvalidJsonError, UnexpectedResponseError):
                    pass
                message = self._error_message(payload, response.status_code)
                if response.status_code == 429:
                    raise RateLimitError(response.status_code, message, payload)
                raise UpstreamServiceError(response.status_code, message, payload)

            if response.status_code == 401:
                payload = None
                try:
                    payload = self._parse_json(response)
                except (InvalidJsonError, UnexpectedResponseError):
                    pass
                raise AuthenticationError(
                    401, self._error_message(payload, 401), payload
                )
            if response.status_code == 404:
                payload = None
                try:
                    payload = self._parse_json(response)
                except (InvalidJsonError, UnexpectedResponseError):
                    pass
                raise NotFoundError(404, self._error_message(payload, 404), payload)
            if response.status_code >= 400:
                payload = None
                try:
                    payload = self._parse_json(response)
                except (InvalidJsonError, UnexpectedResponseError):
                    pass
                raise ApiError(
                    response.status_code,
                    self._error_message(payload, response.status_code),
                    payload,
                )

            return self._parse_json(response)

        raise UpstreamServiceError("RailRadar request ended without a response")

    @staticmethod
    def _path_value(value: str, label: str) -> str:
        cleaned = str(value).strip().upper()
        if not cleaned:
            raise ValueError(f"{label} must not be empty")
        return quote(cleaned, safe="")

    def get_station_directory(self) -> dict[str, Any]:
        """GET /v1/lookup/stations."""

        return self._request("lookup/stations")

    def get_local_trains(self, city: str = "Mumbai") -> dict[str, Any]:
        """GET /v1/lookup/trains/local."""

        return self._request("lookup/trains/local", params={"city": city})

    def get_station_live_board(
        self,
        station_code: str,
        *,
        hours: int = 4,
        include_intermediate: bool = True,
    ) -> dict[str, Any]:
        """GET /v1/stations/{code}/live."""

        if hours not in {2, 4, 6, 8}:
            raise ValueError("hours must be 2, 4, 6, or 8")
        params: dict[str, Any] = {"hours": hours}
        if include_intermediate:
            params["includeIntermediate"] = "true"
        return self._request(
            f"stations/{self._path_value(station_code, 'station_code')}/live",
            params=params,
        )

    def get_trains_between(
        self,
        from_station: str,
        to_station: str,
        *,
        date: str | None = None,
        train_type: str | None = None,
        category: str | None = None,
        by_city: bool = False,
        live: bool = False,
    ) -> dict[str, Any]:
        """GET /v1/trains/between/{from}/{to}."""

        params: dict[str, Any] = {}
        if date:
            params["date"] = date
        if train_type:
            params["type"] = train_type
        if category:
            params["category"] = category
        if by_city:
            params["byCity"] = "true"
        if live:
            params["live"] = "true"
        return self._request(
            f"trains/between/{self._path_value(from_station, 'from_station')}"
            f"/{self._path_value(to_station, 'to_station')}",
            params=params or None,
        )

    def get_live_train_status(
        self,
        train_number: str,
        *,
        date: str | None = None,
        authoritative: bool = False,
        halts_only: bool = False,
        geometry: bool = False,
        format: str | None = None,
        include_coordinates: bool = False,
    ) -> dict[str, Any]:
        """GET /v1/trains/{number}/live."""

        params: dict[str, Any] = {}
        if date:
            params["date"] = date
        if authoritative:
            params["authoritative"] = "true"
        if halts_only:
            params["haltsOnly"] = "true"
        if geometry:
            params["geometry"] = "true"
        if format:
            if format not in {"polyline", "geojson", "coordinates"}:
                raise ValueError("format must be polyline, geojson, or coordinates")
            params["format"] = format
        if include_coordinates:
            params["includeCoordinates"] = "true"
        return self._request(
            f"trains/{self._path_value(train_number, 'train_number')}/live",
            params=params or None,
        )

    def get_train_route_geometry(
        self,
        train_number: str,
        *,
        format: str = "geojson",
        stops: bool = False,
    ) -> dict[str, Any]:
        """GET /v1/trains/{number}/route."""

        if format not in {"polyline", "geojson", "coordinates"}:
            raise ValueError("format must be polyline, geojson, or coordinates")
        params = {"format": format}
        if stops:
            params["stops"] = "true"
        return self._request(
            f"trains/{self._path_value(train_number, 'train_number')}/route",
            params=params,
        )
