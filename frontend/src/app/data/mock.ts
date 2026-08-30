import type { AnalyticsPayload, Player, ShapeMetrics, ShotEvent } from "../hooks/useAnalytics";

export const MOCK_PLAYERS: Player[] = Array.from({ length: 20 }, (_, index) => ({
  id: index + 1,
  team: index < 10 ? 0 : 1,
  role: index === 0 || index === 10 ? "goalkeeper" : "outfield",
  x_m: index < 10 ? 8 + index * 5 : 97 - (index - 10) * 5,
  y_m: 8 + (index % 5) * 13,
  confidence: 0.88,
})) as Player[];

const SHAPE: ShapeMetrics = {
  defensive_line_height_m: 39.8,
  team_length_m: 34.2,
  width_m: 43.1,
  centroid_x_m: 51.2,
  centroid_y_m: 33.6,
  convex_hull_area_m2: 1120,
  compactness_m: 18.4,
  players_behind_ball: 7,
  line_gap_1_m: 10.2,
  line_gap_2_m: 11.4,
  goalkeeper_line_gap_m: 15.1,
};

const SHOTS: ShotEvent[] = [
  { id: "demo-1", type: "shot", timestamp_ms: 420_000, match_clock_s: 420, period: 1, team: "team1", location: [19, 26], status: "confirmed", confidence: 0.79, xg: 0.09, speed_mps: 17.1, box_shot: false, on_target: false, outcome: "off_target", play_context: "open_play", shot_after_regain: false },
  { id: "demo-2", type: "shot", timestamp_ms: 720_000, match_clock_s: 720, period: 1, team: "team0", location: [91, 30], status: "confirmed", confidence: 0.88, xg: 0.31, speed_mps: 18.4, box_shot: true, on_target: true, outcome: "saved", play_context: "open_play", shot_after_regain: false },
  { id: "demo-3", type: "shot", timestamp_ms: 1_020_000, match_clock_s: 1020, period: 1, team: "team0", location: [87, 43], status: "confirmed", confidence: 0.82, xg: 0.12, speed_mps: 15.7, box_shot: true, on_target: false, outcome: "blocked", play_context: "open_play", shot_after_regain: true },
  { id: "demo-4", type: "shot", timestamp_ms: 1_380_000, match_clock_s: 1380, period: 1, team: "team1", location: [24, 37], status: "confirmed", confidence: 0.77, xg: 0.06, speed_mps: 16.2, box_shot: false, on_target: false, outcome: "off_target", play_context: "open_play", shot_after_regain: false },
  { id: "demo-5", type: "shot", timestamp_ms: 1_740_000, match_clock_s: 1740, period: 1, team: "team0", location: [94, 35], status: "confirmed", confidence: 0.93, xg: 0.48, speed_mps: 20.3, box_shot: true, on_target: true, outcome: "goal", play_context: "open_play", shot_after_regain: false },
  { id: "demo-6", type: "shot", timestamp_ms: 1_980_000, match_clock_s: 1980, period: 1, team: "team1", location: [18, 40], status: "confirmed", confidence: 0.81, xg: 0.18, speed_mps: 16.8, box_shot: true, on_target: true, outcome: "saved", play_context: "set_piece", shot_after_regain: true },
  { id: "demo-7", type: "shot", timestamp_ms: 2_340_000, match_clock_s: 2340, period: 1, team: "team0", location: [82, 19], status: "confirmed", confidence: 0.75, xg: 0.05, speed_mps: 14.9, box_shot: false, on_target: false, outcome: "off_target", play_context: "open_play", shot_after_regain: false },
  { id: "demo-8", type: "shot", timestamp_ms: 2_880_000, match_clock_s: 2880, period: 2, team: "team1", location: [14, 32], status: "confirmed", confidence: 0.84, xg: 0.21, speed_mps: 19.1, box_shot: true, on_target: true, outcome: "saved", play_context: "open_play", shot_after_regain: false },
  { id: "demo-9", type: "shot", timestamp_ms: 3_060_000, match_clock_s: 3060, period: 2, team: "team0", location: [89, 25], status: "confirmed", confidence: 0.8, xg: 0.14, speed_mps: 17.5, box_shot: true, on_target: false, outcome: "blocked", play_context: "open_play", shot_after_regain: false },
  { id: "demo-10", type: "shot", timestamp_ms: 3_240_000, match_clock_s: 3240, period: 2, team: "team0", location: [85, 38], status: "confirmed", confidence: 0.78, xg: 0.10, speed_mps: 15.2, box_shot: true, on_target: false, outcome: "off_target", play_context: "set_piece", shot_after_regain: false },
  { id: "demo-11", type: "shot", timestamp_ms: 3_420_000, match_clock_s: 3420, period: 2, team: "team1", location: [28, 49], status: "confirmed", confidence: 0.73, xg: 0.07, speed_mps: 14.6, box_shot: false, on_target: false, outcome: "off_target", play_context: "open_play", shot_after_regain: false },
  { id: "demo-12", type: "shot", timestamp_ms: 3_600_000, match_clock_s: 3600, period: 2, team: "team0", location: [96, 40], status: "confirmed", confidence: 0.9, xg: 0.21, speed_mps: 21.2, box_shot: true, on_target: true, outcome: "saved", play_context: "open_play", shot_after_regain: true },
  { id: "demo-13", type: "shot", timestamp_ms: 3_750_000, match_clock_s: 3750, period: 2, team: "team0", location: [92, 33], status: "candidate", confidence: 0.72, xg: 0.01, speed_mps: 13.8, box_shot: false, on_target: null, outcome: null, play_context: null, shot_after_regain: false },
];

export const MOCK_PAYLOAD: AnalyticsPayload = {
  schema_version: 2,
  pitch: { length_m: 105, width_m: 68 },
  frame: { id: 1842, source_timestamp_ms: 3_780_000, emitted_at_ms: Date.now() },
  runtime: { run_id: "demo", mode: "replay", source_state: "live", inference_fps: 10, payload_fps: 10, processing_latency_ms: 34, last_frame_age_ms: 0, reconnect_count: 0 },
  frame_quality: {
    visible_players: 20,
    ball_visible: true,
    detection_confidence: 0.88,
    ball_confidence: 0.81,
    calibration_confidence: 0.86,
    visible_pitch_fraction: 0.72,
    reprojection_error_m: 0.62,
    observation_coverage: 0.84,
  },
  match: {
    team_names: ["USask", "Opponent"],
    score: [0, 0],
    phase: "second_half",
    period: 2,
    clock_s: 3780,
    clock_running: true,
    directions: { first_half: ["right", "left"], second_half: ["left", "right"] },
    tactical_targets: {
      team0: {
        in_possession: { team_length_m: { min: 30, max: 38 }, width_m: { min: 40, max: 48 } },
        out_of_possession: { team_length_m: { min: 26, max: 34 }, width_m: { min: 36, max: 44 } },
      },
      team1: { in_possession: {}, out_of_possession: {} },
    },
  },
  observations: { players: MOCK_PLAYERS, ball: { x_m: 62, y_m: 36, confidence: 0.81 } },
  possession: { state: "team0", team0_pct: 56.2, team1_pct: 43.8, coverage: 0.81 },
  chance_quality: {
    teams: [
      { status: "experimental", shots: 8, pending_shots: 1, shots_on_target: 3, reviewed_on_target: 7, box_shots: 6, xg: 2.54, open_play_shots: 6, open_play_xg: 2.18, set_piece_shots: 1, set_piece_xg: 0.35 },
      { status: "experimental", shots: 5, pending_shots: 0, shots_on_target: 2, reviewed_on_target: 5, box_shots: 2, xg: 3.84, open_play_shots: 4, open_play_xg: 3.21, set_piece_shots: 1, set_piece_xg: 0.63 },
    ],
    shots: SHOTS,
  },
  progression: { teams: [
    { status: "experimental", final_third_entries: 11, penalty_area_entries: 4, entry_channels: { left: 5, centre: 2, right: 0 }, key_area_entries: { wide_left: 5, half_space_left: 0, central: 2, half_space_right: 0, wide_right: 0 }, field_tilt_pct: 61.4, behind_line_entries: 7, line_break_methods: { pass: 4, carry: 2, unknown: 1 } },
    { status: "experimental", final_third_entries: 27, penalty_area_entries: 11, entry_channels: { left: 4, centre: 8, right: 4 }, key_area_entries: { wide_left: 2, half_space_left: 2, central: 8, half_space_right: 1, wide_right: 3 }, field_tilt_pct: 38.6, behind_line_entries: 3, line_break_methods: { pass: 2, carry: 1, unknown: 0 } },
  ] },
  transitions: { teams: [
    { status: "experimental", high_regains: 6, dangerous_losses: 4, counterattacks: 3, shots_after_regain: 2, opponent_shots_after_loss: 1, average_recovery_s: 8.4 },
    { status: "experimental", high_regains: 3, dangerous_losses: 2, counterattacks: 2, shots_after_regain: 1, opponent_shots_after_loss: 2, average_recovery_s: 10.2 },
  ] },
  shape: { teams: [
    { in_possession: SHAPE, out_of_possession: { ...SHAPE, team_length_m: 31.5, width_m: 40.2 } },
    { in_possession: { ...SHAPE, defensive_line_height_m: 35.1 }, out_of_possession: { ...SHAPE, defensive_line_height_m: 37.2 } },
  ] },
  pressing: { teams: [
    { attempts: 12, successes: 5, success_pct: 41.7, high_press_attempts: 7, central_escapes: 2, forced_backward: 4, forced_long_candidates: 3, average_escape_s: 4.3, success_by_zone: { left: 2, centre: 2, right: 1 }, opponent_final_third_entries_allowed: 14, status: "experimental" },
    { attempts: 9, successes: 3, success_pct: 33.3, high_press_attempts: 5, central_escapes: 3, forced_backward: 2, forced_long_candidates: 2, average_escape_s: 5.1, success_by_zone: { left: 1, centre: 1, right: 1 }, opponent_final_third_entries_allowed: 22, status: "experimental" },
  ] },
  events: [
    { id: "event-1", type: "high_regain", match_clock_s: 510, team: "team0" },
    { id: "event-2", type: "shot", match_clock_s: 720, team: "team0", xg: 0.31, status: "confirmed" },
    { id: "event-3", type: "final_third_entry", match_clock_s: 940, team: "team0" },
    { id: "event-4", type: "dangerous_loss", match_clock_s: 1320, team: "team0" },
    { id: "event-5", type: "goal", match_clock_s: 1740, team: "team0", xg: 0.48, status: "confirmed" },
    { id: "event-6", type: "shot", match_clock_s: 1980, team: "team1", xg: 0.18, status: "confirmed" },
    { id: "event-7", type: "penalty_area_entry", match_clock_s: 2760, team: "team1" },
    { id: "event-8", type: "shot", match_clock_s: 2880, team: "team1", xg: 0.21, status: "confirmed" },
    { id: "event-9", type: "line_break_pass", match_clock_s: 3180, team: "team0" },
    { id: "event-10", type: "counterattack", match_clock_s: 3510, team: "team0" },
    { id: "event-11", type: "shot_after_regain", match_clock_s: 3600, team: "team0", xg: 0.21, status: "confirmed" },
    { id: "event-12", type: "shot", match_clock_s: 3750, team: "team0", xg: 0.01, status: "candidate" },
  ],
};
