export type JobState =
  | "queued"
  | "preflight"
  | "waiting_for_setup"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "interrupted";

export interface Period {
  number: number;
  start_ms: number;
  end_ms: number;
}

export interface AnalysisJob {
  id: string;
  match_id: string;
  state: JobState;
  progress: number;
  current_video_ms: number;
  processing_fps: number | null;
  eta_seconds: number | null;
  detection_coverage: number;
  calibration_coverage: number;
  failure_code: string | null;
  failure_detail: string | null;
  log_tail: string[];
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Match {
  id: string;
  source_filename: string;
  source_codec: string | null;
  source_width: number | null;
  source_height: number | null;
  duration_ms: number;
  fps: number | null;
  home_team: string | null;
  away_team: string | null;
  home_score: number | null;
  away_score: number | null;
  usask_side: "home" | "away" | null;
  periods: Period[];
  directions: Record<string, "left" | "right">;
  tactical_targets: Record<string, Record<string, Record<string, { min?: number; max?: number }>>>;
  team_mapping: { usask_cluster?: number; opponent_cluster?: number };
  thumbnail_paths: string[];
  status: string;
  setup_complete: boolean;
  created_at: string;
  updated_at: string;
  latest_job: AnalysisJob | null;
}

export interface InboxFile {
  filename: string;
  size_bytes: number;
  modified_at: string;
}

export interface Observation {
  id: number;
  match_id: string;
  timestamp_ms: number;
  object_type: "player" | "ball" | string;
  track_id: number | null;
  team: "home" | "away" | null;
  image_box: number[] | null;
  pitch_x_m: number | null;
  pitch_y_m: number | null;
  detection_confidence: number;
  calibration_confidence: number | null;
}

export interface MatchEvent {
  id: string;
  match_id: string;
  type: string;
  team: "home" | "away" | null;
  period: number | null;
  timestamp_ms: number;
  pitch_x_m: number | null;
  pitch_y_m: number | null;
  possession_context: string | null;
  play_context: "open_play" | "set_piece" | null;
  confidence: number;
  review_status: "pending" | "confirmed" | "corrected" | "rejected";
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface MetricValue<T = unknown> {
  value: T | null;
  unit: string | null;
  confidence: number;
  sample_coverage: number;
  status: "available" | "partial" | "experimental" | "unavailable";
  explanation: string | null;
}

export interface MatchReport {
  match_id: string;
  provisional: boolean;
  generated_at: string;
  score: {
    home_team: string | null;
    away_team: string | null;
    home: number | null;
    away: number | null;
    source: "operator";
    reconciled_goals: { home: number; away: number; matches_final_score: boolean };
  };
  summary: Record<string, MetricValue>;
  events: MatchEvent[];
  shot_map: Array<Record<string, unknown>>;
  territorial: Record<string, MetricValue>;
  transitions: Record<string, MetricValue>;
  shape: Record<string, MetricValue>;
  pressing: Record<string, MetricValue> | null;
  set_pieces: Record<string, MetricValue> | null;
  time_series: Record<string, Array<Record<string, unknown>>>;
  quality: Record<string, MetricValue>;
  diagnostics: string[];
}

export interface StreamMessage {
  type:
    | "job_status"
    | "progress"
    | "provisional_report"
    | "review_updated"
    | "report_updated"
    | "completed"
    | "error";
  match_id: string;
  payload: Record<string, unknown>;
  sent_at: string;
}
