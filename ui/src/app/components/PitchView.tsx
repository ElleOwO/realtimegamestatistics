"use client";

import { useState } from 'react';
import { Card, CardContent } from './ui/card';
import { Switch } from './ui/switch';
import { Label } from './ui/label';
import { Map as MapIcon, Share2 } from 'lucide-react';

export function PitchView() {
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showPassing, setShowPassing] = useState(false);

  // Home Team (US) - Set up in a 4-3-3 formation
  const players = [
    { id: 1, x: 8, y: 30, position: 'GK' },
    { id: 2, x: 22, y: 12, position: 'LB' },
    { id: 3, x: 22, y: 48, position: 'RB' },
    { id: 4, x: 18, y: 24, position: 'CB' },
    { id: 5, x: 18, y: 36, position: 'CB' },
    { id: 6, x: 35, y: 30, position: 'CDM' },
    { id: 7, x: 45, y: 15, position: 'LCM' },
    { id: 8, x: 45, y: 45, position: 'RCM' },
    { id: 9, x: 55, y: 30, position: 'CAM' },
    { id: 10, x: 75, y: 15, position: 'LW' },
    { id: 11, x: 75, y: 45, position: 'RW' },
    { id: 12, x: 85, y: 30, position: 'ST' },
  ];

  // Passing pattern data (mock weights)
  const passes = [
    { from: 4, to: 6, weight: 3 },
    { from: 5, to: 6, weight: 2 },
    { from: 6, to: 9, weight: 4 },
    { from: 6, to: 7, weight: 2 },
    { from: 6, to: 8, weight: 2 },
    { from: 9, to: 10, weight: 3 },
    { from: 9, to: 11, weight: 3 },
    { from: 9, to: 12, weight: 5 },
    { from: 7, to: 10, weight: 2 },
    { from: 8, to: 11, weight: 2 },
    { from: 2, to: 7, weight: 1.5 },
    { from: 3, to: 8, weight: 1.5 },
  ];

  return (
    <Card className="h-full flex flex-col border-zinc-800 shadow-xl overflow-hidden bg-card">
      {/* NO HEADER - Full emphasis on the pitch */}
      <CardContent className="flex-1 p-0 relative flex flex-col">
        {/* Pitch Area */}
        <div className="flex-1 bg-[#051f14] p-6 lg:p-12 flex items-center justify-center relative">
          <div className="relative w-full max-w-5xl aspect-[100/60] bg-[#072a1b] rounded shadow-2xl border-2 border-emerald-900/50">
            {/* Pitch Markings */}
            <svg className="absolute inset-0 w-full h-full opacity-30 pointer-events-none" viewBox="0 0 100 60" preserveAspectRatio="none">
              <rect x="0" y="0" width="100" height="60" fill="none" stroke="#10b981" strokeWidth="0.2" />
              <line x1="50" y1="0" x2="50" y2="60" stroke="#10b981" strokeWidth="0.2" />
              <circle cx="50" cy="30" r="8" fill="none" stroke="#10b981" strokeWidth="0.2" />
              <rect x="0" y="15" width="16" height="30" fill="none" stroke="#10b981" strokeWidth="0.2" />
              <rect x="84" y="15" width="16" height="30" fill="none" stroke="#10b981" strokeWidth="0.2" />
              <rect x="0" y="24" width="6" height="12" fill="none" stroke="#10b981" strokeWidth="0.2" />
              <rect x="94" y="24" width="6" height="12" fill="none" stroke="#10b981" strokeWidth="0.2" />
            </svg>

            {/* Heatmap Overlay */}
            {showHeatmap && (
              <div className="absolute inset-0 pointer-events-none opacity-60">
                <div className="absolute top-[20%] left-[60%] w-32 h-32 bg-emerald-500/40 rounded-full blur-[40px]" />
                <div className="absolute top-[50%] left-[35%] w-40 h-40 bg-emerald-600/30 rounded-full blur-[50px]" />
                <div className="absolute top-[40%] left-[80%] w-24 h-24 bg-emerald-400/20 rounded-full blur-[30px]" />
              </div>
            )}

            {/* Tactical Overlays */}
            <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 60" preserveAspectRatio="none">
               {/* Passing Patterns */}
               {showPassing && passes.map((pass, i) => {
                 const p1 = players.find(p => p.id === pass.from);
                 const p2 = players.find(p => p.id === pass.to);
                 if (!p1 || !p2) return null;
                 return (
                   <line 
                     key={i} 
                     x1={p1.x} 
                     y1={p1.y} 
                     x2={p2.x} 
                     y2={p2.y} 
                     stroke="#10b981" 
                     strokeWidth={pass.weight * 0.08} 
                     strokeDasharray="0.5, 0.5"
                     opacity="0.6" 
                   />
                 )
               })}

               {/* Home Players ONLY */}
               {players.map(p => (
                 <g key={p.id}>
                    <circle cx={p.x} cy={p.y} r="1.5" fill="#10b981" stroke="#000" strokeWidth="0.1" />
                    <text x={p.x} y={p.y - 2.5} textAnchor="middle" fill="#ececec" fontSize="1.5" fontWeight="black" className="uppercase tracking-tighter opacity-90 drop-shadow-md">
                      {p.position}
                    </text>
                 </g>
               ))}
            </svg>
          </div>
        </div>

        {/* Bottom Control Bar */}
        <div className="h-16 md:h-20 border-t border-emerald-900/30 bg-[#03150d] px-6 md:px-10 flex items-center justify-between z-10 shrink-0">
          <div className="flex items-center gap-4">
            <div className="w-3 h-3 md:w-4 md:h-4 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.3)]" />
            <span className="text-xs md:text-sm font-black uppercase text-zinc-100 tracking-widest">U of S • 4-3-3 Shape</span>
          </div>
          
          <div className="flex items-center gap-6 md:gap-10">
            <div className="flex items-center gap-3">
               <Share2 className="w-4 h-4 md:w-5 md:h-5 text-emerald-500/80" />
               <Label htmlFor="passing" className="text-[10px] md:text-xs font-black uppercase text-zinc-300 tracking-widest cursor-pointer select-none">Passing Patterns</Label>
               <Switch id="passing" checked={showPassing} onCheckedChange={setShowPassing} className="data-[state=checked]:bg-emerald-600" />
            </div>
            <div className="w-px h-6 bg-emerald-900/50 hidden md:block" />
            <div className="flex items-center gap-3">
               <MapIcon className="w-4 h-4 md:w-5 md:h-5 text-emerald-500/80" />
               <Label htmlFor="heatmap" className="text-[10px] md:text-xs font-black uppercase text-zinc-300 tracking-widest cursor-pointer select-none">Heatmaps</Label>
               <Switch id="heatmap" checked={showHeatmap} onCheckedChange={setShowHeatmap} className="data-[state=checked]:bg-emerald-600" />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
