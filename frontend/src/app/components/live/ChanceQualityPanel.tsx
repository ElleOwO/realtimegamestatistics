"use client";

import type { AnalyticsPayload, LiveCommand, ShotEvent } from "../../hooks/useAnalytics";
import { EmptyState, LiveBadge, Panel } from "./Panel";
import { StatCompareBar } from "./StatCompareBar";

export function ChanceQualityPanel({ data, teamNames, sendCommand }: {
  data: AnalyticsPayload | null;
  teamNames: [string, string];
  sendCommand: (command: LiveCommand) => boolean;
}) {
  if (!data) return <Panel title="Chance Quality"><EmptyState /></Panel>;
  const [first, second] = data.chance_quality.teams;
  if (first.status === "unavailable" && second.status === "unavailable") return <Panel title="Chance Quality"><EmptyState hint="Waiting for a quality-gated ball projection" /></Panel>;
  const pending = data.chance_quality.shots.filter((shot) => shot.status === "candidate");
  const review = (shot: ShotEvent, patch: Record<string, unknown>) => sendCommand({ type: "event.review", payload: { event_id: shot.id, ...patch } });

  return (
    <Panel title="Chance Quality" badge={<LiveBadge />}>
      <Header names={teamNames} />
      <div className="space-y-2.5">
        <StatCompareBar label="Goals" value0={data.match.score[0]} value1={data.match.score[1]} />
        <StatCompareBar label="Shots" value0={first.shots} value1={second.shots} />
        <StatCompareBar label="On target" value0={`${first.shots_on_target}/${first.reviewed_on_target}`} value1={`${second.shots_on_target}/${second.reviewed_on_target}`} />
        <StatCompareBar label="xG" value0={first.xg.toFixed(2)} value1={second.xg.toFixed(2)} />
        <StatCompareBar label="Box shots" value0={first.box_shots} value1={second.box_shots} />
        <StatCompareBar label="Open play" value0={`${first.open_play_shots} · ${first.open_play_xg.toFixed(2)}`} value1={`${second.open_play_shots} · ${second.open_play_xg.toFixed(2)}`} />
        <StatCompareBar label="Set pieces" value0={`${first.set_piece_shots} · ${first.set_piece_xg.toFixed(2)}`} value1={`${second.set_piece_shots} · ${second.set_piece_xg.toFixed(2)}`} />
      </div>
      <ShotMap shots={data.chance_quality.shots} />
      {pending.slice(-1).map((shot) => (
        <div key={shot.id} className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2 text-[9px]">
          <div className="flex justify-between"><b>Review shot · {teamNames[shot.team === "team0" ? 0 : 1]}</b><span>xG {shot.xg.toFixed(2)}</span></div>
          <div className="mt-1.5 flex flex-wrap gap-1">
            <Action label="Confirm" onClick={() => review(shot, { status: "confirmed" })} />
            <Action label="On target" onClick={() => review(shot, { status: "corrected", on_target: true })} />
            <Action label="Goal" onClick={() => review(shot, { status: "corrected", on_target: true, outcome: "goal" })} />
            <Action label="Set piece" onClick={() => review(shot, { status: "corrected", play_context: "set_piece" })} />
            <Action label="Open play" onClick={() => review(shot, { status: "corrected", play_context: "open_play" })} />
            <Action label="Reject" onClick={() => review(shot, { status: "rejected" })} />
          </div>
        </div>
      ))}
      {pending.length > 0 && <p className="mt-2 text-[9px] text-amber-300">{pending.length} provisional shot{pending.length === 1 ? "" : "s"} awaiting review</p>}
    </Panel>
  );
}

function Header({ names }: { names: [string, string] }) {
  return <div className="mb-2 flex justify-between text-[9px] font-black uppercase tracking-[0.18em]"><span className="text-primary">{names[0]}</span><span className="text-secondary">{names[1]}</span></div>;
}

function ShotMap({ shots }: { shots: ShotEvent[] }) {
  return <svg viewBox="0 0 105 68" className="mt-3 w-full rounded-md bg-[#0a3523]" aria-label="Live shot map">
    <rect x=".5" y=".5" width="104" height="67" fill="none" stroke="#ffffff55" />
    <line x1="52.5" x2="52.5" y1="0" y2="68" stroke="#ffffff55" />
    {shots.map((shot) => <circle key={shot.id} cx={shot.location[0]} cy={shot.location[1]} r={1.2 + shot.xg * 3.5} fill={shot.team === "team0" ? "#23a469" : "#DBCC52"} opacity={shot.status === "candidate" ? .55 : .9} stroke={shot.status === "candidate" ? "white" : "none"} strokeDasharray="1 1" />)}
  </svg>;
}

function Action({ label, onClick }: { label: string; onClick: () => void }) {
  return <button onClick={onClick} className="rounded bg-zinc-800 px-1.5 py-1 font-black uppercase text-muted-foreground hover:text-white">{label}</button>;
}
