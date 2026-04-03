"use client";

import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Target, Zap, Users, Shield, TrendingUp } from 'lucide-react';
import { useSocket } from './SocketProvider';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { MOCK_PAYLOAD } from '../data/mock';

interface StatRowProps {
  label: string;
  homeValue: number | string;
  awayValue: number | string;
  homePercent: number; // 0-100 for the visual bar
  icon?: React.ReactNode;
}

function StatRow({ label, homeValue, awayValue, homePercent, icon }: StatRowProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-zinc-500 px-1">
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-white text-xs">{homeValue}</span>
        </div>
        <span>{label}</span>
        <span className="text-white text-xs">{awayValue}</span>
      </div>
      <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden flex gap-0.5">
        <div 
          className="h-full bg-primary transition-all duration-500" 
          style={{ width: `${Math.min(Math.max(homePercent, 0), 100)}%` }} 
        />
        <div 
          className="h-full bg-secondary transition-all duration-500" 
          style={{ width: `${Math.min(Math.max(100 - homePercent, 0), 100)}%` }} 
        />
      </div>
    </div>
  );
}

export function TraditionalStats() {
  const { data } = useSocket();
  const d = data ?? MOCK_PAYLOAD;

  const stats = [
    { 
      label: 'Expected Goals (xG)', 
      home: d.total_xg_team0, 
      away: d.total_xg_team1, 
      homePercent: (d.total_xg_team0 / (d.total_xg_team0 + d.total_xg_team1 + 0.1)) * 100, 
      icon: <Target className="w-3 h-3 text-primary" /> 
    },
    { 
      label: 'Possession', 
      home: `${d.possession.team0_pct}%`, 
      away: `${d.possession.team1_pct}%`, 
      homePercent: d.possession.team0_pct, 
      icon: <Users className="w-3 h-3 text-primary" /> 
    },
    { 
        label: 'Defensive Line (m)', 
        home: d.defensive_line_height_m.toFixed(1), 
        away: '-', 
        homePercent: (d.defensive_line_height_m / 105) * 100, 
        icon: <Shield className="w-3 h-3 text-primary" /> 
    },
    { 
        label: 'Attack Width (m)', 
        home: d.width_of_attack_m.toFixed(1), 
        away: '-', 
        homePercent: (d.width_of_attack_m / 68) * 100, 
        icon: <TrendingUp className="w-3 h-3 text-primary" /> 
    },
    { 
        label: 'Transition Speed (s)', 
        home: d.transition_speed_s.toFixed(1), 
        away: '-', 
        homePercent: (1 - d.transition_speed_s / 15) * 100, 
        icon: <Zap className="w-3 h-3 text-primary" /> 
    },
  ];

  return (
    <Card className="h-full border-border bg-card overflow-hidden flex flex-col">
      <CardHeader className="p-6 border-b border-border flex flex-row items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <CardTitle className="text-xl font-black uppercase tracking-tight text-foreground italic">Match Stats</CardTitle>
            {data && <Badge className="bg-green-500/10 text-green-500 border-green-500/20 text-[8px] font-black h-5 uppercase tracking-tighter">Live Feed</Badge>}
            {!data && <Badge variant="outline" className="border-border text-muted-foreground font-black uppercase text-[9px]">Mock Data</Badge>}
          </div>
          <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
            {data?.possession.team0_name ?? "Home"} vs {data?.possession.team1_name ?? "Away"}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-primary rounded-full" />
            <span className="text-[10px] font-black text-foreground/80 uppercase">Home</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-secondary rounded-full" />
            <span className="text-[10px] font-black text-foreground/80 uppercase">Away</span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-6 space-y-8 overflow-y-auto">
        <ScrollArea className="h-full w-full">
          <div className="space-y-8">
            {stats.map((stat) => (
              <StatRow 
                key={stat.label}
                label={stat.label}
                homeValue={stat.home}
                awayValue={stat.away}
                homePercent={stat.homePercent}
                icon={stat.icon}
              />
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}