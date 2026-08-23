export interface StationNode {
  station_code: string;
  station_name: string;
  pos_x: number;
  pos_y: number;
  lat?: number;
  lon?: number;
  line_corridor: string;
  is_terminal: boolean;
  is_halt: boolean;
}

export type TrainStatus = 'Moving' | 'Waiting' | 'Delayed' | 'Conflict';
export type TrainType = 'Express' | 'Local' | 'Freight' | 'Passenger';
export type TrainPriority = 'High' | 'Medium' | 'Low';

export interface Train {
  id: string;
  name: string;
  type: TrainType;
  origin: string;
  origin_name: string;
  destination: string;
  destination_name: string;
  current_location: string;
  current_location_name: string;
  speed_kmh: number;
  scheduled_eta: string;
  expected_eta: string;
  delay_min: number;
  priority: TrainPriority;
  assigned_track: string;
  status: TrainStatus;
  progress_percent: number;
  current_edge_id: string;
  route: string[];
}

export type ActionType = 'PROCEED' | 'HOLD' | 'TRACK_CHANGE';

export interface AiRecommendation {
  id: string;
  affected_train_id: string;
  affected_train_name: string;
  action: string;
  action_type: ActionType;
  assigned_track: string;
  waiting_time_sec: number;
  expected_delay_reduction_min: number;
  reason: string;
  confidence_score: number;
  resource_involved?: string;
  trains_involved?: string[];
  conflict_predicted_min?: number;
}

export type ConflictSeverity = 'HIGH' | 'MEDIUM' | 'LOW';

export interface ConflictItem {
  id: string;
  trains_involved: string[];
  section: string;
  predicted_in_min: number;
  severity: ConflictSeverity;
  status: 'DETECTED' | 'RESOLVED';
  ai_resolution: string;
}

export interface KpiMetrics {
  active_trains: number;
  throughput_trains_per_hr: number;
  throughput_trend_pct: number;
  average_delay_min: number;
  delay_trend_pct: number;
  track_utilization_pct: number;
  utilization_trend_pct: number;
  conflicts_detected: number;
  conflicts_resolved: number;
}

export interface MetricComparison {
  throughput: number;
  throughput_unit: string;
  average_delay: number;
  average_delay_unit: string;
  track_utilization: number;
  track_utilization_unit: string;
  waiting_time: number;
  waiting_time_unit: string;
  conflicts: number;
}

export interface BeforeAfterMetrics {
  without_ai: MetricComparison;
  with_ai: MetricComparison;
  improvements: {
    throughput_increase_pct: number;
    delay_reduction_pct: number;
    utilization_increase_pct: number;
    waiting_time_reduction_pct: number;
    conflict_elimination_pct: number;
  };
}

export interface Validated10TrainBenchmark {
  legacy_baseline: {
    total_completion_delay_min: number;
    additional_hold_min: number;
    delay_variance_min2: number;
    modeled_conflicts: number;
    zero_hold_trains: number;
  };
  infrastructure_aware: {
    total_completion_delay_min: number;
    additional_hold_min: number;
    delay_variance_min2: number;
    modeled_conflicts: number;
    zero_hold_trains: number;
  };
  improvements: {
    total_completion_delay_pct: number;
    optimizer_added_hold_pct: number;
    delay_variance_pct: number;
    modeled_conflicts_pct: number;
    zero_hold_trains_change: string;
  };
}

export interface NetworkData {
  corridor: string;
  station_count: number;
  track_segment_count: number;
  nodes: StationNode[];
  edges: any[];
  track_resources: any[];
}

export interface SimulationConfig {
  scenario: string;
  density: string;
  track_status: string;
  blocked_section?: string;
  priority_train_id?: string;
}
