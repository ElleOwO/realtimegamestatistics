import type { AnalyticsPayload } from "../../hooks/useAnalytics";
import { EmptyState, LiveBadge, Panel } from "./Panel";
import { StatCompareBar } from "./StatCompareBar";

export function TransitionsPanel({ data, teamNames }: { data: AnalyticsPayload | null; teamNames: [string, string] }) {
  if (!data) return <Panel title="Transitions & Turnovers"><EmptyState /></Panel>;
  const [first, second] = data.transitions.teams;
  if (first.status === "unavailable" && second.status === "unavailable") return <Panel title="Transitions & Turnovers"><EmptyState hint="Waiting for quality-gated possession changes" /></Panel>;
  return <Panel title="Transitions & Turnovers" badge={<LiveBadge />}>
    <div className="mb-2 flex justify-between text-[9px] font-black uppercase tracking-[0.18em]"><span className="text-primary">{teamNames[0]}</span><span className="text-secondary">{teamNames[1]}</span></div>
    <div className="space-y-2.5">
      <StatCompareBar label="High regains" value0={first.high_regains} value1={second.high_regains} />
      <StatCompareBar label="Counterattacks" value0={first.counterattacks} value1={second.counterattacks} />
      <StatCompareBar label="Regains → shot" value0={first.shots_after_regain} value1={second.shots_after_regain} />
      <StatCompareBar label="Losses → opp. shot" value0={first.opponent_shots_after_loss} value1={second.opponent_shots_after_loss} />
      <StatCompareBar label="Dangerous losses" value0={first.dangerous_losses} value1={second.dangerous_losses} />
      <StatCompareBar label="Avg recovery" value0={first.average_recovery_s == null ? "—" : `${first.average_recovery_s.toFixed(1)}s`} value1={second.average_recovery_s == null ? "—" : `${second.average_recovery_s.toFixed(1)}s`} />
    </div>
    <p className="mt-3 text-[9px] text-muted-foreground">Possession changes are quality-gated to reduce false turnovers.</p>
  </Panel>;
}
