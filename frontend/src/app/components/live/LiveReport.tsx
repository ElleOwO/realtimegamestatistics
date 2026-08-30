"use client";

import { useMemo, useState } from "react";
import { Activity, ArrowRight, RadioTower } from "lucide-react";
import type { AnalyticsPayload } from "../../hooks/useAnalytics";
import {
  buildLiveReportPlaceholders,
  buildLiveReportSections,
  type LiveMetricStatus,
  type LiveMetricValue,
  type LiveReportMetric,
  type LiveSectionId,
} from "../../lib/liveReportMetrics";

const STATUS_STYLES: Record<LiveMetricStatus, string> = {
  available: "border-primary/30 bg-primary/10 text-primary",
  partial: "border-blue-500/25 bg-blue-500/15 text-blue-200",
  experimental: "border-amber-500/25 bg-amber-500/15 text-amber-200",
  unavailable: "border-white/10 bg-white/[0.03] text-muted-foreground",
};

export function LiveReport({ data }: { data: AnalyticsPayload | null }) {
  const [active, setActive] = useState<LiveSectionId>("overview");
  const sections = useMemo(
    () => data ? buildLiveReportSections(data) : buildLiveReportPlaceholders(),
    [data],
  );
  const section = sections.find((item) => item.id === active) ?? sections[0];
  const teamNames: [string, string] = data?.match.team_names ?? ["USask", "Opponent"];

  return (
    <section className="w-full min-w-0 overflow-hidden rounded-xl border border-white/10 bg-card">
      <div className="grid min-w-0 xl:grid-cols-[13rem_minmax(0,1fr)]">
        <aside className="min-w-0 border-b border-white/10 bg-background/35 p-3 xl:border-b-0 xl:border-r xl:p-4">
          <div className="mb-4 hidden px-2 pt-1 xl:block">
            <p className="eyebrow text-primary">Analysis desk</p>
            <h2 className="mt-2 font-display text-2xl font-semibold uppercase tracking-wide">Live report</h2>
            <p className="mt-2 text-xs leading-5 text-muted-foreground">Choose a match question.</p>
          </div>
          <div role="tablist" aria-label="Live report sections" className="flex gap-1 overflow-x-auto xl:flex-col xl:overflow-visible">
            {sections.map((item) => <button key={item.id} role="tab" aria-selected={active === item.id} onClick={() => setActive(item.id)} className={`group flex shrink-0 items-center justify-between gap-5 rounded-sm px-3 py-2.5 text-left font-mono text-[10px] font-semibold uppercase tracking-[0.13em] transition xl:w-full ${active === item.id ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-white/[0.045] hover:text-white"}`}>
              {item.label}<ArrowRight className={`h-3 w-3 transition ${active === item.id ? "opacity-100" : "opacity-0 group-hover:opacity-50"}`} />
            </button>)}
          </div>
          <div className="mt-5 hidden border-t border-white/10 px-2 pt-4 xl:block">
            <p className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.12em] text-muted-foreground">
              {data ? <Activity className="h-3 w-3 text-primary" /> : <RadioTower className="h-3 w-3" />}
              {data ? `Frame ${data.frame.id}` : "Awaiting live feed"}
            </p>
            <p className="mt-1.5 text-[10px] leading-4 text-muted-foreground">
              {data ? "Values refresh as each usable frame arrives." : "Metric positions stay visible and fill automatically when analysis begins."}
            </p>
          </div>
        </aside>

        <div className="w-full min-w-0 overflow-hidden p-4 sm:p-6">
          <header className="section-rule flex min-w-0 flex-wrap items-end justify-between gap-4 pl-4">
            <div className="min-w-0 flex-1">
              <p className="eyebrow text-primary">{section.label}</p>
              <h3 className="mt-2 max-w-2xl break-words font-display text-2xl font-semibold uppercase tracking-[0.025em] sm:text-3xl">{section.description}</h3>
            </div>
            <div className="flex items-center gap-4 font-mono text-[9px] uppercase tracking-[0.12em] text-muted-foreground">
              <span><i className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-primary" />{teamNames[0]}</span>
              <span><i className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-secondary" />{teamNames[1]}</span>
            </div>
          </header>

          <div className="mt-6 grid min-w-0 gap-px overflow-hidden rounded-md border border-white/10 bg-white/10 sm:grid-cols-2 2xl:grid-cols-3">
            {section.metrics.map((metric) => <LiveMetricCard key={metric.id} metric={metric} teamNames={teamNames} />)}
          </div>
        </div>
      </div>
    </section>
  );
}

function LiveMetricCard({ metric, teamNames }: { metric: LiveReportMetric; teamNames: [string, string] }) {
  const isTeamComparison = metric.values.length === 2;
  const ratio = comparisonRatio(metric.values);
  return (
    <article className="flex min-h-48 min-w-0 flex-col bg-card p-4 transition-colors hover:bg-[#353535] sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="font-display text-base font-semibold uppercase tracking-[0.04em] text-white">{metric.label}</p>
        <span className={`shrink-0 rounded-sm border px-1.5 py-0.5 font-mono text-[8px] font-semibold uppercase ${STATUS_STYLES[metric.status]}`}>{metric.status}</span>
      </div>
      {isTeamComparison ? (
        <>
          <div className="mt-5 grid grid-cols-2 gap-3">
            <MetricValue name={teamNames[0]} value={metric.values[0]} metric={metric} color="text-primary" />
            <MetricValue name={teamNames[1]} value={metric.values[1] ?? null} metric={metric} color="text-secondary" align="right" />
          </div>
          {ratio != null && <div aria-hidden="true" className="mt-3 flex h-1.5 overflow-hidden bg-background"><span className="bg-primary transition-[width] duration-500" style={{ width: `${ratio}%` }} /><span className="flex-1 bg-secondary" /></div>}
        </>
      ) : (
        <div className="mt-4"><MetricValue value={metric.values[0]} metric={metric} color="text-foreground" /></div>
      )}
      <div className="mt-auto pt-4">
        <div className="mb-2 flex items-center gap-2">
          <span className="font-mono text-[8px] uppercase tracking-wider text-muted-foreground">Coverage</span>
          <span className="h-px flex-1 bg-white/10"><i className="block h-px bg-white/45" style={{ width: `${metric.coverage * 100}%` }} /></span>
          <span className="font-mono text-[8px] tabular-nums text-muted-foreground">{(metric.coverage * 100).toFixed(0)}%</span>
        </div>
        <p className="line-clamp-2 text-[10px] leading-4 text-muted-foreground">{metric.explanation}</p>
      </div>
    </article>
  );
}

function MetricValue({ name, value, metric, color, align }: {
  name?: string;
  value: LiveMetricValue;
  metric: LiveReportMetric;
  color: string;
  align?: "right";
}) {
  return <div className={`min-w-0 ${align === "right" ? "text-right" : ""}`}>
    {name && <p className={`truncate font-mono text-[8px] font-semibold uppercase tracking-[0.12em] ${color}`}>{name}</p>}
    <p className="mt-1 break-words font-mono text-2xl font-medium tabular-nums text-white sm:text-3xl">{formatValue(value, metric.precision)}{value != null && metric.unit && <span className="ml-1 font-sans text-[10px] font-medium text-muted-foreground">{metric.unit}</span>}</p>
  </div>;
}

function comparisonRatio(values: LiveReportMetric["values"]): number | null {
  if (values.length !== 2 || typeof values[0] !== "number" || typeof values[1] !== "number") return null;
  const total = Math.max(0, values[0]) + Math.max(0, values[1]);
  return total > 0 ? Math.max(0, values[0]) / total * 100 : 50;
}

function formatValue(value: LiveMetricValue, precision: number): string {
  if (value == null) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return value.toFixed(precision);
  return value;
}
