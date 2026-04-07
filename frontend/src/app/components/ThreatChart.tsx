"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { useSocket } from "./SocketProvider";
import { Badge } from "./ui/badge";
import { Target, Radar as RadarIcon } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./ui/tabs";
import { MOCK_PAYLOAD } from "../data/mock";

export function ThreatChart() {
  const { data } = useSocket();
  const d = data ?? MOCK_PAYLOAD;

  const zoneData = useMemo(() => {
    const t0 = d.zone_stats?.team0;
    const t1 = d.zone_stats?.team1;
    if (!t0 || !t1) return [];

    return [
      {
        zone: "Defensive 3rd",
        home: t0.defensive_third_count ?? 0,
        away: t1.defensive_third_count ?? 0,
      },
      {
        zone: "Middle 3rd",
        home: t0.middle_third_count ?? 0,
        away: t1.middle_third_count ?? 0,
      },
      {
        zone: "Attacking 3rd",
        home: t0.attacking_third_count ?? 0,
        away: t1.attacking_third_count ?? 0,
      },
    ];
  }, [d]);

  const radarData = useMemo(() => {
    const t0 = d.zone_stats?.team0;
    const t1 = d.zone_stats?.team1;
    if (!t0 || !t1) return [];

    return [
      {
        metric: "Left Wing",
        home: (t0.Q1_def_left ?? 0) + (t0.Q1_mid_left ?? 0) + (t0.Q1_atk_left ?? 0),
        away: (t1.Q1_def_left ?? 0) + (t1.Q1_mid_left ?? 0) + (t1.Q1_atk_left ?? 0),
      },
      {
        metric: "Left Half-Space",
        home: (t0.Q2_def_left ?? 0) + (t0.Q2_mid_left ?? 0) + (t0.Q2_atk_left ?? 0),
        away: (t1.Q2_def_left ?? 0) + (t1.Q2_mid_left ?? 0) + (t1.Q2_atk_left ?? 0),
      },
      {
        metric: "Central",
        home: (t0.Q3_def_central ?? 0) + (t0.Q3_mid_central ?? 0) + (t0.Q3_atk_central ?? 0),
        away: (t1.Q3_def_central ?? 0) + (t1.Q3_mid_central ?? 0) + (t1.Q3_atk_central ?? 0),
      },
      {
        metric: "Right Half-Space",
        home: (t0.Q4_def_right ?? 0) + (t0.Q4_mid_right ?? 0) + (t0.Q4_atk_right ?? 0),
        away: (t1.Q4_def_right ?? 0) + (t1.Q4_mid_right ?? 0) + (t1.Q4_atk_right ?? 0),
      },
      {
        metric: "Right Wing",
        home: (t0.Q5_def_right ?? 0) + (t0.Q5_mid_right ?? 0) + (t0.Q5_atk_right ?? 0),
        away: (t1.Q5_def_right ?? 0) + (t1.Q5_mid_right ?? 0) + (t1.Q5_atk_right ?? 0),
      },
    ];
  }, [d]);

  const shotThreat = useMemo(() => {
    const players = d.players ?? [];
    const team0Players = players.filter((p) => p.team === 0);
    const team1Players = players.filter((p) => p.team === 1);

    const calcXG = (team: typeof players) => {
      const totalXG = team.reduce((sum, p) => sum + (p.total_xg ?? 0), 0);
      const shots = team.reduce((sum, p) => sum + (p.shots ?? 0), 0);
      const shotsOnTarget = team.reduce(
        (sum, p) => sum + (p.shots_on_target ?? 0),
        0
      );
      return {
        totalXG: totalXG.toFixed(2),
        shots,
        shotsOnTarget,
        shotAccuracy: shots > 0 ? ((shotsOnTarget / shots) * 100).toFixed(0) : "0",
      };
    };

    return [
      { metric: "Total xG", home: calcXG(team0Players).totalXG, away: calcXG(team1Players).totalXG },
      { metric: "Shots", home: calcXG(team0Players).shots, away: calcXG(team1Players).shots },
      { metric: "On Target", home: calcXG(team0Players).shotsOnTarget, away: calcXG(team1Players).shotsOnTarget },
      { metric: "Shot Accuracy %", home: calcXG(team0Players).shotAccuracy, away: calcXG(team1Players).shotAccuracy },
    ];
  }, [d]);

  const team0Name = d.possession.team0_name;
  const team1Name = d.possession.team1_name;

  return (
    <Card className="h-full flex flex-col border-border bg-card overflow-hidden">
      <CardHeader className="p-6 border-b border-border flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-xl font-black uppercase tracking-tight text-foreground italic">
            Threat Analysis
          </CardTitle>
          <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
            Attacking zones & shot quality
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

      <CardContent className="flex-1 min-h-0 p-4">
        <Tabs defaultValue="zones" className="h-full flex flex-col">
          <TabsList className="grid w-full grid-cols-3 mb-4 bg-zinc-900">
            <TabsTrigger
              value="zones"
              className="text-[10px] font-black uppercase tracking-widest data-[state=active]:bg-zinc-800"
            >
              Zones
            </TabsTrigger>
            <TabsTrigger
              value="radar"
              className="text-[10px] font-black uppercase tracking-widest data-[state=active]:bg-zinc-800"
            >
              Shape
            </TabsTrigger>
            <TabsTrigger
              value="shots"
              className="text-[10px] font-black uppercase tracking-widest data-[state=active]:bg-zinc-800"
            >
              Shots
            </TabsTrigger>
          </TabsList>

          <TabsContent value="zones" className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={zoneData}
                margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--border)"
                  opacity={0.5}
                />
                <XAxis
                  dataKey="zone"
                  stroke="var(--muted-foreground)"
                  tick={{
                    fill: "var(--muted-foreground)",
                    fontSize: 9,
                    fontWeight: 900,
                  }}
                  axisLine={{ stroke: "var(--border)" }}
                />
                <YAxis
                  stroke="var(--muted-foreground)"
                  tick={{
                    fill: "var(--muted-foreground)",
                    fontSize: 10,
                    fontWeight: 900,
                  }}
                  axisLine={{ stroke: "var(--border)" }}
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
                />
                <Legend
                  wrapperStyle={{
                    color: "var(--foreground)",
                    fontSize: "11px",
                    fontWeight: 900,
                    textTransform: "uppercase",
                    paddingTop: "20px",
                  }}
                  iconType="circle"
                />
                <Bar
                  dataKey="home"
                  fill="var(--primary)"
                  name={team0Name}
                  radius={[4, 4, 0, 0]}
                  isAnimationActive={false}
                />
                <Bar
                  dataKey="away"
                  fill="var(--secondary)"
                  name={team1Name}
                  radius={[4, 4, 0, 0]}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          </TabsContent>

          <TabsContent value="radar" className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart
                data={radarData}
                margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
              >
                <PolarGrid stroke="var(--border)" opacity={0.5} />
                <PolarAngleAxis
                  dataKey="metric"
                  tick={{
                    fill: "var(--muted-foreground)",
                    fontSize: 9,
                    fontWeight: 900,
                  }}
                />
                <PolarRadiusAxis
                  tick={{
                    fill: "var(--muted-foreground)",
                    fontSize: 8,
                    fontWeight: 900,
                  }}
                  axisLine={{ stroke: "var(--border)" }}
                />
                <Radar
                  name={team0Name}
                  dataKey="home"
                  stroke="var(--primary)"
                  fill="var(--primary)"
                  fillOpacity={0.2}
                  strokeWidth={2}
                  isAnimationActive={false}
                />
                <Radar
                  name={team1Name}
                  dataKey="away"
                  stroke="var(--secondary)"
                  fill="var(--secondary)"
                  fillOpacity={0.2}
                  strokeWidth={2}
                  isAnimationActive={false}
                />
                <Legend
                  wrapperStyle={{
                    color: "var(--foreground)",
                    fontSize: "11px",
                    fontWeight: 900,
                    textTransform: "uppercase",
                  }}
                  iconType="circle"
                />
              </RadarChart>
            </ResponsiveContainer>
          </TabsContent>

          <TabsContent value="shots" className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={shotThreat}
                margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--border)"
                  opacity={0.5}
                />
                <XAxis
                  dataKey="metric"
                  stroke="var(--muted-foreground)"
                  tick={{
                    fill: "var(--muted-foreground)",
                    fontSize: 9,
                    fontWeight: 900,
                  }}
                  axisLine={{ stroke: "var(--border)" }}
                />
                <YAxis
                  stroke="var(--muted-foreground)"
                  tick={{
                    fill: "var(--muted-foreground)",
                    fontSize: 10,
                    fontWeight: 900,
                  }}
                  axisLine={{ stroke: "var(--border)" }}
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
                />
                <Legend
                  wrapperStyle={{
                    color: "var(--foreground)",
                    fontSize: "11px",
                    fontWeight: 900,
                    textTransform: "uppercase",
                    paddingTop: "20px",
                  }}
                  iconType="circle"
                />
                <Bar
                  dataKey="home"
                  fill="var(--primary)"
                  name={team0Name}
                  radius={[4, 4, 0, 0]}
                  isAnimationActive={false}
                />
                <Bar
                  dataKey="away"
                  fill="var(--secondary)"
                  name={team1Name}
                  radius={[4, 4, 0, 0]}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
