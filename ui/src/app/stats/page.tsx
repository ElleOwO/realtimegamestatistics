'use client';

import { MatchControl } from '../components/MatchControl';
import { MatchTimeline } from '../components/MatchTimeline';
import { XGChart } from '../components/XGChart';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { FileText, Trophy, Target, TrendingUp, Users } from 'lucide-react';

export default function MatchReports() {
  return (
    <div className="mx-auto max-w-[1700px] space-y-6 pb-12">
      <MatchControl />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Performance Intelligence & Timeline */}
        <div className="lg:col-span-8 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-[450px]">
            <XGChart />
            <MatchTimeline />
          </div>

          <Card className="border-zinc-800 shadow-xl bg-card backdrop-blur-sm">
             <CardHeader className="p-6 border-b border-zinc-800 flex flex-row items-center gap-3">
                <FileText className="w-6 h-6 text-zinc-100" />
                <div>
                   <CardTitle className="text-xl font-black uppercase tracking-tight text-white">Post-Match Summary (Live Preview)</CardTitle>
                   <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Model-generated Intelligence</p>
                </div>
             </CardHeader>
             <CardContent className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-4">
                   <h4 className="text-xs font-black uppercase text-zinc-300 tracking-widest border-l-4 border-zinc-500 pl-3">Key Performance Indicators</h4>
                   <div className="space-y-4">
                      {[
                        ['Shots on Target', '12 / 18', 67],
                        ['Pass Completion', '82%', 82],
                        ['Tackles Won', '76%', 76],
                        ['Aerial Duels', '58%', 58],
                      ].map(([label, value, progress]) => (
                        <div key={label} className="space-y-1.5">
                          <div className="flex items-center justify-between text-[10px] font-black uppercase">
                            <span className="text-zinc-500">{label}</span>
                            <span className="text-white">{value}</span>
                          </div>
                          <Progress value={progress as number} className="h-1 bg-zinc-800" indicatorClassName="bg-zinc-300" />
                        </div>
                      ))}
                   </div>
                </div>
                
                <div className="space-y-4">
                   <h4 className="text-xs font-black uppercase text-zinc-300 tracking-widest border-l-4 border-zinc-700 pl-3">Critical Deficiencies</h4>
                   <div className="p-4 rounded-2xl bg-zinc-900/50 border border-zinc-800 space-y-3">
                      <div className="flex items-start gap-3">
                         <div className="w-2 h-2 rounded-full bg-zinc-600 mt-1" />
                         <p className="text-xs font-bold text-zinc-400 leading-relaxed">Transitions slowing significantly after 60'. Suggest endurance-focused training cycles.</p>
                      </div>
                      <div className="flex items-start gap-3">
                         <div className="w-2 h-2 rounded-full bg-zinc-600 mt-1" />
                         <p className="text-xs font-bold text-zinc-400 leading-relaxed">Opponent xG concentrated in right channel. Overload defense failed 4 times.</p>
                      </div>
                   </div>
                   <div className="pt-2">
                      <Badge className="bg-zinc-800 text-zinc-300 border-zinc-700 text-[9px] font-black uppercase px-2 py-1">Victory Probability: 84%</Badge>
                   </div>
                </div>
             </CardContent>
          </Card>
        </div>

        {/* Right: Box Score & Comparison */}
        <div className="lg:col-span-4 space-y-6">
           <Card className="border-zinc-800 shadow-xl bg-card backdrop-blur-sm">
              <CardHeader className="p-6 border-b border-zinc-800">
                 <CardTitle className="text-lg font-black uppercase tracking-tight text-white flex items-center gap-2">
                    <Trophy className="w-5 h-5 text-zinc-100" />
                    Detailed Box Score
                 </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                 <div className="divide-y divide-zinc-800">
                    {[
                      { icon: TrendingUp, label: 'Corners', home: '8', away: '4' },
                      { icon: Target, label: 'Offsides', home: '3', away: '5' },
                      { icon: Users, label: 'Fouls', home: '11', away: '14' },
                      { icon: Trophy, label: 'Saves', home: '6', away: '2' },
                    ].map((item) => (
                      <div key={item.label} className="p-6 flex items-center justify-between group hover:bg-zinc-900/50 transition-colors">
                        <div className="flex items-center gap-3">
                           <item.icon className="w-4 h-4 text-zinc-500 group-hover:text-zinc-300 transition-colors" />
                           <span className="text-[10px] font-black uppercase text-zinc-400 tracking-widest">{item.label}</span>
                        </div>
                        <div className="flex items-center gap-6">
                           <span className="text-sm font-black text-white">{item.home}</span>
                           <span className="text-[10px] font-bold text-zinc-700">VS</span>
                           <span className="text-sm font-black text-zinc-500">{item.away}</span>
                        </div>
                      </div>
                    ))}
                 </div>
              </CardContent>
           </Card>

           <Card className="border-zinc-800 bg-card shadow-lg p-6 rounded-3xl">
              <div className="flex items-center gap-4 mb-4">
                 <div className="w-12 h-12 rounded-2xl bg-zinc-200 flex items-center justify-center text-zinc-900">
                    <Trophy className="w-6 h-6" />
                 </div>
                 <div>
                    <h3 className="text-lg font-black uppercase tracking-tight text-white">Full Report Ready</h3>
                    <p className="text-[10px] font-bold text-zinc-500 uppercase">Export PDF / Video Clip Bundle</p>
                 </div>
              </div>
              <p className="text-xs text-zinc-400 leading-relaxed font-bold mb-6 italic">
                All match data has been synced to the team repository. Tactical review session scheduled for Monday 09:00.
              </p>
              <div className="grid grid-cols-2 gap-3">
                 <button className="h-10 rounded-xl bg-zinc-800 border border-zinc-700 text-[10px] font-black uppercase tracking-widest text-zinc-100 hover:bg-zinc-700 transition-colors">Export Data</button>
                 <button className="h-10 rounded-xl bg-zinc-200 text-zinc-900 text-[10px] font-black uppercase tracking-widest hover:bg-zinc-300 transition-colors">Bundle Video</button>
              </div>
           </Card>
        </div>
      </div>
    </div>
  );
}
