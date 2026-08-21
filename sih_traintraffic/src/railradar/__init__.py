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
from .moving import MovingCollector
from .ml_preprocessing import load_dataset, run_preprocessing_pipeline

__all__ = [
    "Corridor",
    "MovingCollector",
    "NormalizedRouteGeometry",
    "NormalizedTrainStatus",
    "RailRadarClient",
    "Settings",
    "Station",
    "TrainSummary",
    "load_dataset",
    "load_settings",
    "run_preprocessing_pipeline",
]


