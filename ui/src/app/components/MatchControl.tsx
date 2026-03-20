"use client";

import { Badge } from './ui/badge';
import { Card, CardContent } from './ui/card';
import { Clock, TrendingUp, Users, Target } from 'lucide-react';

export function MatchControl() {
  return (
    <Card className="border border-zinc-800 bg-card text-white shadow-xl rounded-none md:rounded-2xl overflow-hidden mb-6">
      <CardContent className="p-0">
        <div className="flex flex-col md:flex-row items-center divide-y md:divide-y-0 md:divide-x divide-zinc-800">
          {/* Main Scoreboard */}
          <div className="flex-1 flex items-center justify-between p-6 w-full">
            <div className="flex items-center gap-6">
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-zinc-100 text-zinc-900 flex items-center justify-center font-black text-xl mb-1 border border-zinc-300">US</div>
                <div className="text-[10px] font-black uppercase tracking-tighter text-zinc-500">U of S</div>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-5xl font-black tracking-tighter text-white">2</span>
                <span className="text-zinc-600 text-3xl font-light">-</span>
                <span className="text-5xl font-black tracking-tighter text-white">1</span>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-zinc-800 text-zinc-400 flex items-center justify-center font-black text-xl mb-1 border border-zinc-700">CG</div>
                <div className="text-[10px] font-black uppercase tracking-tighter text-zinc-500">Calgary</div>
              </div>
            </div>

            <div className="flex flex-col items-end">
              <div className="flex items-center gap-2 mb-1">
                <Clock className="w-4 h-4 text-zinc-300" />
                <span className="text-2xl font-mono font-black tracking-widest text-zinc-100">62:34</span>
              </div>
              <Badge className="bg-zinc-800 text-zinc-300 border-zinc-700 text-[10px] font-black uppercase">Second Half - Live</Badge>
            </div>
          </div>

          {/* Real-time Momentum */}
          <div className="flex-1 p-6 w-full bg-zinc-900/20">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-zinc-400" />
                <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Match Momentum</span>
              </div>
              <span className="text-xs font-black text-zinc-100">+12.4% Dominance</span>
            </div>
            <div className="flex h-2 w-full gap-1">
              <div className="flex-[62] bg-zinc-300 rounded-full" />
              <div className="flex-[38] bg-zinc-800 rounded-full" />
            </div>
            <div className="flex justify-between mt-2 text-[9px] font-bold uppercase text-zinc-500">
              <span>Home Dominance</span>
              <span>Away Threat</span>
            </div>
          </div>

          {/* Quick Stats Grid */}
          <div className="p-6 grid grid-cols-2 gap-x-8 gap-y-4 w-full md:w-auto min-w-[300px]">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-zinc-800/50 border border-zinc-700 rounded-lg">
                <Target className="w-4 h-4 text-zinc-300" />
              </div>
              <div>
                <div className="text-xs font-black tracking-tight text-zinc-100">1.84</div>
                <div className="text-[9px] font-bold uppercase text-zinc-500">Team xG</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-zinc-800/50 border border-zinc-700 rounded-lg">
                <Users className="w-4 h-4 text-zinc-300" />
              </div>
              <div>
                <div className="text-xs font-black tracking-tight text-zinc-100">8.4s</div>
                <div className="text-[9px] font-bold uppercase text-zinc-500">Regain Speed</div>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
