"use client";

import { PlayerPerformanceMatrix } from "../components/PlayerPerformanceMatrix";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import {
  AlertCircle,
  UserPlus,
  Timer,
  Zap,
  ArrowRightLeft,
} from "lucide-react";
import { Button } from "../components/ui/button";

const substitutionRecommendations = [
  {
    id: "rec-1",
    outgoing: {
      name: "K. Walsh",
      id: 6,
      fatigue: 85,
      reason: "Movement speed dropped by 12%.",
    },
    incoming: { name: "G. Stanway", id: 14, warmUp: "High" },
  },
  {
    id: "rec-2",
    outgoing: {
      name: "L. Hemp",
      id: 11,
      fatigue: 78,
      reason: "Sprint recovery time increasing.",
    },
    incoming: { name: "B. Mead", id: 19, warmUp: "Ready" },
  },
];

export default function PlayerStats() {
  return (
    <div className="mx-auto max-w-[1700px] space-y-6 pb-12">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Main Performance Monitoring Area */}
        <div className="lg:col-span-8">
          <PlayerPerformanceMatrix />
        </div>

        {/* Actionable Bench & Sub Management */}
        <div className="lg:col-span-4 space-y-6">
          {/* Sub Recommendations */}
          <Card className="border-zinc-800 ">
            <CardHeader className="p-6 pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ArrowRightLeft className="w-5 h-5 text-emerald-500" />
                  <CardTitle className="text-lg font-black uppercase tracking-tight text-white">
                    Sub Recommendations
                  </CardTitle>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-6 pt-2 space-y-4">
              {substitutionRecommendations.map((rec) => (
                <div
                  key={rec.id}
                  className="bg-background border border-zinc-800 rounded-2xl p-4 space-y-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex flex-col items-center">
                        <span className="text-[10px] font-black text-zinc-500 uppercase">
                          OUT
                        </span>
                        <div className="w-8 h-8 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center font-black text-zinc-100 text-xs mt-1">
                          {rec.outgoing.id}
                        </div>
                      </div>
                      <ArrowRightLeft className="w-4 h-4 text-zinc-600 mt-4" />
                      <div className="flex flex-col items-center">
                        <span className="text-[10px] font-black text-zinc-500 uppercase">
                          IN
                        </span>
                        <div className="w-8 h-8 rounded-lg bg-emerald-900/30 border border-emerald-800/50 flex items-center justify-center font-black text-emerald-500 text-xs mt-1">
                          {rec.incoming.id}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-black text-white uppercase">
                        {rec.outgoing.name} → {rec.incoming.name}
                      </div>
                      <div className="text-[9px] font-bold text-red-500 uppercase mt-0.5">
                        {rec.outgoing.fatigue}% Fatigue
                      </div>
                    </div>
                  </div>

                  <p className="text-xs text-zinc-400 font-bold leading-tight">
                    {rec.outgoing.reason}
                  </p>

                  <Button
                    variant="outline"
                    className="w-full border-zinc-700 text-zinc-100 hover:bg-zinc-800 hover:text-white rounded-xl h-10 text-[10px] font-black uppercase tracking-widest"
                  >
                    Authorize Substitution
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Available Bench */}
          <Card className="border-zinc-800">
            <CardHeader className="p-6 pb-2 border-b border-zinc-800 flex flex-row items-center justify-between">
              <div className="flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-zinc-100" />
                <CardTitle className="text-lg font-black uppercase tracking-tight text-white">
                  Ready Bench
                </CardTitle>
              </div>
              <Badge
                variant="outline"
                className="border-zinc-700 text-zinc-400 text-[9px] font-black uppercase"
              >
                Warm Up Active
              </Badge>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-zinc-800">
                {[
                  {
                    id: 14,
                    name: "G. Stanway",
                    pos: "MF",
                    warm: "High",
                    energy: 100,
                  },
                  {
                    id: 19,
                    name: "B. Mead",
                    pos: "FW",
                    warm: "Ready",
                    energy: 100,
                  },
                  {
                    id: 3,
                    name: "N. Charles",
                    pos: "DF",
                    warm: "Ready",
                    energy: 100,
                  },
                ].map((bench) => (
                  <div
                    key={bench.id}
                    className="p-4 flex items-center justify-between hover:bg-zinc-800/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center font-black text-zinc-300 text-xs">
                        {bench.id}
                      </div>
                      <div>
                        <div className="text-sm font-black text-white uppercase">
                          {bench.name}
                        </div>
                        <div className="text-[9px] font-bold text-zinc-500 uppercase">
                          {bench.pos} • Energy {bench.energy}%
                        </div>
                      </div>
                    </div>
                    <Badge className="bg-zinc-800 text-zinc-300 border-zinc-700 text-[9px] font-black uppercase">
                      {bench.warm}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Squad Metrics Aggregator */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-3xl bg-card border border-zinc-800">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="w-3 h-3 text-zinc-400" />
                <span className="text-[9px] font-black uppercase text-zinc-500 tracking-tighter">
                  Squad Energy
                </span>
              </div>
              <div className="text-2xl font-black text-white">74%</div>
            </div>
            <div className="p-4 rounded-3xl bg-card border border-zinc-800">
              <div className="flex items-center gap-2 mb-2">
                <Timer className="w-3 h-3 text-zinc-400" />
                <span className="text-[9px] font-black uppercase text-zinc-500 tracking-tighter">
                  Avg Load
                </span>
              </div>
              <div className="text-2xl font-black text-white">
                12.1 <span className="text-xs text-zinc-500">km</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
