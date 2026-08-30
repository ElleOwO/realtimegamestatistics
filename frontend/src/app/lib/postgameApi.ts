import type {
  AnalysisJob,
  InboxFile,
  Match,
  MatchEvent,
  MatchReport,
  Observation,
} from "../types/postgame";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL
  || (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || `${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export const postgameApi = {
  runtime: () => request<{
    mode: "live" | "test" | "replay";
    artifact_policy: "compact" | "source" | "full";
  }>("/api/runtime"),
  seedScenario: (name = "standard") =>
    request<Match>(`/api/test/scenarios/${encodeURIComponent(name)}`, { method: "POST" }),
  inbox: () => request<InboxFile[]>("/api/v1/inbox"),
  matches: () => request<Match[]>("/api/v1/matches"),
  match: (id: string) => request<Match>(`/api/v1/matches/${id}`),
  importMatch: (filename: string) =>
    request<Match>("/api/v1/matches/import", {
      method: "POST",
      body: JSON.stringify({ filename }),
    }),
  setup: (id: string, body: Record<string, unknown>) =>
    request<Match>(`/api/v1/matches/${id}/setup`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  preflight: (id: string) =>
    request<{ match_id: string; state: string; clusters: Array<{ cluster: number; preview_url: string; sample_count: number }> }>(
      `/api/v1/matches/${id}/preflight`,
      { method: "POST" },
    ),
  teamMapping: (id: string, usask_cluster: number) =>
    request<Match>(`/api/v1/matches/${id}/team-mapping`, {
      method: "PATCH",
      body: JSON.stringify({ usask_cluster }),
    }),
  analyze: (id: string) =>
    request<AnalysisJob>(`/api/v1/matches/${id}/analysis`, { method: "POST" }),
  cancel: (id: string) =>
    request<AnalysisJob>(`/api/v1/matches/${id}/cancel`, { method: "POST" }),
  report: (id: string) => request<MatchReport>(`/api/v1/matches/${id}/report`),
  events: (id: string) => request<MatchEvent[]>(`/api/v1/matches/${id}/events`),
  updateEvent: (matchId: string, eventId: string, body: Record<string, unknown>) =>
    request<MatchEvent>(`/api/v1/matches/${matchId}/events/${eventId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  addEvent: (matchId: string, body: Record<string, unknown>) =>
    request<MatchEvent>(`/api/v1/matches/${matchId}/events`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  observations: (id: string, fromMs: number, toMs: number) =>
    request<Observation[]>(
      `/api/v1/matches/${id}/observations?from_ms=${Math.max(fromMs, 0)}&to_ms=${Math.max(toMs, 0)}`,
    ),
  videoUrl: (id: string, kind: "source" | "annotated") =>
    `${API_BASE}/api/v1/matches/${id}/video/${kind}`,
  assetUrl: (path: string) => `${API_BASE}${path}`,
};
