"use client";

import { Clock3, Radio } from "lucide-react";
import { useSocket } from "./components/SocketProvider";
import type { TeamProgressionStats } from "./hooks/useAnalytics";
import { useNow } from "./hooks/useDerivedMetrics";
import { formatClock } from "./lib/deriveMatchMetrics";

const AREAS = [
  { key: "wideLeft", short: "Wide L", label: "Wide left" },
  { key: "halfLeft", short: "Half L", label: "Left half-space" },
  { key: "central", short: "Central", label: "Central" },
  { key: "halfRight", short: "Half R", label: "Right half-space" },
  { key: "wideRight", short: "Wide R", label: "Wide right" },
] as const;

interface EntryAreas {
  wideLeft: number;
  halfLeft: number;
  central: number;
  halfRight: number;
  wideRight: number;
}

interface LiveTeam {
  name: string;
  score: number;
  xg: number;
  totalEntries: number;
  boxEntries: number;
  entries: EntryAreas;
}

export default function LiveFootageAnalytics() {
  const { data, isConnected } = useSocket();
  const now = useNow(1000);
  const elapsed = data?.match.clock_running ? Math.max(0, now - data.frame.emitted_at_ms) / 1000 : 0;
  const clock = data ? formatClock(data.match.clock_s + elapsed) : "--:--";
  const team0 = toLiveTeam(data?.match.team_names[0] ?? "Team 1", data?.match.score[0] ?? 0, data?.chance_quality.teams[0].xg ?? 0, data?.progression.teams[0]);
  const team1 = toLiveTeam(data?.match.team_names[1] ?? "Team 2", data?.match.score[1] ?? 0, data?.chance_quality.teams[1].xg ?? 0, data?.progression.teams[1]);
  const totalXg = team0.xg + team1.xg;
  const share0 = totalXg > 0 ? team0.xg / totalXg : 0.5;

  return (
    <div className="mx-auto flex h-dvh w-full max-w-7xl flex-col overflow-hidden px-5 py-4 sm:px-7 sm:py-5 lg:px-10 lg:py-6">
      <header className="shrink-0 border-b border-white/10 pb-4 lg:pb-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="mb-1.5 text-[10px] font-black uppercase tracking-[0.32em] text-primary">Live footage analytics</p>
            <h1 className="text-xl font-black tracking-tight text-white sm:text-2xl">Match overview</h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-2 rounded-full border border-white/10 bg-card px-3 py-1.5 text-xs font-black tabular-nums text-white">
              <Clock3 className="h-3.5 w-3.5 text-zinc-500" />{clock}
            </span>
            <span className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-[9px] font-black uppercase tracking-widest ${isConnected ? "border-primary/30 bg-primary/10 text-primary" : process.env.NEXT_PUBLIC_DEMO_MODE === "true" ? "border-secondary/30 bg-secondary/10 text-secondary" : "border-white/10 bg-card text-zinc-500"}`}>
              <Radio className="h-3 w-3" />{isConnected ? "Live" : process.env.NEXT_PUBLIC_DEMO_MODE === "true" ? "Demo" : "Waiting"}
            </span>
          </div>
        </div>
      </header>

      <main className="grid min-h-0 flex-1 grid-rows-[auto_minmax(0,1fr)] gap-3 py-3 lg:gap-4 lg:py-4">
        <section className="shrink-0 overflow-hidden rounded-2xl border border-white/10 bg-card">
          <div className="grid grid-cols-[1fr_auto_1fr] items-center px-5 py-4 sm:px-8 sm:py-5">
            <ScoreTeam team={team0} side="left" />
            <div className="px-4 text-center sm:px-10">
              <p className="text-[9px] font-black uppercase tracking-[0.24em] text-zinc-600">Score</p>
              <p className="mt-1 text-4xl font-black tracking-tight text-white tabular-nums sm:text-5xl">{team0.score}<span className="mx-2 text-zinc-700">–</span>{team1.score}</p>
            </div>
            <ScoreTeam team={team1} side="right" />
          </div>
          <div className="border-t border-white/10 px-5 py-3 sm:px-8">
            <div className="mb-2 flex items-end justify-between">
              <XgValue team={team0.name} value={team0.xg} color="primary" />
              <p className="text-[9px] font-black uppercase tracking-[0.2em] text-zinc-600">Expected goals</p>
              <XgValue team={team1.name} value={team1.xg} color="secondary" />
            </div>
            <div className="flex h-2.5 overflow-hidden rounded-full bg-zinc-800">
              <div className="bg-primary transition-all duration-500" style={{ width: `${share0 * 100}%` }} />
              <div className="flex-1 bg-secondary" />
            </div>
          </div>
        </section>

        <section className="flex min-h-0 flex-col rounded-2xl border border-white/10 bg-card">
          <div className="flex shrink-0 items-end justify-between border-b border-white/10 px-5 py-3 sm:px-6">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.22em] text-zinc-500">Possession-based</p>
              <h2 className="mt-1 text-lg font-black text-white">Final-third entries by key area</h2>
            </div>
            <p className="hidden text-xs text-zinc-500 sm:block">Left and right follow the pitch y-axis</p>
          </div>
          <div className="grid min-h-0 flex-1 gap-3 p-3 md:grid-cols-2 lg:p-4">
            <EntryCard team={team0} color="primary" />
            <EntryCard team={team1} color="secondary" />
          </div>
        </section>
      </main>
    </div>
  );
}

function toLiveTeam(name: string, score: number, xg: number, progression?: TeamProgressionStats): LiveTeam {
  const detailed = progression?.key_area_entries;
  return {
    name,
    score,
    xg,
    totalEntries: progression?.final_third_entries ?? 0,
    boxEntries: progression?.penalty_area_entries ?? 0,
    entries: detailed ? {
      wideLeft: detailed.wide_left,
      halfLeft: detailed.half_space_left,
      central: detailed.central,
      halfRight: detailed.half_space_right,
      wideRight: detailed.wide_right,
    } : {
      wideLeft: progression?.entry_channels.left ?? 0,
      halfLeft: 0,
      central: progression?.entry_channels.centre ?? 0,
      halfRight: 0,
      wideRight: progression?.entry_channels.right ?? 0,
    },
  };
}

function ScoreTeam({ team, side }: { team: LiveTeam; side: "left" | "right" }) {
  return <div className={side === "right" ? "text-right" : ""}>
    <p className={`truncate text-xs font-black uppercase tracking-[0.18em] sm:text-sm ${side === "left" ? "text-primary" : "text-secondary"}`}>{team.name}</p>
  </div>;
}

function XgValue({ team, value, color }: { team: string; value: number; color: "primary" | "secondary" }) {
  return <div className={color === "secondary" ? "text-right" : ""}>
    <p className={`text-2xl font-black leading-none tabular-nums sm:text-3xl ${color === "primary" ? "text-primary" : "text-secondary"}`}>{value.toFixed(2)}</p>
    <p className="mt-1 max-w-24 truncate text-[8px] font-bold uppercase tracking-wider text-zinc-600">{team} xG</p>
  </div>;
}

function EntryCard({ team, color }: { team: LiveTeam; color: "primary" | "secondary" }) {
  const accent = color === "primary" ? "text-primary" : "text-secondary";
  const surface = color === "primary" ? "bg-primary/10 border-primary/20" : "bg-secondary/10 border-secondary/20";
  return (
    <article className="flex min-h-0 flex-col justify-center rounded-xl border border-white/10 bg-zinc-950/35 p-3 sm:p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className={`text-sm font-black uppercase tracking-[0.18em] ${accent}`}>{team.name}</h3>
        <div className="text-right"><p className="text-2xl font-black leading-none text-white tabular-nums">{team.totalEntries}</p><p className="mt-1 text-[9px] font-black uppercase tracking-widest text-zinc-500">Total entries</p></div>
      </div>
      <div className={`mb-2 flex items-center justify-between rounded-xl border px-3 py-2 ${surface}`}>
        <div><p className="text-[10px] font-black uppercase tracking-[0.18em] text-zinc-400">Penalty box</p><p className="mt-0.5 text-xs text-zinc-600">Highest-value entry zone</p></div>
        <span className={`text-2xl font-black tabular-nums ${accent}`}>{team.boxEntries}</span>
      </div>
      <div className="grid grid-cols-5 gap-1.5">
        {AREAS.map((area) => <div key={area.key} title={area.label} className="rounded-lg border border-white/10 bg-zinc-900/70 px-1 py-2 text-center"><p className="text-lg font-black text-white tabular-nums">{team.entries[area.key]}</p><p className="mt-1 truncate text-[8px] font-black uppercase tracking-wide text-zinc-500">{area.short}</p></div>)}
      </div>
    </article>
  );
}
