import { useEffect, useMemo, useRef, useState } from 'react';

export interface AnalyticsInsight {
  type: string;
  title: string;
  body: string;
  minute?: number;
}

export interface AnalyticsPlayer {
  id: number;
  team: number;
  x_m: number;
  y_m: number;
  distance_km?: number;
  top_speed_kmh?: number;
}

export interface AnalyticsTimelinePoint {
  minute: number;
  team0_xg: number;
  team1_xg: number;
}

export interface AnalyticsPayload {
  frame_id: number;
  timestamp: number;
  match_clock: number;
  possession: {
    team0_pct: number;
    team1_pct: number;
    team0_name?: string;
    team1_name?: string;
  };
  transition_speed_s: number;
  total_xg_team0: number;
  total_xg_team1: number;
  defensive_line_height_m: number;
  width_of_attack_m: number;
  convex_hull_area_m2: number;
  players: AnalyticsPlayer[];
  ball: [number, number] | null;
  xg_timeline: AnalyticsTimelinePoint[];
  insights: AnalyticsInsight[];
}

export interface UseAnalyticsResult {
  data: AnalyticsPayload | null;
  connected: boolean;
  error: string | null;
}

const FALLBACK_WS_URL = 'ws://localhost:8000/ws';

export function useAnalytics(): UseAnalyticsResult {
  const [data, setData] = useState<AnalyticsPayload | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Keep timeout id in a ref so we can cancel pending reconnects on unmount.
  const reconnectTimeoutRef = useRef<number | null>(null);

  const wsUrl = useMemo(
    // Vite injects env vars at build time; fallback keeps local dev resilient.
    () => import.meta.env.VITE_WS_URL ?? FALLBACK_WS_URL,
    [],
  );

  useEffect(() => {
    let ws: WebSocket | null = null;
    let cancelled = false;

    const connect = () => {
      if (cancelled) {
        return;
      }

      try {
        ws = new WebSocket(wsUrl);
      } catch (err) {
        setConnected(false);
        setError(err instanceof Error ? err.message : 'Failed to create WebSocket');
        // Retry after a short delay (backend may still be starting up).
        reconnectTimeoutRef.current = window.setTimeout(connect, 2000);
        return;
      }

      ws.onopen = () => {
        setConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as AnalyticsPayload;
          setData(payload);
        } catch {
          // Guard against malformed payloads so one bad frame does not crash UI state.
          setError('Received invalid analytics payload JSON');
        }
      };

      ws.onerror = () => {
        setConnected(false);
      };

      ws.onclose = () => {
        setConnected(false);
        if (!cancelled) {
          // Auto-reconnect keeps live view stable across transient network drops.
          reconnectTimeoutRef.current = window.setTimeout(connect, 2000);
        }
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimeoutRef.current !== null) {
        window.clearTimeout(reconnectTimeoutRef.current);
      }
      // Explicit close avoids leaked sockets during route changes/hot reload.
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        ws.close();
      }
    };
  }, [wsUrl]);

  return { data, connected, error };
}
