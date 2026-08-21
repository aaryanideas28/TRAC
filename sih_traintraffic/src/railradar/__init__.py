"""RailRadar acquisition foundation for the Nexora prototype."""

from .client import RailRadarClient
from .config import Settings, load_settings
from .models import (
    Corridor,
    NormalizedRouteGeometry,
    NormalizedTrainStatus,
    Station,
    TrainSummary,
)

__all__ = [
    "Corridor",
    "NormalizedRouteGeometry",
    "NormalizedTrainStatus",
    "RailRadarClient",
    "Settings",
    "Station",
    "TrainSummary",
    "load_settings",
]
