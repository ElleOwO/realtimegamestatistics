"use client";

import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Target, Zap, Activity, Users, Shield, TrendingUp } from 'lucide-react';

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
      <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden flex gap-0.5">
        <div 
          className="h-full bg-emerald-500 transition-all duration-500" 
          style={{ width: `${homePercent}%` }} 
        />
        <div 
          className="h-full bg-zinc-600 transition-all duration-500" 
          style={{ width: `${100 - homePercent}%` }} 
        />
      </div>
    </div>
  );
}

export function TeamStatComparison() {
  const stats = [
    { label: 'Expected Goals (xG)', home: 1.84, away: 1.51, homePercent: 55, icon: <Target className="w-3 h-3 text-emerald-500" /> },
    { label: 'Total Shots', home: 18, away: 12, homePercent: 60, icon: <Zap className="w-3 h-3 text-emerald-500" /> },
    { label: 'Shots on Target', home: 12, away: 5, homePercent: 70, icon: <Activity className="w-3 h-3 text-emerald-500" /> },
    { label: 'Possession', home: '58%', away: '42%', homePercent: 58, icon: <Users className="w-3 h-3 text-emerald-500" /> },
    { label: 'Big Chances', home: 4, away: 2, homePercent: 66, icon: <TrendingUp className="w-3 h-3 text-emerald-500" /> },
    { label: 'Accurate Passes', home: 482, away: 315, homePercent: 60, icon: <Shield className="w-3 h-3 text-emerald-500" /> },
  ];

  return (
    <Card className="h-full border-zinc-800 bg-card overflow-hidden flex flex-col">
      <CardHeader className="p-6 border-b border-zinc-800 flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-xl font-black uppercase tracking-tight text-white italic">Tactical Comparison</CardTitle>
          <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Home (US) vs Away (Calgary)</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-emerald-500 rounded-full" />
            <span className="text-[10px] font-black text-zinc-300 uppercase">Home</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-zinc-600 rounded-full" />
            <span className="text-[10px] font-black text-zinc-300 uppercase">Away</span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-6 space-y-8 overflow-y-auto">
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
      </CardContent>
    </Card>
  );
}
