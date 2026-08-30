"use client";

import { LiveReport } from "./components/live/LiveReport";
import { GameStateBar } from "./components/live/GameStateBar";
import { SystemHealthChip } from "./components/live/SystemHealthChip";
import { useSocket } from "./components/SocketProvider";
import { useDerivedMetrics } from "./hooks/useDerivedMetrics";

export default function LiveFootageAnalytics() {
  const { data, error, isConnected, sendCommand } = useSocket();
  const { fps } = useDerivedMetrics(data);

  return (
    <div className="app-container app-page live-shell space-y-4 font-sans">
      {error && <div role="alert" className="mb-4 border-l-2 border-destructive bg-destructive/10 px-4 py-3 text-sm text-red-100">{error}</div>}
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="eyebrow text-primary">Match command</p>
          <p className="mt-1 text-xs text-muted-foreground">Set the phase before analytics can accumulate.</p>
        </div>
        <SystemHealthChip data={data} isConnected={isConnected} fps={fps} />
      </div>
      <GameStateBar data={data} sendCommand={sendCommand} />
      <LiveReport data={data} />
    </div>
  );
}
