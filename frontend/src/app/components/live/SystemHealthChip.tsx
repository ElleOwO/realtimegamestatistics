"use client";

import { useState } from "react";
import type { AnalyticsPayload } from "../../hooks/useAnalytics";
import { useNow } from "../../hooks/useDerivedMetrics";
import {
  healthStatus,
  streamDelayS,
  type HealthStatus,
} from "../../lib/deriveMatchMetrics";

const STATUS_STYLE: Record<HealthStatus, { dot: string; label: string; text: string }> = {
  live: { dot: "bg-primary animate-pulse", label: "Live", text: "text-primary" },
  delayed: { dot: "bg-amber-400", label: "Delayed", text: "text-amber-400" },
  offline: { dot: "bg-zinc-600", label: "Offline", text: "text-muted-foreground" },
  demo: { dot: "bg-secondary", label: "Demo", text: "text-secondary" },
};

/**
 * ChatGPT's "system confidence" panel, compressed into the top bar:
 * stream delay, visible players, payload rate, last-frame age.
 */
export function SystemHealthChip({
  data,
  isConnected,
  fps,
}: {
  data: AnalyticsPayload | null;
  isConnected: boolean;
  fps: number | null;
}) {
  const [open, setOpen] = useState(false);
  const now = useNow(1000);
  const delayS = data ? streamDelayS(data.frame.emitted_at_ms / 1000, now) : null;
  const status = healthStatus({
    isConnected,
    hasData: data != null,
    delayS,
    // NB: keep inlined — assigning the env comparison to a const trips a
    // SWC minify bug (declaration elided, shorthand reference kept).
    demoMode: process.env.NEXT_PUBLIC_DEMO_MODE === "true",
  });
  const style = STATUS_STYLE[status];
  const visible = data?.frame_quality.visible_players ?? 0;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-full border border-zinc-800 bg-card px-3 py-1.5 transition-colors hover:border-zinc-700"
        aria-label="System confidence details"
      >
        <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
        <span
          className={`text-[10px] font-black uppercase tracking-[0.18em] ${style.text}`}
        >
          {style.label}
        </span>
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-50 mt-2 w-56 rounded-xl border border-zinc-800 bg-popover p-3 shadow-xl">
            <p className="mb-2 text-[9px] font-black uppercase tracking-[0.18em] text-muted-foreground">
              System confidence
            </p>
            <dl className="space-y-1.5 text-xs stat-numerals">
              <Row label="Stream delay" value={delayS != null ? `${delayS.toFixed(1)} s` : "—"} />
              <Row label="Players visible" value={data ? `${visible} / 22` : "—"} />
              <Row label="Payload rate" value={fps != null ? `${fps.toFixed(1)} /s` : "—"} />
              <Row label="Calibration" value={data ? `${(data.frame_quality.calibration_confidence * 100).toFixed(0)}%` : "—"} />
              <Row label="Detection" value={data?.frame_quality.detection_confidence != null ? `${(data.frame_quality.detection_confidence * 100).toFixed(0)}%` : "—"} />
              <Row label="Ball" value={data?.frame_quality.ball_visible ? `${((data.frame_quality.ball_confidence ?? 0) * 100).toFixed(0)}%` : "not visible"} />
              <Row label="Reprojection" value={data?.frame_quality.reprojection_error_m != null ? `${data.frame_quality.reprojection_error_m.toFixed(2)} m` : "—"} />
              <Row label="Coverage" value={data ? `${(data.frame_quality.observation_coverage * 100).toFixed(0)}%` : "—"} />
              <Row label="Last frame" value={data ? `#${data.frame.id}` : "—"} />
              <Row label="Socket" value={isConnected ? "connected" : "disconnected"} />
            </dl>
            <p className="mt-2 border-t border-zinc-800 pt-2 text-[9px] leading-relaxed text-muted-foreground">
              Tactical metrics pause automatically when projection quality is below the gate.
            </p>
          </div>
        </>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-bold">{value}</dd>
    </div>
  );
}
