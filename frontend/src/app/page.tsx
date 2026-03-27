'use client';

import { PitchView } from './components/PitchView';
import { useSocket } from './components/SocketProvider';
import { Badge } from './components/ui/badge';
import { Wifi, WifiOff } from 'lucide-react';

export default function LiveDashboard() {
  const { data, isConnected } = useSocket();

  return (
    <div className="mx-auto max-w-[1700px] h-[calc(100vh-80px)] lg:h-[calc(100vh-120px)] flex flex-col items-center justify-center relative">
      <div className="absolute top-4 right-4 z-50 flex items-center gap-2">
        <Badge variant={isConnected ? "default" : "destructive"} className="gap-1.5 py-1 px-3">
          {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
          <span className="text-[10px] font-black uppercase tracking-widest">
            {isConnected ? "Live Feed Active" : "Searching for Stream..."}
          </span>
        </Badge>
        {data && (
          <Badge variant="outline" className="py-1 px-3 border-border bg-card">
            <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
              Frame: {data.frame_id}
            </span>
          </Badge>
        )}
      </div>
      
      <div className="w-full h-full">
        <PitchView />
      </div>
    </div>
  );
}
