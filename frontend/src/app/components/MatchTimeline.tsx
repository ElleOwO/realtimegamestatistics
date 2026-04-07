"use client";

import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Trophy, AlertCircle, PlayCircle, Clock, ArrowDownUp } from 'lucide-react';
import { ScrollArea } from './ui/scroll-area';
import { useSocket } from './SocketProvider';
import { MOCK_PAYLOAD } from '../data/mock';

interface MatchEvent {
  minute: number;
  type: 'goal' | 'card' | 'sub' | 'chance';
  team: 'home' | 'away';
  title: string;
  description: string;
  xg?: number;
}

export function MatchTimeline() {
  const { data } = useSocket();
  const d = data ?? MOCK_PAYLOAD;

  const events: MatchEvent[] = (() => {
    if (d.key_events && d.key_events.length > 0) {
      return d.key_events.map((event: any) => ({
        minute: event.minute ?? 0,
        type: event.type ?? 'chance',
        team: event.team === 0 ? 'home' : 'away',
        title: event.title ?? 'Event',
        description: event.description ?? '',
        xg: event.xg,
      }));
    }
    return [];
  })();

  const matchClock = d.match_clock ?? 0;
  const minutes = Math.floor(matchClock / 60);
  const seconds = Math.floor(matchClock % 60);
  const clockDisplay = `${minutes}:${seconds.toString().padStart(2, '0')}`;

  const getEventIcon = (type: MatchEvent['type']) => {
    switch (type) {
      case 'goal': return <Trophy className="w-4 h-4 text-foreground" />;
      case 'card': return <div className="w-3 h-4 bg-secondary rounded-sm" />;
      case 'sub': return <ArrowDownUp className="w-4 h-4 text-muted-foreground" />;
      case 'chance': return <AlertCircle className="w-4 h-4 text-muted-foreground" />;
    }
  };

  return (
    <Card className="h-full border-border bg-card overflow-hidden flex flex-col">
      <CardHeader className="p-6 border-b border-border flex flex-row items-center justify-between">
        <div className="flex items-center gap-3">
          <Clock className="w-6 h-6 text-foreground" />
          <div>
            <CardTitle className="text-xl font-black uppercase tracking-tight text-foreground">Live Match Timeline</CardTitle>
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Key Tactical Moments</p>
          </div>
        </div>
        {data
          ? <Badge className="bg-green-500/10 text-green-500 border-green-500/20 text-[8px] font-black h-5 uppercase tracking-tighter">{clockDisplay} ELAPSED</Badge>
          : <Badge variant="outline" className="border-border text-muted-foreground font-black uppercase text-[9px]">Mock Data</Badge>
        }
      </CardHeader>

      <CardContent className="flex-1 p-0">
        <ScrollArea className="h-full">
          {events.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground text-sm font-bold uppercase tracking-widest">
              No events yet
            </div>
          ) : (
            <div className="p-6 space-y-8 relative">
              <div className="absolute left-[39px] top-6 bottom-6 w-px bg-border" />

              {events.map((event, index) => (
                <div key={index} className="flex gap-6 relative group">
                  <div className="w-8 flex-shrink-0 text-right">
                     <span className="text-sm font-black text-muted-foreground group-hover:text-foreground transition-colors">{event.minute}'</span>
                  </div>

                  <div className="relative flex items-center justify-center w-6 h-6 rounded-full bg-card border border-border z-10 group-hover:border-primary transition-colors ">
                     {getEventIcon(event.type)}
                  </div>

                  <div className="flex-1">
                     <div className={`p-4 rounded-2xl border transition-all ${event.type === 'goal' ? 'bg-muted/30 border-border' : 'bg-transparent border-transparent'} group-hover:bg-muted/50`}>
                        <div className="flex items-center justify-between mb-1">
                           <h4 className={`text-sm font-black uppercase tracking-tight ${event.team === 'home' ? 'text-primary' : 'text-secondary'}`}>
                             {event.title}
                           </h4>
                           {event.xg && (
                             <span className="text-[9px] font-black text-muted-foreground uppercase tracking-widest">xG: {event.xg}</span>
                           )}
                        </div>
                        <p className="text-xs text-muted-foreground font-bold leading-relaxed">{event.description}</p>
                     </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
