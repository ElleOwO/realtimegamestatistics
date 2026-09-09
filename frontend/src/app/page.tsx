"use client";

import { useState } from "react";
import { SessionControls } from "./components/live/SessionControls";

import { LiveReport } from "./components/live/LiveReport";
import { GameStateBar } from "./components/live/GameStateBar";
import { SystemHealthChip } from "./components/live/SystemHealthChip";
import { useSocket } from "./components/SocketProvider";
import { useDerivedMetrics } from "./hooks/useDerivedMetrics";

export default function LiveFootageAnalytics() {
  const { data: socketData, error, isConnected, sendCommand } = useSocket();
  const [managed, setManaged] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const data = managed && socketData?.runtime.run_id !== sessionId ? null : socketData;
  const { fps } = useDerivedMetrics(data);

  return (
    <div className="app-container app-page live-shell space-y-4 font-sans">
      <SessionControls data={data} connected={isConnected} sendCommand={sendCommand} onManaged={setManaged} onSession={setSessionId} />
      {error && <div role="alert" className="mb-4 border-l-2 border-destructive bg-destructive/10 px-4 py-3 text-sm text-red-100">{error}</div>}
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="eyebrow text-primary">Match command</p>
          <p className="mt-1 text-xs text-muted-foreground">Set the phase before analytics can accumulate.</p>
        </div>
        <SystemHealthChip data={data} isConnected={isConnected} fps={fps} />
      </div>
      <GameStateBar data={data} sendCommand={command => managed ? (!!data && isConnected && sendCommand({ ...command, source_timestamp_ms: data.frame.source_timestamp_ms })) : sendCommand(command)} />
      <LiveReport data={data} coreOnly={managed} />
    </div>
  );
}
