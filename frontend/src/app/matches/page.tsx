"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Film, FolderInput, Loader2, RefreshCw } from "lucide-react";
import { postgameApi } from "../lib/postgameApi";
import type { InboxFile, Match } from "../types/postgame";

const formatBytes = (bytes: number) => `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
const formatDuration = (ms: number) => `${Math.floor(ms / 60000)}:${Math.floor((ms % 60000) / 1000).toString().padStart(2, "0")}`;

export default function MatchesPage() {
  const [inbox, setInbox] = useState<InboxFile[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState<string | null>(null);
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
    refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => window.clearInterval(timer);
  }, [refresh]);

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
    <div className="mx-auto max-w-7xl space-y-8 p-2 font-sans md:p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-[10px] font-black uppercase tracking-[0.25em] text-primary">Post-game analysis</p>
          <h1 className="text-3xl font-black tracking-tight">Match library</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Copy a Veo MP4 into <code className="rounded bg-muted px-1.5 py-0.5">data/inbox</code>, then import and configure it here.
          </p>
        </div>
        <button onClick={refresh} className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-xs font-bold">
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          <AlertTriangle className="h-5 w-5" /> {error}. No mock values are being shown.
        </div>
      )}

      <section className="rounded-2xl border border-border bg-card p-6">
        <div className="mb-5 flex items-center gap-3">
          <FolderInput className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-black">Inbox</h2>
          <span className="rounded-full bg-muted px-2 py-1 text-[10px] font-bold text-muted-foreground">{inbox.length} MP4</span>
        </div>
        {loading ? (
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        ) : inbox.length === 0 ? (
          <p className="rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">No MP4 files are waiting to be imported.</p>
        ) : (
          <div className="divide-y divide-border">
            {inbox.map((file) => (
              <div key={file.filename} className="flex flex-wrap items-center justify-between gap-4 py-4">
                <div className="flex min-w-0 items-center gap-3">
                  <Film className="h-8 w-8 shrink-0 text-muted-foreground" />
                  <div className="min-w-0">
                    <p className="truncate font-bold">{file.filename}</p>
                    <p className="text-xs text-muted-foreground">{formatBytes(file.size_bytes)} · copied {new Date(file.modified_at).toLocaleString()}</p>
                  </div>
                </div>
                <button disabled={Boolean(importing)} onClick={() => importFile(file.filename)} className="rounded-lg bg-primary px-4 py-2 text-xs font-black text-primary-foreground disabled:opacity-50">
                  {importing === file.filename ? "Validating…" : "Import match"}
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-4 text-lg font-black">Imported matches</h2>
        {matches.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border p-12 text-center text-sm text-muted-foreground">Import the first match from the inbox above.</div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {matches.map((match) => (
              <Link key={match.id} href={`/matches/${match.id}`} className="group rounded-2xl border border-border bg-card p-5 transition hover:border-primary/50">
                <div className="mb-5 flex items-start justify-between gap-3">
                  <Film className="h-7 w-7 text-primary" />
                  <Status status={match.latest_job?.state || match.status} />
                </div>
                <h3 className="truncate text-lg font-black">
                  {match.home_team && match.away_team ? `${match.home_team} vs ${match.away_team}` : match.source_filename}
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {formatDuration(match.duration_ms)} · {match.source_width}×{match.source_height} · {match.source_codec}
                </p>
                {match.latest_job?.state === "running" && (
                  <div className="mt-5">
                    <div className="mb-1 flex justify-between text-[10px] font-bold uppercase text-muted-foreground"><span>Processing</span><span>{Math.round(match.latest_job.progress * 100)}%</span></div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-muted"><div className="h-full bg-primary" style={{ width: `${match.latest_job.progress * 100}%` }} /></div>
                  </div>
                )}
                {match.status === "completed" && <p className="mt-5 flex items-center gap-2 text-xs text-primary"><CheckCircle2 className="h-4 w-4" /> Report ready</p>}
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
