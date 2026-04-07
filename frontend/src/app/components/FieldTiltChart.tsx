"use client";

import { useMemo } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { useSocket } from "./SocketProvider";
import { Badge } from "./ui/badge";
import { Compass } from "lucide-react";
import { MOCK_PAYLOAD } from "../data/mock";

interface FieldTiltPoint {
  minute: number;
  home: number;
  away: number;
}

export function FieldTiltChart() {
  const { data } = useSocket();
  const d = data ?? MOCK_PAYLOAD;

  const chartData: FieldTiltPoint[] = useMemo(() => {
    const t0 = d.zone_stats?.team0;
    const t1 = d.zone_stats?.team1;
    if (!t0 || !t1) return [{ minute: 0, home: 50, away: 50 }];

    const t0Atk =
      (t0.attacking_third_count ?? 0) +
      (t0.Q2_atk_left ?? 0) +
      (t0.Q4_atk_right ?? 0);
    const t1Atk =
      (t1.attacking_third_count ?? 0) +
      (t1.Q2_atk_left ?? 0) +
      (t1.Q4_atk_right ?? 0);
    const total = t0Atk + t1Atk;
    if (total === 0) return [{ minute: 0, home: 50, away: 50 }];

    const homePct = Math.round((t0Atk / total) * 100);
    const matchMin = Math.floor(d.match_clock / 60);

    return [{ minute: matchMin, home: homePct, away: 100 - homePct }];
  }, [d]);

  const currentVal = chartData[chartData.length - 1];
  const homePct = currentVal?.home ?? 50;

  const team0Name = d.possession.team0_name;
  const team1Name = d.possession.team1_name;

  return (
    <Card className="h-full flex flex-col border-border bg-card overflow-hidden">
      <CardHeader className="p-6 border-b border-border flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-xl font-black uppercase tracking-tight text-foreground italic">
            Field Tilt
          </CardTitle>
          <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
            Territorial dominance in attacking third (%)
          </p>
        </div>
        {data ? (
          <Badge className="bg-green-500/10 text-green-500 border-green-500/20 text-[8px] font-black h-5 uppercase tracking-tighter">
            Live Feed
          </Badge>
        ) : (
          <Badge
            variant="outline"
            className="border-border text-muted-foreground font-black uppercase text-[9px]"
          >
            Mock Data
          </Badge>
        )}
      </CardHeader>

      <CardContent className="flex-1 min-h-0 p-6">
        <div className="flex items-center justify-around mb-4">
          <div className="text-center">
            <div className="text-3xl font-black text-primary">{homePct}%</div>
            <div className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest">
              {team0Name}
            </div>
          </div>
          <Compass className="w-5 h-5 text-muted-foreground opacity-30" />
          <div className="text-center">
            <div className="text-3xl font-black text-secondary">
              {100 - homePct}%
            </div>
            <div className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest">
              {team1Name}
            </div>
          </div>
        </div>

        <ResponsiveContainer width="100%" height="75%">
          <AreaChart
            data={chartData}
            margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              opacity={0.5}
            />
            <XAxis
              dataKey="minute"
              stroke="var(--muted-foreground)"
              tick={{
                fill: "var(--muted-foreground)",
                fontSize: 10,
                fontWeight: 900,
              }}
              axisLine={{ stroke: "var(--border)" }}
            />
            <YAxis
              domain={[0, 100]}
              ticks={[0, 25, 50, 75, 100]}
              stroke="var(--muted-foreground)"
              tick={{
                fill: "var(--muted-foreground)",
                fontSize: 10,
                fontWeight: 900,
              }}
              axisLine={{ stroke: "var(--border)" }}
              tickFormatter={(v) => `${v}%`}
            />
            <ReferenceLine
              y={50}
              stroke="var(--muted-foreground)"
              strokeDasharray="4 4"
              opacity={0.5}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--card)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
                color: "var(--foreground)",
                fontSize: "12px",
                fontWeight: 900,
                textTransform: "uppercase",
              }}
              formatter={(value: number) => `${value}%`}
            />
            <Area
              type="monotone"
              dataKey="home"
              stackId="1"
              stroke="var(--primary)"
              fill="var(--primary)"
              fillOpacity={0.2}
              strokeWidth={2}
              name={team0Name}
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="away"
              stackId="1"
              stroke="var(--secondary)"
              fill="var(--secondary)"
              fillOpacity={0.2}
              strokeWidth={2}
              name={team1Name}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
