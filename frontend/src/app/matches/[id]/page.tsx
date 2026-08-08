"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, ArrowLeft, Check, Film, Loader2, Play, RotateCcw, Square, Wifi, WifiOff } from "lucide-react";
import { useMatchStream } from "../../hooks/useMatchStream";
import { postgameApi } from "../../lib/postgameApi";
import type { Match, MatchEvent, MatchReport, MetricValue, Observation, StreamMessage } from "../../types/postgame";

const formatTime = (ms: number) => `${Math.floor(ms / 60000)}:${Math.floor((ms % 60000) / 1000).toString().padStart(2, "0")}`;
const numeric = (metric?: MetricValue) => metric?.value === null || metric?.value === undefined ? "—" : `${typeof metric.value === "number" ? metric.value.toFixed(metric.unit === "%" ? 1 : 2) : metric.value}${metric.unit ? ` ${metric.unit}` : ""}`;

export default function MatchDetailPage() {
  const id = useParams<{ id: string }>().id;
  const [match, setMatch] = useState<Match | null>(null);
  const [report, setReport] = useState<MatchReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [clusters, setClusters] = useState<Array<{ cluster: number; preview_url: string; sample_count: number }>>([]);

  const load = useCallback(async () => {
    try {
      const nextMatch = await postgameApi.match(id);
      setMatch(nextMatch);
      if (nextMatch.latest_job || nextMatch.status === "completed") setReport(await postgameApi.report(id));
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load match");
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);
  const onStream = useCallback((message: StreamMessage) => {
    if (message.type === "provisional_report") setReport(message.payload as unknown as MatchReport);
    if (message.type === "completed") {
      const payload = message.payload as { report?: MatchReport };
      if (payload.report) setReport(payload.report);
    }
    if (["progress", "job_status", "completed", "error"].includes(message.type)) load();
  }, [load]);
  const stream = useMatchStream(id, onStream);

  const act = async (label: string, action: () => Promise<unknown>) => {
    setBusy(label); setError(null);
    try { await action(); await load(); } catch (cause) { setError(cause instanceof Error ? cause.message : `${label} failed`); }
    finally { setBusy(null); }
  };

  if (!match) return <div className="flex h-64 items-center justify-center">{error ? <ErrorBox message={error} /> : <Loader2 className="h-6 w-6 animate-spin" />}</div>;
  const job = match.latest_job;

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 p-2 font-sans md:p-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link href="/matches" className="rounded-lg border border-border p-2"><ArrowLeft className="h-4 w-4" /></Link>
          <div><p className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">Match workspace</p><h1 className="text-2xl font-black">{match.home_team ? `${match.home_team} vs ${match.away_team}` : match.source_filename}</h1></div>
        </div>
        <span className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-[10px] font-bold uppercase ${stream.connected ? "border-primary/30 text-primary" : "border-border text-muted-foreground"}`}>
          {stream.connected ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}{stream.connected ? "Updates connected" : "Reconnecting"}
        </span>
      </div>
      {error && <ErrorBox message={error} />}

      {!match.setup_complete ? (
        <SetupForm match={match} disabled={Boolean(busy)} onSubmit={(body) => act("setup", () => postgameApi.setup(id, body))} />
      ) : !("usask_cluster" in match.team_mapping) ? (
        <section className="rounded-2xl border border-border bg-card p-6">
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">Team calibration</p>
          <h2 className="mt-1 text-xl font-black">Identify the USask kit cluster</h2>
          <p className="mt-2 text-sm text-muted-foreground">Preflight samples frames across the match and fits two anonymous kit clusters. Analysis will not start until you confirm the mapping.</p>
          {clusters.length === 0 ? (
            <button disabled={Boolean(busy)} onClick={() => act("preflight", async () => { const result = await postgameApi.preflight(id); setClusters(result.clusters); })} className="mt-6 rounded-lg bg-primary px-5 py-3 text-xs font-black text-primary-foreground disabled:opacity-50">
              {busy === "preflight" ? "Running GPU preflight…" : "Run calibration preview"}
            </button>
          ) : (
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {clusters.map((cluster) => <button key={cluster.cluster} onClick={() => act("mapping", () => postgameApi.teamMapping(id, cluster.cluster))} className="overflow-hidden rounded-xl border border-border text-left transition hover:border-primary"><img src={postgameApi.assetUrl(cluster.preview_url)} alt={`Kit cluster ${cluster.cluster}`} className="w-full bg-black object-contain" /><span className="block p-4 text-sm font-black">Cluster {cluster.cluster + 1} · {cluster.sample_count} samples <span className="float-right text-primary">Choose as USask</span></span></button>)}
            </div>
          )}
        </section>
      ) : !job ? (
        <Ready match={match} busy={busy} onStart={() => act("analysis", () => postgameApi.analyze(id))} />
      ) : ["queued", "running", "preflight"].includes(job.state) ? (
        <Processing match={match} onCancel={() => act("cancel", () => postgameApi.cancel(id))} />
      ) : job.state === "failed" || job.state === "interrupted" || job.state === "cancelled" ? (
        <section className="rounded-2xl border border-red-500/30 bg-red-500/5 p-6"><AlertTriangle className="mb-3 h-7 w-7 text-red-300" /><h2 className="text-xl font-black">Analysis {job.state}</h2><p className="mt-2 max-w-3xl text-sm text-red-100/80">{job.failure_detail || "The partial report remains available. Restarting begins from the source video."}</p><button onClick={() => act("restart", () => postgameApi.analyze(id))} className="mt-5 flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-black"><RotateCcw className="h-4 w-4" /> Restart from beginning</button></section>
      ) : report ? <ReportWorkspace match={match} initialReport={report} onReload={async () => setReport(await postgameApi.report(id))} /> : <Loader2 className="h-6 w-6 animate-spin" />}
    </div>
  );
}

function SetupForm({ match, disabled, onSubmit }: { match: Match; disabled: boolean; onSubmit: (body: Record<string, unknown>) => void }) {
  const half = Math.floor(match.duration_ms / 2 / 1000);
  const [values, setValues] = useState({ home_team: "USask", away_team: "", home_score: "0", away_score: "0", usask_side: "home", kickoff: "0", firstEnd: String(Math.max(half - 600, 1)), secondStart: String(Math.min(half + 600, Math.floor(match.duration_ms / 1000) - 1)), fullTime: String(Math.floor(match.duration_ms / 1000)), direction1: "right", direction2: "left" });
  const submit = (event: FormEvent) => { event.preventDefault(); onSubmit({ home_team: values.home_team, away_team: values.away_team, home_score: Number(values.home_score), away_score: Number(values.away_score), usask_side: values.usask_side, periods: [{ number: 1, start_ms: Number(values.kickoff) * 1000, end_ms: Number(values.firstEnd) * 1000 }, { number: 2, start_ms: Number(values.secondStart) * 1000, end_ms: Number(values.fullTime) * 1000 }], directions: { "1": values.direction1, "2": values.direction2 } }); };
  const field = (key: keyof typeof values, label: string, type = "text") => <label className="space-y-2 text-xs font-bold text-muted-foreground"><span>{label}</span><input required type={type} value={values[key]} onChange={(e) => setValues({ ...values, [key]: e.target.value })} className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-foreground" /></label>;
  return <form onSubmit={submit} className="rounded-2xl border border-border bg-card p-6"><p className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">Required setup</p><h2 className="mt-1 text-xl font-black">Match facts and video boundaries</h2><p className="mt-2 text-sm text-muted-foreground">Times are source-video seconds. The final score remains operator-supplied and is never inferred from xG.</p><div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">{field("home_team", "Home team")}{field("away_team", "Away team")}{field("home_score", "Home final score", "number")}{field("away_score", "Away final score", "number")}{field("kickoff", "First-half kickoff (s)", "number")}{field("firstEnd", "First-half end (s)", "number")}{field("secondStart", "Second-half kickoff (s)", "number")}{field("fullTime", "Full-time (s)", "number")}<label className="space-y-2 text-xs font-bold text-muted-foreground"><span>USask is</span><select value={values.usask_side} onChange={(e) => setValues({ ...values, usask_side: e.target.value })} className="w-full rounded-lg border border-border bg-background px-3 py-2.5"><option value="home">Home</option><option value="away">Away</option></select></label>{[1, 2].map((period) => <label key={period} className="space-y-2 text-xs font-bold text-muted-foreground"><span>USask attacks in half {period}</span><select value={period === 1 ? values.direction1 : values.direction2} onChange={(e) => setValues({ ...values, [period === 1 ? "direction1" : "direction2"]: e.target.value })} className="w-full rounded-lg border border-border bg-background px-3 py-2.5"><option value="right">Right</option><option value="left">Left</option></select></label>)}</div><button disabled={disabled} className="mt-6 rounded-lg bg-primary px-5 py-3 text-xs font-black text-primary-foreground disabled:opacity-50">Save setup</button></form>;
}

function Ready({ match, busy, onStart }: { match: Match; busy: string | null; onStart: () => void }) {
  return <section className="rounded-2xl border border-primary/30 bg-card p-8"><Check className="mb-4 h-8 w-8 text-primary" /><h2 className="text-2xl font-black">Ready to analyze</h2><p className="mt-2 text-sm text-muted-foreground">{match.home_team} {match.home_score}–{match.away_score} {match.away_team} · {formatTime(match.duration_ms)} source video. One GPU job runs at a time; this match may queue behind another.</p><button disabled={Boolean(busy)} onClick={onStart} className="mt-6 flex items-center gap-2 rounded-lg bg-primary px-5 py-3 text-xs font-black text-primary-foreground"><Play className="h-4 w-4" /> Start full analysis</button></section>;
}

function Processing({ match, onCancel }: { match: Match; onCancel: () => void }) {
  const job = match.latest_job!;
  return <div className="grid gap-6 lg:grid-cols-[2fr_1fr]"><section className="rounded-2xl border border-border bg-card p-6"><div className="flex items-center justify-between"><div><p className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">{job.state}</p><h2 className="text-xl font-black">Processing source video</h2></div><span className="text-3xl font-black">{Math.round(job.progress * 100)}%</span></div><div className="mt-6 h-3 overflow-hidden rounded-full bg-muted"><div className="h-full bg-primary transition-all" style={{ width: `${job.progress * 100}%` }} /></div><div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4"><ProgressStat label="Video time" value={formatTime(job.current_video_ms)} /><ProgressStat label="Processing" value={job.processing_fps ? `${job.processing_fps.toFixed(1)} samples/s` : "—"} /><ProgressStat label="ETA" value={job.eta_seconds ? formatTime(job.eta_seconds * 1000) : "—"} /><ProgressStat label="Calibration" value={`${(job.calibration_coverage * 100).toFixed(0)}%`} /></div><button onClick={onCancel} className="mt-6 flex items-center gap-2 rounded-lg border border-red-500/30 px-4 py-2 text-xs font-black text-red-300"><Square className="h-3 w-3" /> Cancel</button></section><section className="rounded-2xl border border-border bg-card p-6"><h3 className="font-black">Diagnostics</h3><div className="mt-4 max-h-64 space-y-2 overflow-auto font-mono text-[11px] text-muted-foreground">{job.log_tail.length ? job.log_tail.map((line, i) => <p key={i}>{line}</p>) : <p>No warnings. Progress is persisted on each sampled source timestamp.</p>}</div></section></div>;
}

function ProgressStat({ label, value }: { label: string; value: string }) { return <div className="rounded-xl bg-background p-4"><p className="text-[9px] font-black uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 font-mono text-lg font-black">{value}</p></div>; }

function ErrorBox({ message }: { message: string }) { return <div className="flex items-center gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200"><AlertTriangle className="h-5 w-5 shrink-0" />{message}</div>; }

function ReportWorkspace({ match, initialReport, onReload }: { match: Match; initialReport: MatchReport; onReload: () => Promise<void> }) {
  const [report, setReport] = useState(initialReport);
  const [videoKind, setVideoKind] = useState<"source" | "annotated">("source");
  const [currentMs, setCurrentMs] = useState(0);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [tab, setTab] = useState("overview");
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => setReport(initialReport), [initialReport]);
  useEffect(() => { const timer = window.setTimeout(() => postgameApi.observations(match.id, Math.max(currentMs - 75, 0), currentMs + 75).then(setObservations).catch(() => setObservations([])), 120); return () => window.clearTimeout(timer); }, [currentMs, match.id]);
  const seek = (ms: number) => { if (video.current) video.current.currentTime = ms / 1000; setCurrentMs(ms); };
  const review = async (event: MatchEvent, status: MatchEvent["review_status"], extra: Record<string, unknown> = {}) => { await postgameApi.updateEvent(match.id, event.id, { review_status: status, ...extra }); const next = await postgameApi.report(match.id); setReport(next); await onReload(); };
  const sections: Record<string, Record<string, MetricValue>> = { overview: report.summary, territory: report.territorial, transitions: report.transitions, shape: report.shape, quality: report.quality };
  if (report.pressing) sections.pressing = report.pressing;
  return <div className="space-y-6"><div className="sticky top-24 z-20 grid gap-4 rounded-2xl border border-border bg-background/95 p-4 backdrop-blur lg:grid-cols-[2fr_1fr]"><div><div className="mb-3 flex items-center justify-between"><div className="flex gap-2">{(["source", "annotated"] as const).map((kind) => <button key={kind} onClick={() => setVideoKind(kind)} className={`rounded-lg px-3 py-1.5 text-[10px] font-black uppercase ${videoKind === kind ? "bg-primary text-primary-foreground" : "bg-card text-muted-foreground"}`}>{kind}</button>)}</div><span className="font-mono text-sm font-black">{formatTime(currentMs)}</span></div><video ref={video} key={videoKind} controls preload="metadata" src={postgameApi.videoUrl(match.id, videoKind)} onTimeUpdate={(e) => setCurrentMs(Math.round(e.currentTarget.currentTime * 1000))} className="aspect-video w-full rounded-xl bg-black" /></div><PitchSnapshot observations={observations} /></div><section className="rounded-2xl border border-border bg-card p-6"><div className="flex flex-wrap items-center justify-between gap-4"><div><p className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">{report.provisional ? "Provisional report" : "Completed report"}</p><h2 className="text-2xl font-black">{report.score.home_team} <span className="mx-2 font-mono">{report.score.home}–{report.score.away}</span> {report.score.away_team}</h2></div><span className="text-xs text-muted-foreground">Score source: operator</span></div>{report.diagnostics.map((item) => <p key={item} className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">{item}</p>)}<div className="mt-6 flex flex-wrap gap-2">{Object.keys(sections).map((name) => <button key={name} onClick={() => setTab(name)} className={`rounded-lg px-4 py-2 text-[10px] font-black uppercase ${tab === name ? "bg-primary text-primary-foreground" : "bg-background text-muted-foreground"}`}>{name}</button>)}</div><div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{Object.entries(sections[tab]).map(([key, value]) => <MetricCard key={key} label={key} metric={value} />)}</div></section><section className="grid gap-6 lg:grid-cols-[1fr_2fr]"><div className="rounded-2xl border border-border bg-card p-5"><div className="flex items-center justify-between"><h3 className="font-black">Event review</h3><button onClick={async () => { const type = window.prompt("Event type", "shot") || "shot"; const team = window.prompt("Team: home or away", match.usask_side || "home"); await postgameApi.addEvent(match.id, { type, team, timestamp_ms: currentMs, review_status: "confirmed" }); setReport(await postgameApi.report(match.id)); }} className="text-[10px] font-black uppercase text-primary">+ Manual event</button></div><div className="mt-4 max-h-[560px] space-y-3 overflow-auto">{report.events.length ? report.events.map((event) => <div key={event.id} className="rounded-xl border border-border bg-background p-3"><button onClick={() => seek(event.timestamp_ms)} className="w-full text-left"><div className="flex justify-between"><span className="text-xs font-black uppercase">{event.type.replaceAll("_", " ")}</span><span className="font-mono text-xs">{formatTime(event.timestamp_ms)}</span></div><p className="mt-1 text-[10px] text-muted-foreground">{event.team || "Unassigned"} · confidence {(event.confidence * 100).toFixed(0)}% · {event.review_status}</p></button><div className="mt-3 flex flex-wrap gap-2"><button onClick={() => review(event, "confirmed")} className="rounded bg-primary/15 px-2 py-1 text-[9px] font-black text-primary">CONFIRM</button><button onClick={() => review(event, "corrected", { play_context: event.play_context === "set_piece" ? "open_play" : "set_piece" })} className="rounded bg-amber-500/15 px-2 py-1 text-[9px] font-black text-amber-200">{event.play_context === "set_piece" ? "OPEN PLAY" : "SET PIECE"}</button>{event.type === "shot" && <button onClick={() => review(event, "corrected", { on_target: true })} className="rounded bg-blue-500/15 px-2 py-1 text-[9px] font-black text-blue-200">ON TARGET</button>}<button onClick={() => review(event, "rejected")} className="rounded bg-red-500/15 px-2 py-1 text-[9px] font-black text-red-200">REJECT</button></div></div>) : <p className="text-sm text-muted-foreground">No events were measured.</p>}</div></div><ShotMap report={report} /></section></div>;
}

function MetricCard({ label, metric }: { label: string; metric: MetricValue }) { return <div className="rounded-xl border border-border bg-background p-4"><div className="flex items-start justify-between gap-2"><p className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">{label.replaceAll("_", " ")}</p><span className={`rounded px-1.5 py-0.5 text-[8px] font-black uppercase ${metric.status === "unavailable" ? "bg-muted text-muted-foreground" : metric.status === "experimental" ? "bg-amber-500/15 text-amber-200" : "bg-primary/15 text-primary"}`}>{metric.status}</span></div><p className="mt-3 text-2xl font-black">{numeric(metric)}</p><p className="mt-2 text-[10px] text-muted-foreground">Confidence {(metric.confidence * 100).toFixed(0)}% · coverage {(metric.sample_coverage * 100).toFixed(0)}%</p>{metric.explanation && <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">{metric.explanation}</p>}</div>; }

function PitchSnapshot({ observations }: { observations: Observation[] }) { return <div className="flex flex-col"><p className="mb-3 text-[10px] font-black uppercase tracking-wider text-muted-foreground">Synchronized pitch observations</p><svg viewBox="0 0 105 68" className="aspect-[105/68] w-full rounded-xl bg-[#0a3523]"><rect x="0.5" y="0.5" width="104" height="67" fill="none" stroke="#ffffff66" /><line x1="52.5" x2="52.5" y1="0" y2="68" stroke="#ffffff66" /><circle cx="52.5" cy="34" r="9.15" fill="none" stroke="#ffffff66" />{observations.filter((item) => item.pitch_x_m !== null && item.pitch_y_m !== null).map((item) => <circle key={item.id} cx={item.pitch_x_m!} cy={item.pitch_y_m!} r={item.object_type === "ball" ? 1.2 : 1.7} fill={item.object_type === "ball" ? "white" : item.team === "home" ? "#23a469" : "#DBCC52"} stroke="#111" strokeWidth="0.4" />)}</svg>{observations.length === 0 && <p className="mt-2 text-xs text-muted-foreground">No valid observations at this timestamp.</p>}</div>; }

function ShotMap({ report }: { report: MatchReport }) { return <div className="rounded-2xl border border-border bg-card p-5"><h3 className="font-black">Shot map</h3><p className="mt-1 text-xs text-muted-foreground">All automatic shots require review; on-target remains unknown until confirmed.</p><svg viewBox="0 0 105 68" className="mt-5 w-full rounded-xl bg-[#0a3523]"><rect x="0.5" y="0.5" width="104" height="67" fill="none" stroke="#ffffff66" /><line x1="52.5" x2="52.5" y1="0" y2="68" stroke="#ffffff66" />{report.shot_map.map((shot, index) => typeof shot.x_m === "number" && typeof shot.y_m === "number" ? <g key={String(shot.event_id || index)}><circle cx={shot.x_m} cy={shot.y_m} r={2 + Number(shot.xg || 0) * 6} fill={shot.team === "home" ? "#23a469" : "#DBCC52"} opacity="0.85" /><text x={Number(shot.x_m) + 2} y={Number(shot.y_m) - 2} fontSize="2.5" fill="white">{Number(shot.xg || 0).toFixed(2)}</text></g> : null)}</svg></div>; }
