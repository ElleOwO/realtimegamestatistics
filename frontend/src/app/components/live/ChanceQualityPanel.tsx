"use client";

import type { AnalyticsPayload } from "../../hooks/useAnalytics";
import { EmptyState, LiveBadge, Panel } from "./Panel";
import { StatCompareBar } from "./StatCompareBar";

export function ChanceQualityPanel({ data, teamNames }: {
  data: AnalyticsPayload | null;
  teamNames: [string, string];
}) {
  if (!data) return <Panel title="Chance Quality"><EmptyState /></Panel>;
  const [first, second] = data.chance_quality.teams;
  if (first.status === "unavailable" && second.status === "unavailable") return <Panel title="Chance Quality"><EmptyState hint="Waiting for a quality-gated ball projection" /></Panel>;
  return (
    <Panel title="Chance Quality" badge={<LiveBadge />}>
      <Header names={teamNames} />
      <div className="space-y-2.5">
        <StatCompareBar label="xG" value0={first.xg.toFixed(2)} value1={second.xg.toFixed(2)} />
        <StatCompareBar label="Open-play xG" value0={first.open_play_xg.toFixed(2)} value1={second.open_play_xg.toFixed(2)} />
        <StatCompareBar label="Set-piece xG" value0={first.set_piece_xg.toFixed(2)} value1={second.set_piece_xg.toFixed(2)} />
      </div>
      <p className="mt-3 text-[9px] text-muted-foreground">Cumulative expected goals from detected and reviewed chances.</p>
    </Panel>
  );
}

function Header({ names }: { names: [string, string] }) {
  return <div className="mb-2 flex justify-between text-[9px] font-black uppercase tracking-[0.18em]"><span className="text-primary">{names[0]}</span><span className="text-secondary">{names[1]}</span></div>;
}
