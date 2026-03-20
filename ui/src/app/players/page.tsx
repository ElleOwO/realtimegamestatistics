'use client';

import { MatchControl } from '../components/MatchControl';
import { PlayerPerformanceMatrix } from '../components/PlayerPerformanceMatrix';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Alert, AlertTitle, AlertDescription } from '../components/ui/alert';
import { AlertCircle, UserPlus, Timer, Zap } from 'lucide-react';
import { Button } from '../components/ui/button';

export default function PlayerStats() {
  return (
    <div className="mx-auto max-w-[1700px] space-y-6 pb-12">
      <MatchControl />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Main Performance Monitoring Area */}
        <div className="lg:col-span-8">
          <PlayerPerformanceMatrix />
        </div>

        {/* Actionable Bench & Sub Management */}
        <div className="lg:col-span-4 space-y-6">
          {/* Critical Fatigue Alerts */}
          <Card className="border-zinc-800 bg-zinc-900/30 shadow-lg">
            <CardHeader className="p-6 pb-2">
              <div className="flex items-center justify-between">
                 <div className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-zinc-100" />
                    <CardTitle className="text-lg font-black uppercase tracking-tight text-white">Sub Alerts</CardTitle>
                 </div>
                 <Badge className="bg-zinc-200 text-zinc-900 border-none text-[9px] font-black uppercase hover:bg-zinc-300">Critical</Badge>
              </div>
            </CardHeader>
            <CardContent className="p-6 pt-2 space-y-4">
               <Alert className="border-zinc-700 bg-zinc-900/50 rounded-2xl">
                 <div className="space-y-2">
                    <div className="flex justify-between items-center">
                       <span className="font-black text-sm uppercase text-white">#6 K. Walsh</span>
                       <span className="text-[10px] font-black text-zinc-300">85% FATIGUE</span>
                    </div>
                    <p className="text-xs text-zinc-400 leading-relaxed font-bold">
                      Movement speed dropped by 12% in last 10 mins. High risk of muscle strain.
                    </p>
                    <Button variant="outline" className="w-full mt-2 border-zinc-700 text-zinc-100 hover:bg-zinc-800 hover:text-white rounded-xl h-10 text-[10px] font-black uppercase tracking-widest">
                      Prepare #14 Stanway
                    </Button>
                 </div>
               </Alert>
            </CardContent>
          </Card>

          {/* Available Bench */}
          <Card className="border-zinc-800 bg-zinc-900/30 shadow-xl">
            <CardHeader className="p-6 pb-2 border-b border-zinc-800 flex flex-row items-center justify-between">
              <div className="flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-zinc-100" />
                <CardTitle className="text-lg font-black uppercase tracking-tight text-white">Ready Bench</CardTitle>
              </div>
              <Badge variant="outline" className="border-zinc-700 text-zinc-400 text-[9px] font-black uppercase">Warm Up Active</Badge>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-zinc-800">
                {[
                  { id: 14, name: 'G. Stanway', pos: 'MF', warm: 'High', energy: 100 },
                  { id: 19, name: 'B. Mead', pos: 'FW', warm: 'Mid', energy: 100 },
                  { id: 3, name: 'N. Charles', pos: 'DF', warm: 'Ready', energy: 100 },
                ].map((bench) => (
                  <div key={bench.id} className="p-4 flex items-center justify-between hover:bg-zinc-800/50 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center font-black text-zinc-300 text-xs">{bench.id}</div>
                      <div>
                        <div className="text-sm font-black text-white uppercase">{bench.name}</div>
                        <div className="text-[9px] font-bold text-zinc-500 uppercase">{bench.pos} • Energy {bench.energy}%</div>
                      </div>
                    </div>
                    <Badge className="bg-zinc-800 text-zinc-300 border-zinc-700 text-[9px] font-black uppercase hover:bg-zinc-700">{bench.warm}</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Squad Metrics Aggregator */}
          <div className="grid grid-cols-2 gap-4">
             <div className="p-4 rounded-3xl bg-zinc-900/30 border border-zinc-800">
                <div className="flex items-center gap-2 mb-2">
                   <Zap className="w-3 h-3 text-zinc-400" />
                   <span className="text-[9px] font-black uppercase text-zinc-500 tracking-tighter">Squad Energy</span>
                </div>
                <div className="text-2xl font-black text-white">74%</div>
             </div>
             <div className="p-4 rounded-3xl bg-zinc-900/30 border border-zinc-800">
                <div className="flex items-center gap-2 mb-2">
                   <Timer className="w-3 h-3 text-zinc-400" />
                   <span className="text-[9px] font-black uppercase text-zinc-500 tracking-tighter">Avg Load</span>
                </div>
                <div className="text-2xl font-black text-white">12.1 <span className="text-xs text-zinc-500">km</span></div>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
