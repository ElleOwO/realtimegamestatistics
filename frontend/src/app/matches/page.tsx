"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, ArrowUpRight, CheckCircle2, Film, FolderInput, Loader2, RefreshCw } from "lucide-react";
import { postgameApi } from "../lib/postgameApi";
import type { InboxFile, Match } from "../types/postgame";

const formatBytes = (bytes: number) => `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
const formatDuration = (ms: number) => `${Math.floor(ms / 60000)}:${Math.floor((ms % 60000) / 1000).toString().padStart(2, "0")}`;

export default function MatchesPage() {
  const [inbox, setInbox] = useState<InboxFile[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);
  const [testMode, setTestMode] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [nextInbox, nextMatches] = await Promise.all([postgameApi.inbox(), postgameApi.matches()]);
      setInbox(nextInbox);
      setMatches(nextMatches);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Backend unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    postgameApi.runtime().then((runtime) => setTestMode(runtime.mode !== "live")).catch(() => undefined);
    refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const seedReplay = async () => {
    setSeeding(true);
    setError(null);
    try {
      await postgameApi.seedScenario();
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Replay fixture failed");
    } finally {
      setSeeding(false);
    }
  };

  const importFile = async (filename: string) => {
    setImporting(filename);
    setError(null);
    try {
      await postgameApi.importMatch(filename);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Import failed");
    } finally {
      setImporting(null);
    }
  };

  return (
    <div className="app-container app-page app-stack live-shell font-sans">
      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertTriangle className="h-5 w-5" /> {error}. No mock values are being shown.
        </div>
      )}

      <section className="overflow-hidden rounded-xl border border-white/10 bg-card">
        <div className="flex items-center gap-3 border-b border-white/10 bg-background/30 px-5 py-4 sm:px-6">
          <FolderInput className="h-5 w-5 text-primary" />
          <h2 className="font-display text-xl font-semibold uppercase tracking-wide">Footage inbox</h2>
          <div className="ml-auto flex items-center gap-3">
            {testMode && <button disabled={seeding} onClick={seedReplay} className="rounded-sm bg-secondary px-3 py-2 font-mono text-[9px] font-semibold uppercase tracking-[0.12em] text-secondary-foreground disabled:opacity-50">{seeding ? "Running…" : "Run replay fixture"}</button>}
            <span className="hidden font-mono text-[9px] font-semibold uppercase tracking-[0.14em] text-muted-foreground sm:inline">{inbox.length} files ready</span>
            <button onClick={refresh} aria-label="Refresh footage and matches" className="grid h-8 w-8 place-items-center rounded-sm border border-white/10 text-muted-foreground transition hover:border-white/20 hover:text-white">
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
        <div className="p-5 sm:p-6">
        {loading ? (
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        ) : inbox.length === 0 ? (
          <div className="border border-dashed border-white/15 px-6 py-9 text-center"><p className="font-display text-lg font-semibold uppercase tracking-wide text-white">The touchline is clear</p><p className="mt-2 text-sm text-muted-foreground">Copy an MP4 into <code className="bg-background px-1.5 py-0.5 font-mono text-xs text-foreground">data/inbox</code> to prepare a match.</p></div>
        ) : (
          <div className="divide-y divide-white/10">
            {inbox.map((file) => (
              <div key={file.filename} className="flex flex-wrap items-center justify-between gap-4 py-4">
                <div className="flex min-w-0 items-center gap-3">
                  <Film className="h-8 w-8 shrink-0 text-muted-foreground" />
                  <div className="min-w-0">
                    <p className="truncate font-bold">{file.filename}</p>
                    <p className="text-xs text-muted-foreground">{formatBytes(file.size_bytes)} · copied {new Date(file.modified_at).toLocaleString()}</p>
                  </div>
                </div>
                <button disabled={Boolean(importing)} onClick={() => importFile(file.filename)} className="rounded-sm bg-primary px-4 py-2.5 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-primary-foreground disabled:opacity-50">
                  {importing === file.filename ? "Validating…" : "Import match"}
                </button>
              </div>
            ))}
          </div>
        )}
        </div>
      </section>

      <section>
        <div className="mb-4 flex items-baseline justify-between"><h2 className="font-display text-2xl font-semibold uppercase tracking-wide">Imported matches</h2><p className="font-mono text-[9px] uppercase tracking-[0.14em] text-muted-foreground">{matches.length} in archive</p></div>
        {matches.length === 0 ? (
          <div className="rounded-xl border border-dashed border-white/15 p-12 text-center text-sm text-muted-foreground">Import the first match from the footage inbox above.</div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {matches.map((match) => (
              <Link key={match.id} href={`/matches/${match.id}`} className="group relative overflow-hidden rounded-xl border border-white/10 bg-card p-5 transition hover:-translate-y-0.5 hover:border-primary/45 hover:shadow-xl hover:shadow-black/15">
                <span className="absolute inset-x-0 top-0 h-0.5 origin-left scale-x-0 bg-primary transition-transform group-hover:scale-x-100" />
                <div className="mb-8 flex items-start justify-between gap-3">
                  <span className="grid h-10 w-10 place-items-center rounded-sm bg-primary/10 text-primary"><Film className="h-5 w-5" /></span>
                  <Status status={match.latest_job?.state || match.status} />
                </div>
                <h3 className="truncate font-display text-xl font-semibold uppercase tracking-[0.025em]">
                  {match.home_team && match.away_team ? `${match.home_team} vs ${match.away_team}` : match.source_filename}
                </h3>
                <p className="mt-2 font-mono text-[10px] text-muted-foreground">
                  {formatDuration(match.duration_ms)} · {match.source_width}×{match.source_height} · {match.source_codec}
                </p>
                {match.latest_job?.state === "running" && (
                  <div className="mt-5">
                    <div className="mb-1 flex justify-between text-[10px] font-bold uppercase text-muted-foreground"><span>Processing</span><span>{Math.round(match.latest_job.progress * 100)}%</span></div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-muted"><div className="h-full bg-primary" style={{ width: `${match.latest_job.progress * 100}%` }} /></div>
                  </div>
                )}
                {match.status === "completed" && <p className="mt-6 flex items-center gap-2 border-t border-white/10 pt-4 font-mono text-[9px] font-semibold uppercase tracking-[0.12em] text-primary"><CheckCircle2 className="h-4 w-4" /> Report ready <ArrowUpRight className="ml-auto h-4 w-4" /></p>}
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function Status({ status }: { status: string }) {
  const failed = ["failed", "interrupted", "cancelled"].includes(status);
  return <span className={`rounded-full border px-2.5 py-1 text-[9px] font-black uppercase tracking-wider ${failed ? "border-red-500/30 bg-red-500/10 text-red-300" : "border-primary/30 bg-primary/10 text-primary"}`}>{status.replaceAll("_", " ")}</span>;
}
