"use client";

import { useSocket } from "./SocketProvider";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { AlertCircle, Info, CheckCircle2, TrendingUp, AlertTriangle } from "lucide-react";
import { ScrollArea } from "./ui/scroll-area";
import { useMemo } from "react";

export function LiveInsights() {
  const { data } = useSocket();
  
  // Base insights from backend if available
  const backendInsights = data?.insights || [];

  // Command Center Synthesis Engine (Client-Side)
  const syntheticInsights = useMemo(() => {
    const generated = [];

    // Fallback logic for demo/testing if data is null (using default mocked data in the UI)
    const fieldTilt = data?.field_tilt_pct ?? 62;
    const xgPerPoss = data?.xg_per_possession ?? 0.04;
    const ppda = data?.ppda ?? 8.5;
    const sprintDecay = data?.sprint_decay_pct ?? -12;
    const defLine = data?.defensive_line_height_m ?? 42.5;
    const verticalCompactness = data?.vertical_compactness_m ?? 34.5;

    // 1. Sterile Domination Check
    if (fieldTilt > 60 && xgPerPoss < 0.05 && ppda > 10) {
      generated.push({
        type: "warning",
        title: "Sterile Domination Detected",
        body: "High field tilt but low penetration. Opponent is resting in a low block. Recommend introducing a creative risk-taker or changing width.",
      });
    } else if (fieldTilt > 60 && xgPerPoss < 0.05) {
      generated.push({
        type: "warning",
        title: "Low Creativity in Final Third",
        body: "Dominating possession in attacking areas but struggling to create quality chances. Consider quicker ball circulation or overloads out wide.",
      });
    }

    // 2. Physical Load & Sprint Decay Check
    if (sprintDecay < -10) {
      generated.push({
        type: "critical",
        title: "High Sprint Decay Alert",
        body: "Significant drop in high-intensity sprints (-12%) over the last 10 minutes. Wide players are gassed. Consider tactical substitutions before defensive lapses occur.",
      });
    }

    // 3. Structural Integrity / Compactness Check
    if (verticalCompactness > 30) {
      generated.push({
        type: "warning",
        title: "Vertical Disconnection",
        body: `Distance between forwards and defensive line is ${verticalCompactness.toFixed(1)}m (Ideal: <30m). The midfield is becoming bypassed. Push the defensive line up or drop the #10.`,
      });
    }
    
    // 4. Successful Pressing / Positive Control Check
    if (ppda < 9 && fieldTilt > 55) {
      generated.push({
        type: "positive",
        title: "Suffocating Press",
        body: "Excellent counter-pressing. You are winning the ball back rapidly high up the pitch and sustaining attacks. Maintain current intensity.",
      });
    }

    return generated;
  }, [data]);

  // Combine and deduplicate
  const allInsights = [...syntheticInsights, ...backendInsights].slice(0, 5); // Keep top 5

  return (
    <Card className="h-full flex flex-col border-border bg-card overflow-hidden">
      <CardHeader className="p-4 md:p-6 border-b border-border bg-zinc-950/50">
        <CardTitle className="text-xl font-black uppercase tracking-tight text-foreground flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-primary" />
          Command Center Synthesis
        </CardTitle>
        <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
          AI-Generated Real-Time Directives
        </p>
      </CardHeader>
      
      <CardContent className="flex-1 min-h-0 p-0">
        <ScrollArea className="h-full px-4 py-4 md:px-6 md:py-4">
          {allInsights.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-zinc-500 gap-3">
              <Info className="w-8 h-8 opacity-50" />
              <p className="text-sm font-medium uppercase tracking-widest text-center">
                Analyzing tactical patterns...
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {allInsights.map((insight, idx) => {
                let colorClass = "bg-zinc-900 border-zinc-800 text-zinc-300";
                let Icon = Info;
                let bgGradient = "";
                
                if (insight.type === "critical") {
                  colorClass = "bg-red-500/10 border-red-500/50 text-red-200 shadow-[0_0_15px_rgba(239,68,68,0.2)]";
                  Icon = AlertTriangle;
                  bgGradient = "bg-gradient-to-r from-red-500/20 to-transparent";
                } else if (insight.type === "warning") {
                  colorClass = "bg-yellow-500/10 border-yellow-500/30 text-yellow-200";
                  Icon = AlertCircle;
                } else if (insight.type === "positive") {
                  colorClass = "bg-green-500/10 border-green-500/30 text-green-200";
                  Icon = CheckCircle2;
                } else if (insight.type === "info") {
                  colorClass = "bg-blue-500/10 border-blue-500/30 text-blue-200";
                  Icon = Info;
                }

                return (
                  <div 
                    key={idx} 
                    className={`relative flex items-start gap-4 p-4 rounded-xl border ${colorClass} transition-all hover:scale-[1.01] overflow-hidden`}
                  >
                    {bgGradient && <div className={`absolute inset-0 ${bgGradient} opacity-50`} />}
                    <div className="mt-1 relative z-10">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="relative z-10">
                      <h4 className="font-bold text-sm uppercase tracking-wide mb-1">
                        {insight.title}
                      </h4>
                      <p className="text-xs opacity-90 leading-relaxed font-serif">
                        {insight.body}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}