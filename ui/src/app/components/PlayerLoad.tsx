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
      case 'optimal': return 'bg-zinc-300';
      case 'warning': return 'bg-zinc-500';
      case 'critical': return 'bg-zinc-700';
    }
  };

  return (
    <Card className="h-full flex flex-col border-zinc-800 shadow-lg bg-card">
      <CardHeader className="flex flex-row items-center justify-between p-4 pb-2 border-b border-zinc-800/50">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-zinc-100" />
          <CardTitle className="text-lg font-bold uppercase tracking-tight text-white">Player Load & Fatigue</CardTitle>
        </div>
        <Badge variant="outline" className="text-[10px] text-zinc-400 border-zinc-700">LIVE BIOMETRICS</Badge>
      </CardHeader>

      <CardContent className="flex-1 p-4 pt-4">
        <ScrollArea className="h-full pr-4">
          <div className="space-y-4">
            {players.map((player) => (
              <div key={player.id} className="space-y-2 group">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-black text-zinc-500 w-4 group-hover:text-zinc-300 transition-colors">{player.id}</span>
                    <span className="font-bold text-sm uppercase text-white">{player.name}</span>
                    <Badge variant="secondary" className="text-[9px] h-4 px-1 bg-zinc-800 text-zinc-300 hover:bg-zinc-700">{player.position}</Badge>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] font-medium text-zinc-400">
                    <div className="flex items-center gap-1">
                      <Zap className="w-3 h-3 text-zinc-500 group-hover:text-zinc-300 transition-colors" />
                      {player.sprints} Sprints
                    </div>
                    <div>{player.distance}km</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  <Battery className={`w-4 h-4 ${player.stamina < 40 ? 'text-zinc-100' : 'text-zinc-500'}`} />
                  <div className="flex-1">
                    <div className="flex justify-between mb-1">
                      <span className="text-[10px] uppercase text-zinc-500 font-bold">Stamina Reserve</span>
                      <span className={`text-[10px] font-black ${player.stamina < 40 ? 'text-zinc-100' : 'text-zinc-300'}`}>{player.stamina}%</span>
                    </div>
                    <Progress value={player.stamina} className="h-1.5 bg-zinc-800" indicatorClassName={getStatusColor(player.status)} />
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
