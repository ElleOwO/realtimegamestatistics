"use client";

import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { TrendingUp, TrendingDown, Minus, Zap, Target, Activity } from 'lucide-react';
import { ScrollArea } from './ui/scroll-area';

interface PlayerPerformance {
  id: number;
  name: string;
  position: string;
  rating: number; // 0-10
  trend: 'up' | 'down' | 'stable';
  fatigue: number; // 0-100
  impact: number; // 0-100 (match impact score)
  keyStat: string;
}

export function PlayerPerformanceMatrix() {
  const players: PlayerPerformance[] = [
    { id: 10, name: 'S. Hansen', position: 'FW', rating: 8.4, trend: 'up', fatigue: 65, impact: 92, keyStat: '2 Goals, 1 Assist' },
    { id: 7, name: 'M. Kerr', position: 'FW', rating: 7.2, trend: 'stable', fatigue: 30, impact: 65, keyStat: '5 Shots, 3 On Target' },
    { id: 6, name: 'K. Walsh', position: 'MF', rating: 9.1, trend: 'up', fatigue: 85, impact: 88, keyStat: '94% Pass Accuracy' },
    { id: 11, name: 'A. Hemp', position: 'MF', rating: 6.8, trend: 'down', fatigue: 72, impact: 45, keyStat: '12 Ball Recoveries' },
    { id: 4, name: 'M. Bright', position: 'DF', rating: 7.9, trend: 'stable', fatigue: 25, impact: 78, keyStat: '8 Interceptions' },
    { id: 8, name: 'L. Williamson', position: 'DF', rating: 8.2, trend: 'up', fatigue: 40, impact: 82, keyStat: '100% Aerial Duels Won' },
  ];

  const getTrendIcon = (trend: PlayerPerformance['trend']) => {
    switch (trend) {
      case 'up': return <TrendingUp className="w-4 h-4 text-zinc-300" />;
      case 'down': return <TrendingDown className="w-4 h-4 text-zinc-500" />;
      case 'stable': return <Minus className="w-4 h-4 text-zinc-600" />;
    }
  };

  return (
    <Card className="h-full flex flex-col border-zinc-800 shadow-xl bg-card backdrop-blur-sm">
      <CardHeader className="flex flex-row items-center justify-between p-6 pb-4 border-b border-zinc-800">
        <div className="flex items-center gap-3">
          <Activity className="w-6 h-6 text-zinc-100" />
          <div>
            <CardTitle className="text-xl font-black uppercase tracking-tight text-white">Performance Matrix</CardTitle>
            <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Real-time Squad Impact Analysis</p>
          </div>
        </div>
        <div className="flex gap-2">
           <Badge variant="outline" className="border-zinc-700 text-zinc-400 font-bold uppercase text-[9px]">LIVE UPDATING</Badge>
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-0 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="divide-y divide-zinc-800/50">
            {players.map((player) => (
              <div key={player.id} className="p-6 hover:bg-zinc-900/50 transition-colors group">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-zinc-900 border border-zinc-700 flex items-center justify-center font-black text-xl text-zinc-100 group-hover:border-zinc-500 transition-colors">
                      {player.id}
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-black text-lg text-white uppercase tracking-tight">{player.name}</span>
                        {getTrendIcon(player.trend)}
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge className="bg-zinc-800 text-zinc-300 border-zinc-700 text-[9px] font-black tracking-widest uppercase hover:bg-zinc-700">{player.position}</Badge>
                        <span className="text-[10px] font-bold text-zinc-500 uppercase">{player.keyStat}</span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-black text-zinc-100 tracking-tighter">{player.rating}</div>
                    <div className="text-[9px] font-black uppercase text-zinc-500 tracking-widest">Match Rating</div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-8">
                  <div className="space-y-2">
                    <div className="flex justify-between items-end">
                      <div className="flex items-center gap-2">
                        <Zap className={`w-3 h-3 ${player.fatigue > 75 ? 'text-zinc-100' : 'text-zinc-500'}`} />
                        <span className="text-[9px] font-black uppercase text-zinc-400 tracking-widest">Fatigue Level</span>
                      </div>
                      <span className={`text-[10px] font-black ${player.fatigue > 75 ? 'text-zinc-100' : 'text-zinc-300'}`}>{player.fatigue}%</span>
                    </div>
                    <Progress value={player.fatigue} className="h-1 bg-zinc-800" indicatorClassName={player.fatigue > 75 ? 'bg-zinc-100' : 'bg-zinc-400'} />
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between items-end">
                      <div className="flex items-center gap-2">
                        <Target className="w-3 h-3 text-zinc-300" />
                        <span className="text-[9px] font-black uppercase text-zinc-400 tracking-widest">Tactical Impact</span>
                      </div>
                      <span className="text-[10px] font-black text-zinc-100">{player.impact}%</span>
                    </div>
                    <Progress value={player.impact} className="h-1 bg-zinc-800" indicatorClassName="bg-zinc-300" />
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
