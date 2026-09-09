"use client";

import { useEffect, useState } from "react";
import type { AnalyticsPayload, LiveCommand } from "../../hooks/useAnalytics";
import { isSessionActive, sessionLabel, validExclusion, type LiveSession } from "../../lib/liveSession";

const inputClass = "rounded border border-white/20 bg-background px-3 py-2 text-sm text-foreground";
const buttonClass = "rounded border border-white/20 px-3 py-2 text-sm hover:bg-white/10 disabled:opacity-40";

export function SessionControls({ data, connected, sendCommand, onManaged, onSession }: {
  data: AnalyticsPayload | null;
  connected: boolean;
  sendCommand: (command: LiveCommand) => boolean;
  onManaged: (value: boolean) => void;
  onSession: (value: string | null) => void;
}) {
  const [managed, setManaged] = useState(false);
  const [session, setSession] = useState<LiveSession | null>(null);
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);
  const [cluster, setCluster] = useState("0");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    const poll = async () => {
      try {
        const result = await fetch("/api/live/sessions/current", { signal: controller.signal, cache: "no-store" });
        if (result.status === 404) return; // Legacy/replay deployment.
        if (!result.ok) throw new Error("Session service is unavailable.");
        const value = await result.json();
        if (!stopped && value.managed) {
          setManaged(true); onManaged(true); setSession(value.session); onSession(value.session?.id ?? null); setTick(Date.now());
        }
      } catch {
        if (!stopped) setError("Cannot reach the session service. Reload or check the connection.");
      }
      if (!stopped) timer = setTimeout(poll, 3000);
    };
    void poll();
    return () => { stopped = true; controller.abort(); clearTimeout(timer); };
  }, [onManaged, onSession]);

  const request = async (path: string, payload = {}) => {
    setBusy(true); setError(null);
    try {
      const result = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const value = await result.json();
      if (!result.ok) throw new Error(typeof value.detail === "string" ? value.detail : "Session request failed.");
      setSession(value);
      onSession(value.id ?? null);
    } catch (err) { setError(err instanceof Error ? err.message : "Session request failed."); }
    finally { setBusy(false); }
  };
  if (!managed) return null;
  const active = isSessionActive(session);
  const currentData = session && data?.runtime.run_id === session.id ? data : null;
  const canControl = !!currentData && connected && session?.state !== "stopping";
  const analyzing = currentData?.runtime.analysis_state === "analyzing";
  const playhead = (currentData?.frame.source_timestamp_ms ?? 0) / 1000;
  const minutesLeft = session ? Math.max(0, Math.ceil((session.deadline * 1000 - tick) / 60000)) : 0;
  const command = (value: LiveCommand) => sendCommand({ ...value, source_timestamp_ms: currentData?.frame.source_timestamp_ms });

  return <section className="space-y-4 rounded-xl border border-white/10 bg-card p-4 sm:p-6" aria-label="CanadaWest live session">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><p className="eyebrow text-primary">CanadaWest.TV</p><h2 className="mt-2 text-xl font-semibold">{session ? sessionLabel(session.state) : "Connect a live game"}</h2></div>
      {active && <span className={minutesLeft <= 15 ? "text-amber-300" : "text-muted-foreground"}>{minutesLeft} min remaining</span>}
    </div>
    {(error || session?.error) && <p role="alert" className="text-sm text-amber-200">{error || session?.error}</p>}
    {!active && <form className="flex flex-wrap gap-2" onSubmit={e => { e.preventDefault(); void request("/api/live/sessions", { event_url: url }); }}>
      <label className="min-w-56 flex-1"><span className="sr-only">CanadaWest game link</span><input required type="url" value={url} onChange={e => setUrl(e.target.value)} placeholder="Paste the CanadaWest.TV game link" className={`${inputClass} w-full`} /></label>
      <button disabled={busy} className={`${buttonClass} bg-primary text-primary-foreground`}>Start analysis session</button>
    </form>}
    {session && <div className="flex flex-wrap gap-2">
      {active && <><button disabled={busy} className={buttonClass} onClick={() => void request(`/api/live/sessions/${session.id}/extend`)}>Add one hour</button><button disabled={busy} className={buttonClass} onClick={() => void request(`/api/live/sessions/${session.id}/stop`)}>End session</button></>}
      {["interrupted", "failed"].includes(session.state) && <button disabled={busy} className={buttonClass} onClick={() => void request(`/api/live/sessions/${session.id}/resume`)}>Resume session</button>}
      {session.artifacts_ready && <a className={buttonClass} href={`/api/live/sessions/${session.id}/artifacts`}>Download checkpoint</a>}
    </div>}
    <p className="text-xs text-muted-foreground">Statistics follow the broadcast timeline. Broadcast delay is unknown; processing delay is shown separately. An analyst confirms teams, halves, and shots.</p>
    {active && session?.worker_started && <div className="grid gap-4 lg:grid-cols-2">
      <div>
        {/* One backend ingest supplies this preview; no additional provider login. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        {currentData?.runtime.preview_timestamp_ms != null ? <img src={`/api/live/preview?t=${tick}`} alt="Current broadcast with detected team colors 0 (blue) and 1 (pink)" className="aspect-video w-full rounded bg-black object-contain" /> : <div className="flex aspect-video items-center justify-center rounded bg-black text-sm text-muted-foreground">Waiting for the first preview…</div>}
        <p className="mt-2 text-xs text-muted-foreground">Analysis position: {playhead.toFixed(1)} s · Preview refreshes every 3 s · Processing: {currentData?.runtime.processing_latency_ms?.toFixed(0) ?? "—"} ms · Queue: {currentData?.runtime.queue_delay_ms?.toFixed(0) ?? "—"} ms</p>
      </div>
      <fieldset disabled={!canControl} className="space-y-3 disabled:opacity-50">
        <legend className="mb-2 text-sm font-semibold">Match setup and broadcast controls</legend>
        <div className="flex flex-wrap gap-2">
          <label className="text-sm">USask kit <select aria-label="USask team color" className={`${inputClass} ml-2`} value={cluster} onChange={e => setCluster(e.target.value)}><option value="0">0 — Blue boxes</option><option value="1">1 — Pink boxes</option></select></label>
          <button className={buttonClass} disabled={analyzing} onClick={() => command({ type: "analysis.confirm_teams", payload: { usask_cluster: Number(cluster) } })}>Confirm teams</button>
        </div>
        <label className="block text-sm">USask attacks in first half <select className={`${inputClass} ml-2`} defaultValue="right" onChange={e => command({ type: "match.configure", payload: { directions: e.target.value === "right" ? { first_half: ["right", "left"], second_half: ["left", "right"] } : { first_half: ["left", "right"], second_half: ["right", "left"] } } })}><option value="right">Right</option><option value="left">Left</option></select></label>
        <button disabled={!currentData?.runtime.teams_confirmed} className={`${buttonClass} bg-primary text-primary-foreground`} onClick={() => command({ type: "analysis.set_enabled", payload: { enabled: !analyzing } })}>{analyzing ? "Pause accumulation" : "Enable accumulation"}</button>
        <p className="text-xs text-muted-foreground">Select 1H or 2H below to accumulate. Pause for replays and cutaways. Exclude a missed replay using its video positions.</p>
        <div className="flex flex-wrap gap-2">
          <input aria-label="Exclude from video second" type="number" min="0" placeholder="From second" className={`${inputClass} w-32`} value={start} onChange={e => setStart(e.target.value)} />
          <input aria-label="Exclude to video second" type="number" min="0" placeholder="To second" className={`${inputClass} w-32`} value={end} onChange={e => setEnd(e.target.value)} />
          <button className={buttonClass} disabled={start === "" || end === "" || !validExclusion(Number(start), Number(end), playhead)} onClick={() => command({ type: "analysis.exclude_interval", payload: { start_ms: Number(start) * 1000, end_ms: Number(end) * 1000 } })}>Exclude interval</button>
        </div>
      </fieldset>
    </div>}
    {currentData && <div className="border-t border-white/10 pt-4">
      <h3 className="mb-3 text-sm font-semibold">Shot review · xG is provisional</h3>
      {currentData.chance_quality.shots.length === 0 && <p className="text-sm text-muted-foreground">No shot candidates yet.</p>}
      <div className="space-y-2">{currentData.chance_quality.shots.slice(-12).reverse().map(shot => <div key={shot.id} className="flex flex-wrap items-center gap-2 text-sm">
        <span>{(shot.timestamp_ms / 1000).toFixed(1)} s · {currentData.match.team_names[shot.team === "team0" ? 0 : 1]} · {shot.status}</span>
        {currentData.runtime.clips_ready?.includes(shot.id) ? <a target="_blank" rel="noreferrer" className="underline" href={`/api/live/clips/${shot.id}`}>Review clip</a> : <span className="text-muted-foreground">Clip pending or unavailable</span>}
        <select aria-label="Shot team" disabled={!canControl} className={inputClass} value={shot.team} onChange={e => command({ type: "event.review", payload: { event_id: shot.id, patch: { team: e.target.value } } })}><option value="team0">{currentData.match.team_names[0]}</option><option value="team1">{currentData.match.team_names[1]}</option></select>
        <select aria-label="Shot on target" disabled={!canControl} className={inputClass} value={shot.on_target == null ? "unknown" : String(shot.on_target)} onChange={e => command({ type: "event.review", payload: { event_id: shot.id, patch: { on_target: e.target.value === "unknown" ? null : e.target.value === "true", outcome: null } } })}><option value="unknown">On target unknown</option><option value="true">On target</option><option value="false">Off target</option></select>
        <button disabled={!canControl} className={buttonClass} onClick={() => command({ type: "event.review", payload: { event_id: shot.id, patch: { status: "confirmed" } } })}>Confirm shot</button>
        <button disabled={!canControl} className={buttonClass} onClick={() => command({ type: "event.review", payload: { event_id: shot.id, patch: { status: "confirmed", outcome: "goal", on_target: true } } })}>Goal</button>
        <button disabled={!canControl} className={buttonClass} onClick={() => command({ type: "event.review", payload: { event_id: shot.id, patch: { status: "rejected" } } })}>Reject</button>
      </div>)}</div>
    </div>}
  </section>;
}
