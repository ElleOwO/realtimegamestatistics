"use client";

import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Trophy, AlertCircle, PlayCircle, Clock } from 'lucide-react';
import { ScrollArea } from './ui/scroll-area';

interface MatchEvent {
  minute: number;
  type: 'goal' | 'card' | 'sub' | 'chance';
  team: 'home' | 'away';
  title: string;
  description: string;
  xg?: number;
}

export function MatchTimeline() {
  const events: MatchEvent[] = [
    { minute: 62, type: 'chance', team: 'home', title: 'Big Chance - Hansen', description: 'Shot from close range saved by keeper', xg: 0.45 },
    { minute: 58, type: 'card', team: 'home', title: 'Yellow Card - Walsh', description: 'Tactical foul to stop counter' },
    { minute: 51, type: 'goal', team: 'home', title: 'GOAL - Martinez', description: 'Long range strike from edge of box', xg: 0.12 },
    { minute: 45, type: 'sub', team: 'away', title: 'Substitution - Calgary', description: '#14 Off • #22 On' },
    { minute: 34, type: 'goal', team: 'away', title: 'GOAL - Calgary', description: 'Counter attack finished at back post', xg: 0.68 },
    { minute: 18, type: 'goal', team: 'home', title: 'GOAL - Williams', description: 'Header from corner kick', xg: 0.38 },
  ];

  const getEventIcon = (type: MatchEvent['type'], team: MatchEvent['team']) => {
    switch (type) {
      case 'goal': return <Trophy className="w-4 h-4 text-zinc-100" />;
      case 'card': return <div className="w-3 h-4 bg-zinc-400 rounded-sm" />;
      case 'sub': return <PlayCircle className="w-4 h-4 text-zinc-400" />;
      case 'chance': return <AlertCircle className="w-4 h-4 text-zinc-300" />;
    }
  };

  return (
    <Card className="h-full border-zinc-800 shadow-xl bg-card overflow-hidden flex flex-col">
      <CardHeader className="p-6 border-b border-zinc-800 flex flex-row items-center justify-between">
        <div className="flex items-center gap-3">
          <Clock className="w-6 h-6 text-zinc-100" />
          <div>
            <CardTitle className="text-xl font-black uppercase tracking-tight text-white">Live Match Timeline</CardTitle>
            <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Key Tactical Moments</p>
          </div>
        </div>
        <Badge variant="outline" className="border-zinc-800 text-zinc-400 font-black uppercase text-[9px]">62:34 ELAPSED</Badge>
      </CardHeader>

      <CardContent className="flex-1 p-0">
        <ScrollArea className="h-full">
          <div className="p-6 space-y-8 relative">
            {/* Vertical Line */}
            <div className="absolute left-[39px] top-6 bottom-6 w-px bg-zinc-800" />

            {events.map((event, index) => (
              <div key={index} className="flex gap-6 relative group">
                <div className="w-8 flex-shrink-0 text-right">
                   <span className="text-sm font-black text-zinc-500 group-hover:text-zinc-300 transition-colors">{event.minute}'</span>
                </div>

                <div className="relative flex items-center justify-center w-6 h-6 rounded-full bg-zinc-900 border border-zinc-700 z-10 group-hover:border-zinc-500 transition-colors shadow-sm">
                   {getEventIcon(event.type, event.team)}
                </div>

                <div className="flex-1">
                   <div className={`p-4 rounded-2xl border transition-all ${event.type === 'goal' ? 'bg-zinc-900 border-zinc-700' : 'bg-transparent border-transparent'} group-hover:bg-zinc-800/50`}>
                      <div className="flex items-center justify-between mb-1">
                         <h4 className={`text-sm font-black uppercase tracking-tight ${event.team === 'home' ? 'text-white' : 'text-zinc-400'}`}>
                           {event.title}
                         </h4>
                         {event.xg && (
                           <span className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">xG: {event.xg}</span>
                         )}
                      </div>
                      <p className="text-xs text-zinc-500 font-bold leading-relaxed">{event.description}</p>
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
