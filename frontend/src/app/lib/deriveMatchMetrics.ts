/** Seconds a backend payload is behind wall-clock time. */
export function streamDelayS(timestampSeconds: number | undefined, nowMs: number): number | null {
  if (timestampSeconds == null) return null;
  return Math.max(0, nowMs / 1000 - timestampSeconds);
}

export type HealthStatus = "live" | "delayed" | "offline" | "demo";

export function healthStatus({ isConnected, hasData, delayS, demoMode }: {
  isConnected: boolean;
  hasData: boolean;
  delayS: number | null;
  demoMode: boolean;
}): HealthStatus {
  if (isConnected && delayS != null) {
    if (delayS <= 3) return "live";
    if (delayS <= 15) return "delayed";
    return "offline";
  }
  if (demoMode && hasData) return "demo";
  return "offline";
}

export function formatClock(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}
