"use client";

import { useSocket } from "./components/SocketProvider";
import { useDerivedMetrics } from "./hooks/useDerivedMetrics";
import { GameStateBar } from "./components/live/GameStateBar";
import { ChanceQualityPanel } from "./components/live/ChanceQualityPanel";
import { ProgressionPanel } from "./components/live/ProgressionPanel";
import { TeamShapePanel } from "./components/live/TeamShapePanel";
import { TransitionsPanel } from "./components/live/TransitionsPanel";
import { XgTimelineChart } from "./components/live/XgTimelineChart";
import { EventsTicker } from "./components/live/EventsTicker";

/**
 * Live "Match Command" dashboard. Panel set follows the coaching-priority
 * categories: game state, chance quality, progression, transitions,
 * team shape, and system confidence. Only payload-backed or client-derivable
 * metrics are shown live; the rest are explicit pending-backend placeholders.
 */
export default function LiveDashboard() {
  const { data, isConnected, error, sendCommand } = useSocket();
  const { fps } = useDerivedMetrics(data);
  const teamNames: [string, string] = data?.match.team_names ?? ["USask", "Opponent"];

  return (
    <div className="w-full h-full flex flex-col gap-3">
      <GameStateBar
        data={data}
        isConnected={isConnected}
        fps={fps}
        sendCommand={sendCommand}
      />

      {!data && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          {isConnected
            ? "The backend is running in post-game mode; no live frames are being published."
            : error || "Live backend unavailable. Demo data is disabled unless NEXT_PUBLIC_DEMO_MODE=true."}
        </div>
      )}

      {/* Stat panels: chance quality / progression / shape / transitions */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <ChanceQualityPanel data={data} teamNames={teamNames} sendCommand={sendCommand} />
        <ProgressionPanel data={data} teamNames={teamNames} />
        <TeamShapePanel data={data} teamNames={teamNames} sendCommand={sendCommand} />
        <TransitionsPanel data={data} teamNames={teamNames} />
      </div>

      {/* Bottom strip: xG race + event feed (fills remaining height) */}
      <div className="flex-1 min-h-0 grid gap-3 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <XgTimelineChart data={data} teamNames={teamNames} />
        <EventsTicker data={data} teamNames={teamNames} />
      </div>
    </div>
  );
}
