import type { AnalyticsPayload } from "../../hooks/useAnalytics";
import { EmptyState, LiveBadge, Panel } from "./Panel";
import { StatCompareBar } from "./StatCompareBar";

export function TransitionsPanel({ data, teamNames }: { data: AnalyticsPayload | null; teamNames: [string, string] }) {
  if (!data) return <Panel title="Transitions & Press"><EmptyState /></Panel>;
  const [first, second] = data.transitions.teams;
  if (first.status === "unavailable" && second.status === "unavailable") return <Panel title="Transitions & Press"><EmptyState hint="Waiting for quality-gated possession changes" /></Panel>;
  const [press0, press1] = data.pressing.teams;
  return <Panel title="Transitions & Press" badge={<LiveBadge />}>
    <div className="mb-2 flex justify-between text-[9px] font-black uppercase tracking-[0.18em]"><span className="text-primary">{teamNames[0]}</span><span className="text-secondary">{teamNames[1]}</span></div>
    <div className="space-y-2.5">
      <StatCompareBar label="High regains" value0={first.high_regains} value1={second.high_regains} />
      <StatCompareBar label="Regains → shot" value0={first.shots_after_regain} value1={second.shots_after_regain} />
      <StatCompareBar label="Losses → opp. shot" value0={first.opponent_shots_after_loss} value1={second.opponent_shots_after_loss} />
      <StatCompareBar label="Dangerous losses" value0={first.dangerous_losses} value1={second.dangerous_losses} />
      <StatCompareBar label="Avg recovery" value0={first.average_recovery_s == null ? "—" : `${first.average_recovery_s.toFixed(1)}s`} value1={second.average_recovery_s == null ? "—" : `${second.average_recovery_s.toFixed(1)}s`} />
      <StatCompareBar label="Press success" value0={`${press0.successes}/${press0.attempts}`} value1={`${press1.successes}/${press1.attempts}`} />
      <StatCompareBar label="High-press attempts" value0={press0.high_press_attempts} value1={press1.high_press_attempts} />
      <StatCompareBar label="Forced backward" value0={press0.forced_backward} value1={press1.forced_backward} />
      <StatCompareBar label="Forced long*" value0={press0.forced_long_candidates} value1={press1.forced_long_candidates} />
      <StatCompareBar label="Central escapes" value0={press0.central_escapes} value1={press1.central_escapes} />
      <StatCompareBar label="Avg escape" value0={press0.average_escape_s == null ? "—" : `${press0.average_escape_s.toFixed(1)}s`} value1={press1.average_escape_s == null ? "—" : `${press1.average_escape_s.toFixed(1)}s`} />
      <StatCompareBar label="Opp. final-3rd allowed" value0={press0.opponent_final_third_entries_allowed} value1={press1.opponent_final_third_entries_allowed} />
    </div>
    <p className="mt-3 text-[9px] text-amber-300">Pressure episodes are experimental; possession changes are quality-gated.</p>
  </Panel>;
}
