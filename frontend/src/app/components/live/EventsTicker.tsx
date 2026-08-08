"use client";

import type { AnalyticsPayload } from "../../hooks/useAnalytics";
import { EmptyState, Panel } from "./Panel";

export function EventsTicker({ data, teamNames }: { data: AnalyticsPayload | null; teamNames: [string, string] }) {
  const events = (data?.events ?? []).slice(-12).reverse();
  return <Panel title="Key Events" className="h-full flex flex-col" bodyClassName="flex-1 min-h-0">
    {!events.length ? <EmptyState hint="Quality-gated shots, entries, turnovers, and pressure events appear here" /> : <div className="flex h-full min-h-36 flex-col gap-1.5 overflow-y-auto pr-1">
      {events.map((event, index) => {
        const team = event.team === "team0" ? 0 : event.team === "team1" ? 1 : null;
        const type = String(event.type ?? "event").replaceAll("_", " ");
        const minute = typeof event.match_clock_s === "number" ? Math.floor(event.match_clock_s / 60) : typeof event.timestamp_ms === "number" ? Math.floor(event.timestamp_ms / 60_000) : null;
        return <div key={String(event.id ?? index)} className="flex items-center gap-2 rounded-lg border border-zinc-800/60 bg-zinc-900/40 px-3 py-2">
          <span className="w-8 text-xs font-black text-muted-foreground">{minute == null ? "—" : `${minute}'`}</span>
          {team != null && <span className={`h-2 w-2 rounded-full ${team === 0 ? "bg-primary" : "bg-secondary"}`} title={teamNames[team]} />}
          <span className="min-w-0 flex-1 truncate text-xs font-bold capitalize">{type}</span>
          {typeof event.xg === "number" && <span className="rounded bg-zinc-800 px-1.5 py-.5 text-[10px] font-black">xG {event.xg.toFixed(2)}</span>}
          {event.status === "candidate" && <span className="text-[8px] font-black uppercase text-amber-300">pending</span>}
        </div>;
      })}
    </div>}
  </Panel>;
}
