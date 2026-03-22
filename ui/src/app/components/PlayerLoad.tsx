"use client";

import { ScrollArea } from './ui/scroll-area';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Battery, Zap, Activity } from 'lucide-react';
import { Progress } from './ui/progress';
import { Badge } from './ui/badge';

interface PlayerLoadData {
  id: number;
  name: string;
  position: string;
  stamina: number; // 0-100
  sprints: number;
  distance: number; // in km
  status: 'optimal' | 'warning' | 'critical';
}

export function PlayerLoad() {
  const players: PlayerLoadData[] = [
    { id: 10, name: 'S. Hansen', position: 'FW', stamina: 42, sprints: 24, distance: 8.2, status: 'warning' },
    { id: 7, name: 'M. Kerr', position: 'FW', stamina: 85, sprints: 12, distance: 6.5, status: 'optimal' },
    { id: 8, name: 'L. Williamson', position: 'DF', stamina: 78, sprints: 8, distance: 7.1, status: 'optimal' },
    { id: 6, name: 'K. Walsh', position: 'MF', stamina: 35, sprints: 31, distance: 9.4, status: 'critical' },
    { id: 11, name: 'A. Hemp', position: 'MF', stamina: 62, sprints: 18, distance: 7.8, status: 'warning' },
    { id: 4, name: 'M. Bright', position: 'DF', stamina: 91, sprints: 5, distance: 5.9, status: 'optimal' },
  ];

  const getStatusColor = (status: PlayerLoadData['status']) => {
    switch (status) {
      case 'optimal': return 'bg-primary';
      case 'warning': return 'bg-secondary';
      case 'critical': return 'bg-muted-foreground';
    }
  };

  return (
    <Card className="h-full flex flex-col border-border shadow-lg bg-card">
      <CardHeader className="flex flex-row items-center justify-between p-6 border-b border-border">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-foreground" />
          <CardTitle className="text-xl font-black uppercase tracking-tight text-foreground italic">Squad Load</CardTitle>
        </div>
        <Badge variant="outline" className="text-[10px] text-muted-foreground border-border font-black uppercase tracking-widest">Live Biometrics</Badge>
      </CardHeader>

      <CardContent className="flex-1 p-6">
        <ScrollArea className="h-full pr-4">
          <div className="space-y-6">
            {players.map((player) => (
              <div key={player.id} className="space-y-3 group">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-black text-muted-foreground w-4 group-hover:text-primary transition-colors">{player.id}</span>
                    <span className="font-black text-sm uppercase text-foreground tracking-tight">{player.name}</span>
                    <Badge className="text-[9px] h-4 px-1.5 bg-muted text-muted-foreground border-border uppercase tracking-widest font-black hover:bg-muted/80">{player.position}</Badge>
                  </div>
                  <div className="flex items-center gap-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                    <div className="flex items-center gap-1.5">
                      <Zap className="w-3 h-3 text-muted-foreground group-hover:text-secondary transition-colors" />
                      {player.sprints} SPRINTS
                    </div>
                    <div>{player.distance}KM</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  <Battery className={`w-4 h-4 ${player.stamina < 40 ? 'text-secondary' : 'text-muted-foreground'}`} />
                  <div className="flex-1">
                    <div className="flex justify-between mb-1.5">
                      <span className="text-[9px] uppercase text-muted-foreground font-black tracking-widest">Stamina Reserve</span>
                      <span className={`text-[10px] font-black ${player.stamina < 40 ? 'text-secondary' : 'text-foreground/80'}`}>{player.stamina}%</span>
                    </div>
                    <Progress value={player.stamina} className="h-1.5 bg-muted" indicatorClassName={getStatusColor(player.status)} />
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
