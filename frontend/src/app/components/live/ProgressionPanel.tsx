"use client";

import type { AnalyticsPayload, TeamProgressionStats } from "../../hooks/useAnalytics";
import { EmptyState, LiveBadge, Panel } from "./Panel";
import { StatCompareBar } from "./StatCompareBar";

export function ProgressionPanel({ data, teamNames }: { data: AnalyticsPayload | null; teamNames: [string, string] }) {
  if (!data) return <Panel title="Zonal Entries"><EmptyState /></Panel>;
  const [first, second] = data.progression.teams;
  if (first.status === "unavailable" && second.status === "unavailable") return <Panel title="Zonal Entries"><EmptyState hint="Waiting for controlled possession and a valid projection" /></Panel>;
  return <Panel title="Zonal Entries" badge={<LiveBadge />}>
    <div className="mb-2 flex justify-between text-[9px] font-black uppercase tracking-[0.18em]"><span className="text-primary">{teamNames[0]}</span><span className="text-secondary">{teamNames[1]}</span></div>
    <div className="space-y-3">
      <StatCompareBar label="Final-3rd entries" value0={first.final_third_entries} value1={second.final_third_entries} />
      <StatCompareBar label="Box entries" value0={first.penalty_area_entries} value1={second.penalty_area_entries} />
      <StatCompareBar label="Behind line" value0={first.behind_line_entries} value1={second.behind_line_entries} />
      <ChannelBar name={teamNames[0]} stats={first} color="text-primary" />
      <ChannelBar name={teamNames[1]} stats={second} color="text-secondary" />
    </div>
    <p className="mt-3 text-[9px] text-muted-foreground">Entries count controlled-ball crossings into each attacking zone.</p>
  </Panel>;
}

function ChannelBar({ name, stats, color }: { name: string; stats: TeamProgressionStats; color: string }) {
  const { left, centre, right } = stats.entry_channels;
  const total = left + centre + right;
  const pct = (value: number) => total ? Math.round(value / total * 100) : 0;
  return <div>
    <div className="flex justify-between text-[9px]"><span className={`font-black uppercase ${color}`}>{name}</span><span className="text-muted-foreground">L {pct(left)}% · C {pct(centre)}% · R {pct(right)}%</span></div>
    <div className="mt-1 flex h-1.5 overflow-hidden rounded bg-zinc-800"><span className="bg-primary/70" style={{ width: `${pct(left)}%` }} /><span className="bg-zinc-400/70" style={{ width: `${pct(centre)}%` }} /><span className="bg-secondary/70" style={{ width: `${pct(right)}%` }} /></div>
  </div>;
}
