"use client";

import { useState, useEffect, useCallback } from "react";

export interface Player {
  id: number;
  team: number;
  x_m: number;
  y_m: number;
  distance_km?: number;
  top_speed_ms?: number;
  top_speed_kmh?: number;
  is_sprinting?: boolean;
  sprint_count?: number;
  sprint_distance_km?: number;
  pass_accuracy?: number;
  passes_attempted?: number;
  passes_completed?: number;
  shots?: number;
  shots_on_target?: number;
  total_xg?: number;
  time_in_attack_zone_s?: number;
  dominant_zone?: string;
}

export interface Possession {
  team0_pct: number;
  team1_pct: number;
  team0_name: string;
  team1_name: string;
}

export interface ZoneStats {
  team0: Record<string, any>;
  team1: Record<string, any>;
}

export interface Heatmaps {
  team0: number[][];
  team1: number[][];
  ball: number[][];
}

export interface AnalyticsPayload {
  frame_id: number;
  timestamp: number;
  match_clock: number;
  possession: Possession;
  transition_speed_s: number;
  total_xg_team0: number;
  total_xg_team1: number;
  defensive_line_height_m: number;
  width_of_attack_m: number;
  convex_hull_area_m2: number;
  // Advanced Dynamic Metrics
  field_tilt_pct?: number;
  deep_completions?: number;
  vertical_compactness_m?: number;
  xg_per_possession?: number;
  ppda?: number;
  packing_rate?: number;
  attacking_third_recoveries?: number;
  counter_attack_threat_score?: number;
  sprint_decay_pct?: number;
  explosive_distance_m?: number;
  accel_decel_count?: number;
  // ---
  players: Player[];
  ball: [number, number] | null;
  zone_stats: ZoneStats;
  heatmaps: Heatmaps | null;
  insights?: { type: string; title: string; body: string }[];
  xg_timeline?: any[];
  key_events?: any[];
}

export function useAnalytics() {
  const [data, setData] = useState<AnalyticsPayload | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
    console.log(`Connecting to WebSocket: ${wsUrl}`);
    
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log("WebSocket connected ✅");
      setIsConnected(true);
      setError(null);
    };

    socket.onmessage = (event) => {
      try {
        const payload: AnalyticsPayload = JSON.parse(event.data);
        setData(payload);
      } catch (err) {
        console.error("Failed to parse analytics payload:", err);
      }
    };

    socket.onerror = (event) => {
      console.error("WebSocket error ❌", event);
      setError("WebSocket connection failed");
      setIsConnected(false);
    };

    socket.onclose = () => {
      console.log("WebSocket disconnected ❌");
      setIsConnected(false);
      // Try to reconnect after 5 seconds
      setTimeout(connect, 5000);
    };

    return socket;
  }, []);

  useEffect(() => {
    const socket = connect();
    return () => {
      socket.close();
    };
  }, [connect]);

  return { data, isConnected, error };
}
