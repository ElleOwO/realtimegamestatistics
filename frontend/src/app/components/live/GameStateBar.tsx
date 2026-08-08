"use client";

import { ArrowLeft, ArrowRight, Minus, Plus, RotateCcw } from "lucide-react";
import type { AnalyticsPayload, LiveCommand, MatchPhase } from "../../hooks/useAnalytics";
import { useNow } from "../../hooks/useDerivedMetrics";
import { formatClock } from "../../lib/deriveMatchMetrics";
import { SystemHealthChip } from "./SystemHealthChip";

const PHASES: Array<[MatchPhase, string]> = [
  ["pregame", "Pre"], ["first_half", "1H"], ["halftime", "HT"],
  ["second_half", "2H"], ["full_time", "FT"],
];

export function GameStateBar({
  data, isConnected, fps, sendCommand,
}: {
  data: AnalyticsPayload | null;
  isConnected: boolean;
  fps: number | null;
  sendCommand: (command: LiveCommand) => boolean;
}) {
  const now = useNow(1000);
  const state = data?.match;
  const elapsedSincePayload = data && state?.clock_running
    ? Math.max(0, now - data.frame.emitted_at_ms) / 1000 : 0;
  const clockS = state ? state.clock_s + elapsedSincePayload : null;
  const activeHalf = state?.phase === "second_half" ? "second_half" : "first_half";
  const direction = state?.directions[activeHalf][0] ?? "right";
  const DirectionIcon = direction === "right" ? ArrowRight : ArrowLeft;

  const setScore = (team: 0 | 1, delta: number) => {
    if (!state) return;
    const score: [number, number] = [...state.score];
    score[team] = Math.max(0, score[team] + delta);
    sendCommand({ type: "match.set_score", payload: { score } });
  };

  const flipDirection = () => {
    if (!state) return;
    const first = state.directions.first_half[0] === "right" ? ["left", "right"] : ["right", "left"];
    const second = [first[1], first[0]];
    sendCommand({ type: "match.configure", payload: { directions: { first_half: first, second_half: second } } });
  };

  const editNames = () => {
    if (!state) return;
    const home = window.prompt("Team 0 name", state.team_names[0]);
    if (home == null) return;
    const away = window.prompt("Team 1 name", state.team_names[1]);
    if (away == null) return;
    sendCommand({ type: "match.configure", payload: { team_names: [home, away] } });
  };

  const alignClock = () => {
    const current = clockS == null ? "0:00" : formatClock(clockS);
    const value = window.prompt("Set match clock (MM:SS)", current);
    if (!value) return;
    const [minutes, seconds = "0"] = value.split(":");
    const total = Number(minutes) * 60 + Number(seconds);
    if (Number.isFinite(total) && total >= 0) sendCommand({ type: "match.set_clock", payload: { clock_s: total } });
  };

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-zinc-800 bg-card px-4 py-2.5">
      <div className="flex items-center gap-2 stat-numerals">
        <div className="flex gap-1"><ScoreButton icon={Minus} onClick={() => setScore(0, -1)} /><ScoreButton icon={Plus} onClick={() => setScore(0, 1)} /></div>
        <button onClick={editNames} title="Edit team names" className="max-w-20 truncate text-xs font-black uppercase tracking-widest text-primary">{state?.team_names[0] ?? "USask"}</button>
        <span className="rounded-lg bg-zinc-900 px-2.5 py-1 text-lg font-black">{state?.score[0] ?? 0}<span className="mx-1.5 text-muted-foreground">–</span>{state?.score[1] ?? 0}</span>
        <button onClick={editNames} title="Edit team names" className="max-w-20 truncate text-xs font-black uppercase tracking-widest text-secondary">{state?.team_names[1] ?? "Opponent"}</button>
        <div className="flex gap-1"><ScoreButton icon={Minus} onClick={() => setScore(1, -1)} /><ScoreButton icon={Plus} onClick={() => setScore(1, 1)} /></div>
      </div>

      <div className="hidden h-6 w-px bg-zinc-800 sm:block" />
      <button onClick={alignClock} title="Align match clock" className="text-lg font-black stat-numerals">{clockS != null ? formatClock(clockS) : "--:--"}</button>
      <div className="flex overflow-hidden rounded-lg border border-zinc-800">
        {PHASES.map(([phase, label]) => (
          <button key={phase} onClick={() => sendCommand({ type: "match.set_phase", payload: { phase } })}
            className={`px-2 py-1 text-[9px] font-black uppercase ${state?.phase === phase ? "bg-primary/15 text-primary" : "text-muted-foreground"}`}>{label}</button>
        ))}
      </div>

      <button onClick={flipDirection} className="flex items-center gap-1.5 rounded-lg border border-zinc-800 px-2.5 py-1.5 text-[10px] font-black uppercase tracking-widest text-muted-foreground">
        <DirectionIcon className="h-3.5 w-3.5 text-primary" /> {state?.team_names[0] ?? "USask"} attacks
      </button>

      <div className="ml-auto flex items-center gap-2">
        <button onClick={() => sendCommand({ type: "match.reset" })} className="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-800 text-muted-foreground" title="Reset match"><RotateCcw className="h-3.5 w-3.5" /></button>
        <SystemHealthChip data={data} isConnected={isConnected} fps={fps} />
      </div>
    </div>
  );
}

function ScoreButton({ icon: Icon, onClick }: { icon: typeof Plus; onClick: () => void }) {
  return <button onClick={onClick} className="flex h-7 w-7 items-center justify-center rounded-lg border border-zinc-800 text-muted-foreground"><Icon className="h-3 w-3" /></button>;
}
