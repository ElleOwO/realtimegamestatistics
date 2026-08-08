"use client";

import { useEffect, useRef, useState } from "react";
import type { AnalyticsPayload } from "./useAnalytics";

export interface DerivedMetrics {
  /** Payloads received per second over a rolling 5 s window. */
  fps: number | null;
}

/**
 * Client-side derivations from the live AnalyticsPayload stream.
 * Pure presentation-layer metrics — the payload contract is unchanged.
 */
export function useDerivedMetrics(data: AnalyticsPayload | null): DerivedMetrics {
  const arrivalsRef = useRef<{ at: number }[]>([]);
  const [fps, setFps] = useState<number | null>(null);

  useEffect(() => {
    if (!data) return;
    const arrivals = arrivalsRef.current;
    const now = Date.now();
    arrivals.push({ at: now });
    const cutoff = now - 5000;
    while (arrivals.length > 0 && arrivals[0].at < cutoff) arrivals.shift();
    if (arrivals.length >= 2) {
      const spanS = (arrivals[arrivals.length - 1].at - arrivals[0].at) / 1000;
      setFps(spanS > 0.2 ? (arrivals.length - 1) / spanS : null);
    }
  }, [data]);

  return { fps };
}

/** Wall-clock ticker for stream-delay / clock displays. */
export function useNow(intervalMs = 1000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}
