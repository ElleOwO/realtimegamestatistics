"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { MOCK_PAYLOAD } from "../data/mock";

export type TeamIndex = 0 | 1;
export type TeamCode = "team0" | "team1";
export type MatchPhase = "pregame" | "first_half" | "halftime" | "second_half" | "full_time";

export interface Player {
  id: number | null;
  team: TeamIndex;
  role: "outfield" | "goalkeeper";
  x_m: number;
  y_m: number;
  confidence: number;
}

export interface BallObservation {
  x_m: number;
  y_m: number;
  confidence: number;
}

export interface TacticalRange { min?: number; max?: number }
export type TacticalTargets = Record<string, Record<string, Record<string, TacticalRange>>>;

export interface LiveMatchState {
  team_names: [string, string];
  score: [number, number];
  phase: MatchPhase;
  period: 1 | 2 | null;
  clock_s: number;
  clock_running: boolean;
  directions: {
    first_half: ["left" | "right", "left" | "right"];
    second_half: ["left" | "right", "left" | "right"];
  };
  tactical_targets: TacticalTargets;
}

export interface ShotEvent {
  id: string;
  type: "shot";
  timestamp_ms: number;
  match_clock_s: number | null;
  period: number | null;
  team: TeamCode;
  location: [number, number];
  status: "candidate" | "confirmed" | "corrected" | "rejected";
  confidence: number;
  xg: number;
  speed_mps: number;
  box_shot: boolean;
  on_target: boolean | null;
  outcome: string | null;
  play_context: "open_play" | "set_piece" | null;
  shot_after_regain: boolean;
}

export interface TeamChanceStats {
  status: "unavailable" | "partial" | "experimental" | "available";
  shots: number;
  pending_shots: number;
  shots_on_target: number;
  reviewed_on_target: number;
  box_shots: number;
  xg: number;
  open_play_shots: number;
  open_play_xg: number;
  set_piece_shots: number;
  set_piece_xg: number;
}

export interface TeamProgressionStats {
  status: "unavailable" | "partial" | "experimental" | "available";
  final_third_entries: number;
  penalty_area_entries: number;
  entry_channels: { left: number; centre: number; right: number };
  field_tilt_pct: number | null;
  behind_line_entries: number;
  line_break_methods: { pass: number; carry: number; unknown: number };
}

export interface TeamTransitionStats {
  status: "unavailable" | "partial" | "experimental" | "available";
  high_regains: number;
  dangerous_losses: number;
  counterattacks: number;
  shots_after_regain: number;
  opponent_shots_after_loss: number;
  average_recovery_s: number | null;
}

export interface ShapeMetrics {
  defensive_line_height_m: number;
  team_length_m: number;
  width_m: number;
  centroid_x_m: number;
  centroid_y_m: number;
  convex_hull_area_m2: number;
  compactness_m: number;
  players_behind_ball: number;
  line_gap_1_m: number;
  line_gap_2_m: number;
  goalkeeper_line_gap_m?: number;
}

export interface AnalyticsPayload {
  schema_version: 2;
  pitch: { length_m: 105; width_m: 68 };
  frame: { id: number; source_timestamp_ms: number; emitted_at_ms: number };
  frame_quality: {
    visible_players: number;
    ball_visible: boolean;
    detection_confidence: number | null;
    ball_confidence: number | null;
    calibration_confidence: number;
    visible_pitch_fraction: number;
    reprojection_error_m: number | null;
    observation_coverage: number;
  };
  match: LiveMatchState;
  observations: { players: Player[]; ball: BallObservation | null };
  possession: { state: TeamCode | "contested" | "unknown"; team0_pct: number | null; team1_pct: number | null; coverage: number };
  chance_quality: { teams: [TeamChanceStats, TeamChanceStats]; shots: ShotEvent[] };
  progression: { teams: [TeamProgressionStats, TeamProgressionStats] };
  transitions: { teams: [TeamTransitionStats, TeamTransitionStats] };
  shape: { teams: [{ in_possession: ShapeMetrics | null; out_of_possession: ShapeMetrics | null }, { in_possession: ShapeMetrics | null; out_of_possession: ShapeMetrics | null }] };
  pressing: { teams: [TeamPressingStats, TeamPressingStats] };
  events: Array<Record<string, unknown>>;
}

export interface TeamPressingStats {
  attempts: number;
  successes: number;
  success_pct: number | null;
  high_press_attempts: number;
  central_escapes: number;
  forced_backward: number;
  forced_long_candidates: number;
  average_escape_s: number | null;
  success_by_zone: { left: number; centre: number; right: number };
  opponent_final_third_entries_allowed: number;
  status: "unavailable" | "experimental";
}

export interface LiveCommand {
  type: "match.configure" | "match.set_phase" | "match.set_clock" | "match.set_score" | "match.set_targets" | "match.reset" | "event.review";
  payload?: Record<string, unknown>;
}

export function useAnalytics() {
  const [data, setData] = useState<AnalyticsPayload | null>(
    process.env.NEXT_PUBLIC_DEMO_MODE === "true" ? MOCK_PAYLOAD : null,
  );
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  const sendCommand = useCallback((command: LiveCommand) => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setError("Live command could not be sent while disconnected");
      return false;
    }
    socket.send(JSON.stringify({
      ...command,
      command_id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    }));
    return true;
  }, []);

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let unmounted = false;

    const connect = () => {
      const socket = new WebSocket(process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001/ws");
      socketRef.current = socket;
      socket.onopen = () => { setIsConnected(true); setError(null); };
      socket.onmessage = (event) => {
        try {
          const message: unknown = JSON.parse(event.data);
          if (message && typeof message === "object" && "schema_version" in message && (message as { schema_version?: unknown }).schema_version === 2) {
            setData(message as AnalyticsPayload);
          } else if (message && typeof message === "object" && "type" in message && (message as { type?: unknown }).type === "command.ack" && !(message as { ok?: boolean }).ok) {
            setError(String((message as { error?: unknown }).error || "Live command failed"));
          }
        } catch {
          setError("Received an invalid live analytics payload");
        }
      };
      socket.onerror = () => { setError("WebSocket connection failed"); setIsConnected(false); };
      socket.onclose = () => {
        setIsConnected(false);
        if (!unmounted) reconnectTimer = setTimeout(connect, 5000);
      };
    };
    connect();
    return () => {
      unmounted = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socketRef.current?.close();
    };
  }, []);

  return { data, isConnected, error, sendCommand };
}
