"use client";

import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Zap,
  Target,
  Activity,
} from "lucide-react";
import { ScrollArea } from "./ui/scroll-area";
import { useSocket } from "./SocketProvider";

interface PlayerPerformance {
  id: number;
  name: string;
  position: string;
  rating: number; // 0-10
  trend: "up" | "down" | "stable";
  fatigue: number; // 0-100
  impact: number; // 0-100 (match impact score)
  keyStat: string;
}

const PLAYER_NAME_MAP: Record<number, string> = {
  1: "Goalkeeper",
  2: "L. Bronze",
  3: "N. Charles",
  4: "M. Bright",
  5: "A. Greenwood",
  6: "K. Walsh",
  7: "L. James",
  8: "G. Stanway",
  9: "E. Toone",
  10: "S. Hansen",
  11: "L. Hemp",
};

export function PlayerPerformanceMatrix() {
  const { data } = useSocket();

  // If we have realtime data, map it to our UI structure
  const players: PlayerPerformance[] = data ? data.players.filter(p => p.team === 0).map(p => ({
    id: p.id,
    name: PLAYER_NAME_MAP[p.id] || `Player ${p.id}`,
    position: p.id === 1 ? "GK" : p.id < 6 ? "DF" : p.id < 9 ? "MF" : "FW",
    rating: 7.0 + (Math.random() * 2), // Mock rating logic
    trend: Math.random() > 0.5 ? "up" : "stable",
    fatigue: Math.min(Math.round((p.distance_km || 0) * 10), 100),
    impact: Math.min(Math.round((p.top_speed_ms || 0) * 8), 100),
    keyStat: `${(p.distance_km || 0).toFixed(2)} km • ${p.is_sprinting ? "SPRINTING" : "Active"}`,
  })) : [
    {
      id: 10,
      name: "S. Hansen",
      position: "FW",
      rating: 8.4,
      trend: "up",
      fatigue: 65,
      impact: 92,
      keyStat: "2 Goals, 1 Assist",
    },
    {
      id: 6,
      name: "K. Walsh",
      position: "MF",
      rating: 9.1,
      trend: "up",
      fatigue: 85,
      impact: 88,
      keyStat: "94% Pass Accuracy",
    },
    {
      id: 4,
      name: "M. Bright",
      position: "DF",
      rating: 7.9,
      trend: "stable",
      fatigue: 25,
      impact: 78,
      keyStat: "8 Interceptions",
    },
  ];

  const getTrendIcon = (trend: PlayerPerformance["trend"]) => {
    switch (trend) {
      case "up":
        return <TrendingUp className="w-4 h-4 text-primary" />;
      case "down":
        return <TrendingDown className="w-4 h-4 text-muted-foreground" />;
      case "stable":
        return <Minus className="w-4 h-4 text-muted-foreground/50" />;
    }
  };

  return (
    <Card className="h-full flex flex-col border-border  bg-card ">
      <CardHeader className="flex flex-row items-center justify-between p-6 pb-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Activity className="w-6 h-6 text-foreground" />
          <div>
            <CardTitle className="text-xl font-black uppercase tracking-tight text-foreground">
              Performance
            </CardTitle>
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
              Real-time Squad Impact Analysis
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Badge
            variant={data ? "default" : "outline"}
            className={data ? "bg-green-500/10 text-green-500 border-green-500/20 text-[9px] font-black uppercase" : "border-border text-muted-foreground font-bold uppercase text-[9px]"}
          >
            {data ? "LIVE STREAMING" : "DEMO MODE"}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-0 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="divide-y divide-border/50">
            {players.map((player) => (
              <div
                key={player.id}
                className="p-6 hover:bg-muted/30 transition-colors group"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-muted border border-border flex items-center justify-center font-black text-xl text-foreground group-hover:border-primary transition-colors">
                      {player.id}
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-black text-lg text-foreground uppercase tracking-tight">
                          {player.name}
                        </span>
                        {getTrendIcon(player.trend)}
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge className="bg-muted text-muted-foreground border-border text-[9px] font-black tracking-widest uppercase hover:bg-muted/80">
                          {player.position}
                        </Badge>
                        <span className="text-[10px] font-bold text-muted-foreground uppercase">
                          {player.keyStat}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-black text-foreground tracking-tighter">
                      {player.rating.toFixed(1)}
                    </div>
                    <div className="text-[9px] font-black uppercase text-muted-foreground tracking-widest">
                      Match Rating
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-8">
                  <div className="space-y-2">
                    <div className="flex justify-between items-end">
                      <div className="flex items-center gap-2">
                        <Zap
                          className={`w-3 h-3 ${player.fatigue > 75 ? "text-secondary" : "text-muted-foreground"}`}
                        />
                        <span className="text-[9px] font-black uppercase text-muted-foreground tracking-widest">
                          Fatigue Level
                        </span>
                      </div>
                      <span
                        className={`text-[10px] font-black ${player.fatigue > 75 ? "text-secondary" : "text-foreground/80"}`}
                      >
                        {player.fatigue}%
                      </span>
                    </div>
                    <Progress
                      value={player.fatigue}
                      className="h-1 bg-muted"
                      indicatorClassName={
                        player.fatigue > 75 ? "bg-secondary" : "bg-muted-foreground"
                      }
                    />
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between items-end">
                      <div className="flex items-center gap-2">
                        <Target className="w-3 h-3 text-primary" />
                        <span className="text-[9px] font-black uppercase text-muted-foreground tracking-widest">
                          Tactical Impact
                        </span>
                      </div>
                      <span className="text-[10px] font-black text-foreground">
                        {player.impact}%
                      </span>
                    </div>
                    <Progress
                      value={player.impact}
                      className="h-1 bg-muted"
                      indicatorClassName="bg-primary"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
