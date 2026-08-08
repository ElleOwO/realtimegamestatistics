"use client";

import { useState } from "react";
import type { AnalyticsPayload, LiveCommand, ShapeMetrics, TacticalTargets } from "../../hooks/useAnalytics";
import { EmptyState, LiveBadge, Panel } from "./Panel";

type ShapePhase = "in_possession" | "out_of_possession";
const METRICS: Array<[keyof ShapeMetrics, string, string]> = [
  ["defensive_line_height_m", "Defensive line", "m"],
  ["team_length_m", "Team length", "m"],
  ["width_m", "Team width", "m"],
  ["line_gap_1_m", "Def–mid gap", "m"],
  ["line_gap_2_m", "Mid–fwd gap", "m"],
  ["compactness_m", "Compactness", "m"],
  ["goalkeeper_line_gap_m", "GK–line gap", "m"],
  ["convex_hull_area_m2", "Hull area", "m²"],
  ["players_behind_ball", "Behind ball", ""],
];

export function TeamShapePanel({ data, teamNames, sendCommand }: {
  data: AnalyticsPayload | null;
  teamNames: [string, string];
  sendCommand: (command: LiveCommand) => boolean;
}) {
  const [team, setTeam] = useState<0 | 1>(0);
  const [phase, setPhase] = useState<ShapePhase>("out_of_possession");
  const [editing, setEditing] = useState(false);
  if (!data) return <Panel title="Team Shape"><EmptyState /></Panel>;
  const shape = data.shape.teams[team][phase];
  const teamCode = team === 0 ? "team0" : "team1";
  const targets = data.match.tactical_targets?.[teamCode]?.[phase] ?? {};

  return <Panel title="Team Shape" badge={<LiveBadge />}>
    <div className="mb-2 flex flex-wrap gap-1">
      {([0, 1] as const).map((value) => <button key={value} onClick={() => setTeam(value)} className={`rounded px-2 py-1 text-[9px] font-black uppercase ${team === value ? "bg-primary/15 text-primary" : "bg-zinc-900 text-muted-foreground"}`}>{teamNames[value]}</button>)}
      {(["in_possession", "out_of_possession"] as const).map((value) => <button key={value} onClick={() => setPhase(value)} className={`rounded px-2 py-1 text-[9px] font-black uppercase ${phase === value ? "bg-secondary/15 text-secondary" : "bg-zinc-900 text-muted-foreground"}`}>{value === "in_possession" ? "In poss." : "Out poss."}</button>)}
      <button onClick={() => setEditing(!editing)} className="ml-auto text-[9px] font-black uppercase text-muted-foreground">Targets</button>
    </div>
    {editing ? <TargetEditor allTargets={data.match.tactical_targets} teamCode={teamCode} phase={phase} sendCommand={sendCommand} close={() => setEditing(false)} /> : shape ? (
      <dl className="space-y-1.5 stat-numerals">
        {METRICS.map(([key, label, unit]) => shape[key] == null ? null : <ShapeRow key={key} label={label} value={Number(shape[key])} unit={unit} target={targets[key as string]} />)}
        <div className="flex items-baseline justify-between"><dt className="text-[9px] font-black uppercase tracking-wider text-muted-foreground">Centroid</dt><dd className="text-xs font-black">{shape.centroid_x_m.toFixed(1)}, {shape.centroid_y_m.toFixed(1)}</dd></div>
      </dl>
    ) : <EmptyState hint="Needs ≥ 7 outfield players and a quality-gated projection" />}
    <p className="mt-3 text-[9px] text-muted-foreground">Rolling 10-second median · targets are staff-defined, never generic.</p>
  </Panel>;
}

function ShapeRow({ label, value, unit, target }: { label: string; value: number; unit: string; target?: { min?: number; max?: number } }) {
  const state = target ? (target.min != null && value < target.min ? "below" : target.max != null && value > target.max ? "above" : "target") : null;
  return <div className="flex items-baseline justify-between gap-2"><dt className="text-[9px] font-black uppercase tracking-wider text-muted-foreground">{label}</dt><dd className="text-xs font-black">{value.toFixed(1)} {unit}{state && <span className={`ml-1 text-[8px] uppercase ${state === "target" ? "text-primary" : "text-amber-300"}`}>{state}</span>}</dd></div>;
}

function TargetEditor({ allTargets, teamCode, phase, sendCommand, close }: { allTargets: TacticalTargets; teamCode: string; phase: ShapePhase; sendCommand: (command: LiveCommand) => boolean; close: () => void }) {
  const initial = allTargets?.[teamCode]?.[phase] ?? {};
  const [draft, setDraft] = useState<Record<string, { min?: number; max?: number }>>(() => structuredClone(initial));
  const set = (key: string, side: "min" | "max", raw: string) => setDraft((current) => ({ ...current, [key]: { ...current[key], [side]: raw === "" ? undefined : Number(raw) } }));
  const save = () => {
    const next = structuredClone(allTargets);
    next[teamCode] ??= {};
    next[teamCode][phase] = draft;
    sendCommand({ type: "match.set_targets", payload: { tactical_targets: next } });
    close();
  };
  return <div className="max-h-64 space-y-1 overflow-y-auto text-[9px]">
    {METRICS.map(([key, label]) => <label key={key} className="grid grid-cols-[1fr_3rem_3rem] items-center gap-1"><span className="font-bold text-muted-foreground">{label}</span><input aria-label={`${label} minimum`} type="number" placeholder="min" value={draft[key]?.min ?? ""} onChange={(event) => set(String(key), "min", event.target.value)} className="w-full rounded border border-zinc-800 bg-background px-1 py-1" /><input aria-label={`${label} maximum`} type="number" placeholder="max" value={draft[key]?.max ?? ""} onChange={(event) => set(String(key), "max", event.target.value)} className="w-full rounded border border-zinc-800 bg-background px-1 py-1" /></label>)}
    <div className="flex justify-end gap-1 pt-2"><button onClick={close} className="rounded px-2 py-1 text-muted-foreground">Cancel</button><button onClick={save} className="rounded bg-primary px-2 py-1 font-black text-primary-foreground">Save</button></div>
  </div>;
}
