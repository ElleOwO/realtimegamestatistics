import type {
  AnalyticsPayload,
  ShapeMetrics,
  TeamChanceStats,
  TeamPressingStats,
  TeamProgressionStats,
  TeamTransitionStats,
} from "../hooks/useAnalytics";

export type LiveMetricStatus = "available" | "partial" | "experimental" | "unavailable";
export type LiveMetricValue = number | string | boolean | null;
export type LiveSectionId = "overview" | "territory" | "transitions" | "shape" | "pressing" | "quality";

export interface LiveReportMetric {
  id: string;
  label: string;
  values: [LiveMetricValue] | [LiveMetricValue, LiveMetricValue];
  unit: string | null;
  precision: number;
  status: LiveMetricStatus;
  confidence: number;
  coverage: number;
  explanation: string;
}

export interface LiveReportSection {
  id: LiveSectionId;
  label: string;
  description: string;
  metrics: LiveReportMetric[];
}

const clamp = (value: number) => Math.max(0, Math.min(value, 1));

function mergeStatus(
  statuses: [LiveMetricStatus, LiveMetricStatus],
  values: [LiveMetricValue, LiveMetricValue],
): LiveMetricStatus {
  if (statuses.every((status) => status === "unavailable") || values.every((value) => value == null)) return "unavailable";
  if (statuses.includes("partial") || statuses.includes("unavailable") || values.some((value) => value == null)) return "partial";
  if (statuses.includes("experimental")) return "experimental";
  return "available";
}

function pair(
  id: string,
  label: string,
  values: [LiveMetricValue, LiveMetricValue],
  statuses: [LiveMetricStatus, LiveMetricStatus],
  unit: string | null,
  confidence: number,
  coverage: number,
  explanation: string,
  precision = 0,
): LiveReportMetric {
  const visibleValues: [LiveMetricValue, LiveMetricValue] = [
    statuses[0] === "unavailable" ? null : values[0],
    statuses[1] === "unavailable" ? null : values[1],
  ];
  return {
    id,
    label,
    values: visibleValues,
    unit,
    precision,
    status: mergeStatus(statuses, visibleValues),
    confidence: clamp(confidence),
    coverage: clamp(coverage),
    explanation,
  };
}

function single(
  id: string,
  label: string,
  value: LiveMetricValue,
  unit: string | null,
  confidence: number,
  coverage: number,
  explanation: string,
  precision = 0,
): LiveReportMetric {
  const status: LiveMetricStatus = value == null
    ? "unavailable"
    : coverage < 0.5
      ? "partial"
      : "available";
  return { id, label, values: [value], unit, precision, status, confidence: clamp(confidence), coverage: clamp(coverage), explanation };
}

const chanceStatus = (team: TeamChanceStats): LiveMetricStatus => team.status;
const progressionStatus = (team: TeamProgressionStats): LiveMetricStatus => team.status;
const transitionStatus = (team: TeamTransitionStats): LiveMetricStatus => team.status;
const pressingStatus = (team: TeamPressingStats): LiveMetricStatus => team.status;

const EMPTY_CHANCE: TeamChanceStats = {
  status: "unavailable",
  shots: 0,
  pending_shots: 0,
  shots_on_target: 0,
  reviewed_on_target: 0,
  box_shots: 0,
  xg: 0,
  open_play_shots: 0,
  open_play_xg: 0,
  set_piece_shots: 0,
  set_piece_xg: 0,
};

const EMPTY_PROGRESSION: TeamProgressionStats = {
  status: "unavailable",
  final_third_entries: 0,
  penalty_area_entries: 0,
  entry_channels: { left: 0, centre: 0, right: 0 },
  key_area_entries: {
    wide_left: 0,
    half_space_left: 0,
    central: 0,
    half_space_right: 0,
    wide_right: 0,
  },
  field_tilt_pct: null,
  behind_line_entries: 0,
  line_break_methods: { pass: 0, carry: 0, unknown: 0 },
};

const EMPTY_TRANSITIONS: TeamTransitionStats = {
  status: "unavailable",
  high_regains: 0,
  dangerous_losses: 0,
  counterattacks: 0,
  shots_after_regain: 0,
  opponent_shots_after_loss: 0,
  average_recovery_s: null,
};

const EMPTY_PRESSING: TeamPressingStats = {
  attempts: 0,
  successes: 0,
  success_pct: null,
  high_press_attempts: 0,
  central_escapes: 0,
  forced_backward: 0,
  forced_long_candidates: 0,
  average_escape_s: null,
  success_by_zone: { left: 0, centre: 0, right: 0 },
  opponent_final_third_entries_allowed: 0,
  status: "unavailable",
};

const EMPTY_PAYLOAD: AnalyticsPayload = {
  schema_version: 2,
  pitch: { length_m: 105, width_m: 68 },
  frame: { id: 0, source_timestamp_ms: 0, emitted_at_ms: 0 },
  runtime: { run_id: "empty", mode: "replay", source_state: "waiting", inference_fps: 0, payload_fps: 0, processing_latency_ms: null, last_frame_age_ms: null, reconnect_count: 0 },
  frame_quality: {
    visible_players: 0,
    ball_visible: false,
    detection_confidence: null,
    ball_confidence: null,
    calibration_confidence: 0,
    visible_pitch_fraction: 0,
    reprojection_error_m: null,
    observation_coverage: 0,
  },
  match: {
    team_names: ["USask", "Opponent"],
    score: [0, 0],
    phase: "pregame",
    period: null,
    clock_s: 0,
    clock_running: false,
    directions: {
      first_half: ["right", "left"],
      second_half: ["left", "right"],
    },
    tactical_targets: {},
  },
  observations: { players: [], ball: null },
  possession: {
    state: "unknown",
    team0_pct: null,
    team1_pct: null,
    coverage: 0,
  },
  chance_quality: { teams: [{ ...EMPTY_CHANCE }, { ...EMPTY_CHANCE }], shots: [] },
  progression: { teams: [{ ...EMPTY_PROGRESSION }, { ...EMPTY_PROGRESSION }] },
  transitions: { teams: [{ ...EMPTY_TRANSITIONS }, { ...EMPTY_TRANSITIONS }] },
  shape: {
    teams: [
      { in_possession: null, out_of_possession: null },
      { in_possession: null, out_of_possession: null },
    ],
  },
  pressing: { teams: [{ ...EMPTY_PRESSING }, { ...EMPTY_PRESSING }] },
  events: [],
};

function shapeStatus(shape: ShapeMetrics | null, coverage: number): LiveMetricStatus {
  if (!shape) return "unavailable";
  return coverage < 0.5 ? "partial" : "available";
}

export function buildLiveReportSections(data: AnalyticsPayload): LiveReportSection[] {
  const chance = data.chance_quality.teams;
  const progression = data.progression.teams;
  const transitions = data.transitions.teams;
  const pressing = data.pressing.teams;
  const qualityCoverage = data.frame_quality.observation_coverage;
  const possessionCoverage = data.possession.coverage;
  const detectionConfidence = data.frame_quality.detection_confidence ?? 0;
  const ballConfidence = data.frame_quality.ball_confidence ?? 0;
  const calibrationConfidence = data.frame_quality.calibration_confidence;
  const chanceStatuses: [LiveMetricStatus, LiveMetricStatus] = [chanceStatus(chance[0]), chanceStatus(chance[1])];
  const progressionStatuses: [LiveMetricStatus, LiveMetricStatus] = [progressionStatus(progression[0]), progressionStatus(progression[1])];
  const transitionStatuses: [LiveMetricStatus, LiveMetricStatus] = [transitionStatus(transitions[0]), transitionStatus(transitions[1])];
  const pressingStatuses: [LiveMetricStatus, LiveMetricStatus] = [pressingStatus(pressing[0]), pressingStatus(pressing[1])];
  const possessionStatus: LiveMetricStatus = data.possession.team0_pct == null
    ? "unavailable"
    : possessionCoverage < 0.5
      ? "partial"
      : "available";
  const possessionStatuses: [LiveMetricStatus, LiveMetricStatus] = [possessionStatus, possessionStatus];

  const overview: LiveReportMetric[] = [
    pair("possession", "Possession", [data.possession.team0_pct, data.possession.team1_pct], possessionStatuses, "%", detectionConfidence, possessionCoverage, "Share of quality-gated controlled possession time.", 1),
    pair("shots", "Shots", [chance[0].shots, chance[1].shots], chanceStatuses, "shots", ballConfidence, qualityCoverage, "Cumulative automatic shot candidates, including pending reviews."),
    pair("xg", "Expected goals", [chance[0].xg, chance[1].xg], chanceStatuses, "xG", ballConfidence, qualityCoverage, "Cumulative xG from detected shot locations.", 2),
    pair("shots_on_target", "Shots on target", [chance[0].reviewed_on_target ? chance[0].shots_on_target : null, chance[1].reviewed_on_target ? chance[1].shots_on_target : null], chanceStatuses, "shots", ballConfidence, qualityCoverage, "Only displayed after shot outcomes have been reviewed."),
    pair("box_shots", "Box shots", [chance[0].box_shots, chance[1].box_shots], chanceStatuses, "shots", ballConfidence, qualityCoverage, "Detected shots originating inside the penalty area."),
    pair("open_play_xg", "Open-play xG", [chance[0].open_play_shots ? chance[0].open_play_xg : null, chance[1].open_play_shots ? chance[1].open_play_xg : null], chanceStatuses, "xG", ballConfidence, qualityCoverage, "xG from shots classified as open play.", 2),
    pair("set_piece_xg", "Set-piece xG", [chance[0].set_piece_shots ? chance[0].set_piece_xg : null, chance[1].set_piece_shots ? chance[1].set_piece_xg : null], chanceStatuses, "xG", ballConfidence, qualityCoverage, "xG from shots classified as set pieces.", 2),
    pair("pending_shots", "Pending shot reviews", [chance[0].pending_shots, chance[1].pending_shots], chanceStatuses, "shots", ballConfidence, qualityCoverage, "Candidates awaiting operator confirmation or correction."),
  ];

  const territory: LiveReportMetric[] = [
    pair("final_third_entries", "Final-third entries", [progression[0].final_third_entries, progression[1].final_third_entries], progressionStatuses, "entries", calibrationConfidence, qualityCoverage, "Controlled-ball crossings into the attacking third."),
    pair("penalty_area_entries", "Penalty-area entries", [progression[0].penalty_area_entries, progression[1].penalty_area_entries], progressionStatuses, "entries", calibrationConfidence, qualityCoverage, "Controlled-ball crossings into the penalty area."),
    pair("field_tilt", "Field tilt", [progression[0].field_tilt_pct, progression[1].field_tilt_pct], progressionStatuses, "%", calibrationConfidence, qualityCoverage, "Share of controlled possession registered in the attacking third.", 1),
    pair("behind_line_entries", "Behind-line entries", [progression[0].behind_line_entries, progression[1].behind_line_entries], progressionStatuses, "entries", calibrationConfidence, qualityCoverage, "Entries progressing beyond the opponent defensive line."),
    pair("entry_channels", "Entry channels", [formatChannels(progression[0]), formatChannels(progression[1])], progressionStatuses, null, calibrationConfidence, qualityCoverage, "Final-third entries split left, centre, and right."),
    pair("line_break_passes", "Line breaks by pass", [progression[0].line_break_methods.pass, progression[1].line_break_methods.pass], progressionStatuses, "entries", calibrationConfidence, qualityCoverage, "Behind-line entries created by a pass."),
    pair("line_break_carries", "Line breaks by carry", [progression[0].line_break_methods.carry, progression[1].line_break_methods.carry], progressionStatuses, "entries", calibrationConfidence, qualityCoverage, "Behind-line entries created by a carry."),
  ];

  const transitionMetrics: LiveReportMetric[] = [
    pair("high_regains", "High regains", [transitions[0].high_regains, transitions[1].high_regains], transitionStatuses, "events", calibrationConfidence, possessionCoverage, "Possession won high up the pitch."),
    pair("dangerous_losses", "Dangerous losses", [transitions[0].dangerous_losses, transitions[1].dangerous_losses], transitionStatuses, "events", calibrationConfidence, possessionCoverage, "Possession lost in a high-risk defensive location."),
    pair("counterattacks", "Counterattacks", [transitions[0].counterattacks, transitions[1].counterattacks], transitionStatuses, "events", calibrationConfidence, possessionCoverage, "Rapid forward progression following a regain."),
    pair("shots_after_regain", "Shots after regain", [transitions[0].shots_after_regain, transitions[1].shots_after_regain], transitionStatuses, "shots", ballConfidence, possessionCoverage, "Shots created within the transition window after regaining possession."),
    pair("opponent_shots_after_loss", "Opponent shots after loss", [transitions[0].opponent_shots_after_loss, transitions[1].opponent_shots_after_loss], transitionStatuses, "shots", ballConfidence, possessionCoverage, "Shots conceded shortly after losing possession."),
    pair("average_recovery", "Average recovery time", [transitions[0].average_recovery_s, transitions[1].average_recovery_s], transitionStatuses, "s", calibrationConfidence, possessionCoverage, "Average elapsed time from losing to regaining possession.", 1),
  ];

  const shapeMetrics: LiveReportMetric[] = [];
  const shapeFields: Array<[keyof ShapeMetrics, string, string | null]> = [
    ["defensive_line_height_m", "Defensive line height", "m"],
    ["team_length_m", "Team length", "m"],
    ["width_m", "Team width", "m"],
    ["convex_hull_area_m2", "Convex hull area", "m²"],
    ["compactness_m", "Compactness", "m"],
    ["line_gap_1_m", "Defence–midfield gap", "m"],
    ["line_gap_2_m", "Midfield–forward gap", "m"],
    ["players_behind_ball", "Players behind ball", "players"],
    ["goalkeeper_line_gap_m", "Goalkeeper–line gap", "m"],
  ];
  for (const phase of ["in_possession", "out_of_possession"] as const) {
    const shapes = [data.shape.teams[0][phase], data.shape.teams[1][phase]] as const;
    const statuses: [LiveMetricStatus, LiveMetricStatus] = [shapeStatus(shapes[0], qualityCoverage), shapeStatus(shapes[1], qualityCoverage)];
    for (const [field, label, unit] of shapeFields) {
      shapeMetrics.push(pair(
        `${phase}_${field}`,
        `${phase === "in_possession" ? "In possession" : "Out of possession"} · ${label}`,
        [shapes[0]?.[field] ?? null, shapes[1]?.[field] ?? null],
        statuses,
        unit,
        calibrationConfidence,
        qualityCoverage,
        "Rolling 10-second median; requires at least seven visible outfield players and a valid pitch projection.",
        1,
      ));
    }
  }

  const pressingMetrics: LiveReportMetric[] = [
    pair("press_attempts", "Pressure attempts", [pressing[0].attempts, pressing[1].attempts], pressingStatuses, "events", calibrationConfidence, possessionCoverage, "Detected pressure episodes against controlled possession."),
    pair("press_successes", "Pressure successes", [pressing[0].successes, pressing[1].successes], pressingStatuses, "events", calibrationConfidence, possessionCoverage, "Pressure episodes ending in a regain or loss of opponent control."),
    pair("press_success_pct", "Pressure success rate", [pressing[0].success_pct, pressing[1].success_pct], pressingStatuses, "%", calibrationConfidence, possessionCoverage, "Successful pressure episodes divided by attempts.", 1),
    pair("high_press_attempts", "High-press attempts", [pressing[0].high_press_attempts, pressing[1].high_press_attempts], pressingStatuses, "events", calibrationConfidence, possessionCoverage, "Pressure attempts initiated high up the pitch."),
    pair("central_escapes", "Central escapes allowed", [pressing[0].central_escapes, pressing[1].central_escapes], pressingStatuses, "events", calibrationConfidence, possessionCoverage, "Opponent pressure escapes through the central channel."),
    pair("forced_backward", "Forced backward", [pressing[0].forced_backward, pressing[1].forced_backward], pressingStatuses, "events", calibrationConfidence, possessionCoverage, "Pressure episodes forcing meaningful backward progression."),
    pair("forced_long", "Forced-long candidates", [pressing[0].forced_long_candidates, pressing[1].forced_long_candidates], pressingStatuses, "events", calibrationConfidence, possessionCoverage, "Candidate long releases produced under pressure."),
    pair("average_escape", "Average escape time", [pressing[0].average_escape_s, pressing[1].average_escape_s], pressingStatuses, "s", calibrationConfidence, possessionCoverage, "Average duration before the opponent escapes a pressure episode.", 1),
    pair("entries_allowed", "Final-third entries allowed", [pressing[0].opponent_final_third_entries_allowed, pressing[1].opponent_final_third_entries_allowed], pressingStatuses, "entries", calibrationConfidence, possessionCoverage, "Opponent final-third entries conceded while evaluating the press."),
  ];

  const quality: LiveReportMetric[] = [
    single("player_coverage", "Observation coverage", qualityCoverage * 100, "%", detectionConfidence, qualityCoverage, "Share of sampled frames passing the analytics quality gate.", 1),
    single("detection_confidence", "Player detection confidence", data.frame_quality.detection_confidence == null ? null : data.frame_quality.detection_confidence * 100, "%", detectionConfidence, qualityCoverage, "Mean confidence of visible player detections in the current frame.", 1),
    single("ball_confidence", "Ball detection confidence", data.frame_quality.ball_confidence == null ? null : data.frame_quality.ball_confidence * 100, "%", ballConfidence, qualityCoverage, "Ball confidence in the current frame.", 1),
    single("calibration_confidence", "Pitch calibration confidence", calibrationConfidence * 100, "%", calibrationConfidence, qualityCoverage, "Confidence in the current image-to-pitch projection.", 1),
    single("visible_pitch", "Visible pitch fraction", data.frame_quality.visible_pitch_fraction * 100, "%", calibrationConfidence, qualityCoverage, "Estimated fraction of the image covered by the calibrated pitch region.", 1),
    single("reprojection_error", "Reprojection error", data.frame_quality.reprojection_error_m, "m", calibrationConfidence, qualityCoverage, "Mean landmark reprojection error; lower is better.", 2),
    single("visible_players", "Visible players", data.frame_quality.visible_players, "players", detectionConfidence, qualityCoverage, "Players currently detected and projected."),
    single("ball_visible", "Ball visible", data.frame_quality.ball_visible, null, ballConfidence, qualityCoverage, "Whether the ball is detected in the current frame."),
  ];

  return [
    { id: "overview", label: "Overview", description: "Possession and chance quality accumulated from the live feed.", metrics: overview },
    { id: "territory", label: "Territory", description: "Progression, entries, and attacking-third control.", metrics: territory },
    { id: "transitions", label: "Transitions", description: "Regains, losses, recoveries, and counterattacking outcomes.", metrics: transitionMetrics },
    { id: "shape", label: "Shape", description: "Rolling in-possession and out-of-possession team structure.", metrics: shapeMetrics },
    { id: "pressing", label: "Pressing", description: "Pressure attempts, outcomes, and opponent escape behaviour.", metrics: pressingMetrics },
    { id: "quality", label: "Quality", description: "Current computer-vision confidence and cumulative usable coverage.", metrics: quality },
  ];
}

export function buildLiveReportPlaceholders(): LiveReportSection[] {
  return buildLiveReportSections(EMPTY_PAYLOAD).map((section) => ({
    ...section,
    metrics: section.metrics.map((metric) => ({
      ...metric,
      values: metric.values.length === 2 ? [null, null] : [null],
      status: "unavailable",
      confidence: 0,
      coverage: 0,
    })),
  }));
}

function formatChannels(team: TeamProgressionStats): string {
  const { left, centre, right } = team.entry_channels;
  return `L ${left} · C ${centre} · R ${right}`;
}
