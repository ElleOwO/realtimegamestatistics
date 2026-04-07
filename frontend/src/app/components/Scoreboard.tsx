"use client";

import { useSocket } from "./SocketProvider";
import { Badge } from "./ui/badge";
import { Wifi, WifiOff, Clock } from "lucide-react";

export function Scoreboard() {
  const { data, isConnected } = useSocket();

  // If we don't have data yet, show a placeholder
  const team0Name = data?.possession?.team0_name || "U of S";
  const team1Name = data?.possession?.team1_name || "Opponent";
  
  // We can use total_xg_team0 as a pseudo-score if real score isn't available
  // Or just hardcode 0 - 0 for now
  const score0 = data ? Math.floor(data.total_xg_team0) : 0;
  const score1 = data ? Math.floor(data.total_xg_team1) : 0;

  const formatClock = (matchClock?: number) => {
    if (!matchClock) return "00:00";
    const minutes = Math.floor(matchClock);
    const seconds = Math.floor((matchClock - minutes) * 60);
    return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
  };

  return (
    <div className="w-full flex items-center justify-between bg-zinc-950/80 backdrop-blur-md border-b border-border/40 p-4 sticky top-0 z-50">
      
      {/* Left: Clock */}
      <div className="flex items-center gap-3 w-[200px]">
        <div className="flex items-center justify-center bg-zinc-900 border border-zinc-800 rounded-md px-3 py-1.5 font-mono text-xl tracking-wider text-green-500">
          <Clock className="w-4 h-4 mr-2 text-zinc-500" />
          {formatClock(data?.match_clock)}
        </div>
      </div>

      {/* Center: Score */}
      <div className="flex-1 flex items-center justify-center">
        <div className="flex items-center gap-6 md:gap-12 bg-zinc-900/50 rounded-2xl px-8 py-3 border border-zinc-800/50 shadow-2xl">
          <div className="text-xl md:text-3xl font-black uppercase tracking-tight text-white w-32 md:w-48 text-right truncate">
            {team0Name}
          </div>
          <div className="flex items-center gap-4 text-3xl md:text-5xl font-black font-mono">
            <span className="text-green-500 bg-green-500/10 px-4 py-1 rounded-lg border border-green-500/20">{score0}</span>
            <span className="text-zinc-600">-</span>
            <span className="text-amber-500 bg-amber-500/10 px-4 py-1 rounded-lg border border-amber-500/20">{score1}</span>
          </div>
          <div className="text-xl md:text-3xl font-black uppercase tracking-tight text-white w-32 md:w-48 text-left truncate">
            {team1Name}
          </div>
        </div>
      </div>

      {/* Right: Connection Status */}
      <div className="flex items-center justify-end gap-3 w-[200px]">
        {data && (
          <Badge variant="outline" className="hidden lg:flex py-1 px-3 border-border bg-card">
            <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
              Frame: {data.frame_id}
            </span>
          </Badge>
        )}
        <Badge variant={isConnected ? "default" : "destructive"} className="gap-1.5 py-1 px-3">
          {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
          <span className="text-[10px] font-black uppercase tracking-widest">
            {isConnected ? "Live Feed" : "Searching..."}
          </span>
        </Badge>
      </div>

    </div>
  );
}