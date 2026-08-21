"""Exceptions raised by the RailRadar integration."""


class RailRadarError(Exception):
    """Base class for expected RailRadar integration failures."""


class ConfigurationError(RailRadarError):
    """The local configuration is missing or invalid."""


class ApiError(RailRadarError):
    """An HTTP error returned by RailRadar."""

    def __init__(self, status_code: int, message: str, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class AuthenticationError(ApiError):
    """RailRadar rejected the API key."""


class NotFoundError(ApiError):
    """The requested train or station resource was not found."""


class RateLimitError(ApiError):
    """RailRadar rate-limited the request."""


class UpstreamServiceError(ApiError):
    """RailRadar or an upstream data source returned a temporary 5xx error."""


class RequestTimeoutError(RailRadarError):
    """The request timed out after the configured retry policy."""


class InvalidJsonError(RailRadarError):
    """The server returned a successful response that was not valid JSON."""


class UnexpectedResponseError(RailRadarError):
    """The server returned JSON in a shape the client cannot consume."""
