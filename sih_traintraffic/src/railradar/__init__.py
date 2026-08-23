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
from .network_scheduler import (
    EdgeOccupancySchedule,
    NetworkScheduleOptimizer,
    NetworkScheduleResult,
    TrainScheduleInput,
    TrainScheduleSummary,
)
from .railway_graph import (
    RailwayNetworkGraph,
    StationNode,
    TrackEdge,
    TrainRoute,
    build_central_line_graph,
)

__all__ = [
    "Corridor",
    "EdgeOccupancySchedule",
    "MovingCollector",
    "NetworkScheduleOptimizer",
    "NetworkScheduleResult",
    "NormalizedRouteGeometry",
    "NormalizedTrainStatus",
    "RailRadarClient",
    "RailwayNetworkGraph",
    "Settings",
    "Station",
    "StationNode",
    "TrackEdge",
    "TrainRoute",
    "TrainScheduleInput",
    "TrainScheduleSummary",
    "TrainSummary",
    "build_central_line_graph",
    "load_dataset",
    "load_settings",
    "run_preprocessing_pipeline",
]


