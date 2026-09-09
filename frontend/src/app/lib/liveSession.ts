export interface LiveSession {
  id: string;
  event_url: string;
  state: string;
  error: string | null;
  deadline: number;
  artifacts_ready: boolean;
  worker_started: boolean;
}

export const isSessionActive = (session: LiveSession | null) =>
  !!session && ["starting", "waiting", "calibrating", "live", "reconnecting", "stopping"].includes(session.state);

export function sessionLabel(state: string): string {
  return ({ starting: "Starting GPU", waiting: "Connecting / waiting for broadcast", calibrating: "Calibrating teams and pitch",
    live: "Broadcast connected", reconnecting: "Reconnecting", interrupted: "Analysis interrupted",
    failed: "Could not start", stopping: "Saving and stopping", finished: "Session finished" } as Record<string, string>)[state] ?? state;
}

export function validExclusion(start: number, end: number, playhead: number): boolean {
  return Number.isFinite(start) && Number.isFinite(end) && start >= 0 && end >= start && end <= playhead;
}
