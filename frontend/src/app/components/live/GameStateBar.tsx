"use client";

import { Clock3, Minus, Pencil, Plus } from "lucide-react";
import type { AnalyticsPayload, LiveCommand, MatchPhase } from "../../hooks/useAnalytics";
import { useNow } from "../../hooks/useDerivedMetrics";
import { formatClock } from "../../lib/deriveMatchMetrics";

const PHASES: Array<[MatchPhase, string]> = [
  ["pregame", "Pre"], ["first_half", "1H"], ["halftime", "HT"],
  ["second_half", "2H"], ["full_time", "FT"],
];

export function GameStateBar({
  data, sendCommand,
}: {
  data: AnalyticsPayload | null;
  sendCommand: (command: LiveCommand) => boolean;
}) {
  const now = useNow(1000);
  const state = data?.match;
  const elapsedSincePayload = data && state?.clock_running
    ? Math.max(0, now - data.frame.emitted_at_ms) / 1000 : 0;
  const clockS = state ? state.clock_s + elapsedSincePayload : null;

  const setScore = (team: 0 | 1, delta: number) => {
    if (!state) return;
    const score: [number, number] = [...state.score];
    score[team] = Math.max(0, score[team] + delta);
    sendCommand({ type: "match.set_score", payload: { score } });
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
    <section aria-label="Match score and controls" className="match-grid relative overflow-hidden rounded-xl border border-white/10 bg-card shadow-[0_24px_70px_rgba(0,0,0,.22)]">
      <div className="absolute inset-x-0 top-0 h-1 bg-[linear-gradient(90deg,var(--primary)_0_50%,var(--secondary)_50%)]" />
      <div className="grid min-h-40 grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-stretch sm:min-h-48">
        <TeamBlock
          name={state?.team_names[0] ?? "USask"}
          team={0}
          score={state?.score[0] ?? 0}
          accent="primary"
          editNames={editNames}
          setScore={setScore}
        />

        <div className="relative flex min-w-28 flex-col items-center justify-center border-x border-white/10 bg-background/50 px-3 text-center sm:min-w-48 sm:px-8">
          <p className="eyebrow mb-2 text-muted-foreground">Match clock</p>
          <button onClick={alignClock} title="Align match clock" className="group flex items-center gap-2 font-mono text-2xl font-semibold tabular-nums text-white sm:text-4xl">
            <Clock3 className="hidden h-4 w-4 text-primary transition group-hover:text-secondary sm:block" />
            {clockS != null ? formatClock(clockS) : "--:--"}
          </button>
          <span className="mt-3 rounded-sm border border-white/10 bg-white/[0.04] px-2 py-1 font-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            {state?.phase ? phaseLabel(state.phase) : "No period"}
          </span>
        </div>

        <TeamBlock
          name={state?.team_names[1] ?? "Opponent"}
          team={1}
          score={state?.score[1] ?? 0}
          accent="secondary"
          editNames={editNames}
          setScore={setScore}
          align="right"
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 bg-background/35 px-3 py-2.5 sm:px-4">
        <p className="hidden font-mono text-[9px] uppercase tracking-[0.16em] text-muted-foreground sm:block">Operator controls</p>
        <div aria-label="Match phase" className="flex flex-1 justify-center sm:flex-none">
          {PHASES.map(([phase, label]) => (
            <button key={phase} onClick={() => sendCommand({ type: "match.set_phase", payload: { phase } })}
              className={`min-w-9 border-y border-l px-2 py-1.5 font-mono text-[9px] font-semibold uppercase transition first:rounded-l-sm last:rounded-r-sm last:border-r sm:min-w-11 ${state?.phase === phase ? "border-primary bg-primary text-primary-foreground" : "border-white/10 bg-white/[0.025] text-muted-foreground hover:bg-white/[0.06] hover:text-white"}`}>{label}</button>
          ))}
        </div>
        <p className="hidden font-mono text-[9px] uppercase tracking-[0.16em] text-muted-foreground sm:block">Score · names · clock</p>
      </div>
    </section>
  );
}

function TeamBlock({ name, team, score, accent, editNames, setScore, align = "left" }: {
  name: string;
  team: 0 | 1;
  score: number;
  accent: "primary" | "secondary";
  editNames: () => void;
  setScore: (team: 0 | 1, delta: number) => void;
  align?: "left" | "right";
}) {
  const color = accent === "primary" ? "text-primary" : "text-secondary";
  return <div className={`relative flex min-w-0 flex-col justify-between p-3 sm:p-6 ${align === "right" ? "items-end text-right" : "items-start"}`}>
    <button onClick={editNames} title="Edit team names" className={`group flex max-w-full items-center gap-2 ${color}`}>
      <span className="truncate font-display text-lg font-semibold uppercase tracking-[0.05em] sm:text-2xl">{name}</span>
      <Pencil className="h-3 w-3 shrink-0 opacity-35 transition group-hover:opacity-100" />
    </button>
    <p className="font-display text-7xl font-semibold leading-none tracking-[-0.04em] text-white tabular-nums sm:text-9xl">{score}</p>
    <div className="flex gap-1.5">
      <ScoreButton icon={Minus} label={`Subtract a goal from ${name}`} onClick={() => setScore(team, -1)} />
      <ScoreButton icon={Plus} label={`Add a goal to ${name}`} onClick={() => setScore(team, 1)} />
    </div>
  </div>;
}

function ScoreButton({ icon: Icon, label, onClick }: { icon: typeof Plus; label: string; onClick: () => void }) {
  return <button aria-label={label} title={label} onClick={onClick} className="flex h-7 w-7 items-center justify-center rounded-sm border border-white/10 bg-background/30 text-muted-foreground transition hover:border-white/25 hover:text-white"><Icon className="h-3 w-3" /></button>;
}

function phaseLabel(phase: MatchPhase) {
  return ({ pregame: "Pre-match", first_half: "First half", halftime: "Half-time", second_half: "Second half", full_time: "Full-time" } as const)[phase];
}
