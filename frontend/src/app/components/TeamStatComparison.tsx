"use client";

import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import {
  Target,
  Zap,
  Activity,
  Users,
  Shield,
  TrendingUp,
  Compass,
  HeartPulse,
  Swords,
  FastForward,
} from "lucide-react";
import { useSocket } from "./SocketProvider";
import { Badge } from "./ui/badge";
import { ScrollArea } from "./ui/scroll-area";
import { useMemo } from "react";

interface StatRowProps {
  label: string;
  homeValue: number | string;
  awayValue: number | string;
  homePercent: number;
  icon?: React.ReactNode;
}

function StatRow({
  label,
  homeValue,
  awayValue,
  homePercent,
  icon,
}: StatRowProps) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-zinc-500 px-1">
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-white text-xs">{homeValue}</span>
        </div>
        <span>{label}</span>
        <span className="text-white text-xs">{awayValue}</span>
      </div>
      <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden flex gap-0.5">
        <div
          className="h-full bg-primary transition-all duration-500"
          style={{ width: `${Math.min(Math.max(homePercent, 0), 100)}%` }}
        />
        <div
          className="h-full bg-secondary transition-all duration-500"
          style={{ width: `${Math.min(Math.max(100 - homePercent, 0), 100)}%` }}
        />
      </div>
    </div>
  );
}

import { MOCK_PAYLOAD } from "../data/mock";

export function TeamStatComparison() {
  const { data } = useSocket();
  const d = data ?? MOCK_PAYLOAD;

  const derived = useMemo(() => {
    if (!d) return null;

    const players0 = d.players.filter((p) => p.team === 0);
    const players1 = d.players.filter((p) => p.team === 1);

    const verticalCompactness = (players: typeof d.players) => {
      if (players.length === 0) return null;
      const ys = players.map((p) => p.y_m);
      return Math.max(...ys) - Math.min(...ys);
    };

    const explosiveDistance = (players: typeof d.players) => {
      return players.reduce(
        (sum, p) => sum + (p.sprint_distance_km ?? 0) * 1000,
        0,
      );
    };

    const totalSprintCount = (players: typeof d.players) => {
      return players.reduce((sum, p) => sum + (p.sprint_count ?? 0), 0);
    };

    const totalDistanceM = (players: typeof d.players) => {
      return players.reduce((sum, p) => sum + (p.distance_km ?? 0) * 1000, 0);
    };

    const xgPerPossession = (totalXg: number, possessionPct: number) => {
      if (possessionPct === 0) return 0;
      return totalXg / possessionPct;
    };

    const fieldTiltFromZones = () => {
      const t0 = d.zone_stats?.team0;
      const t1 = d.zone_stats?.team1;
      if (!t0 || !t1) return null;
      const t0Atk =
        (t0.attacking_third_count ?? 0) +
        (t0.Q2_atk_left ?? 0) +
        (t0.Q4_atk_right ?? 0);
      const t1Atk =
        (t1.attacking_third_count ?? 0) +
        (t1.Q2_atk_left ?? 0) +
        (t1.Q4_atk_right ?? 0);
      const total = t0Atk + t1Atk;
      if (total === 0) return null;
      return Math.round((t0Atk / total) * 100);
    };

    const vc0 = verticalCompactness(players0);
    const vc1 = verticalCompactness(players1);
    const expDist0 = explosiveDistance(players0);
    const expDist1 = explosiveDistance(players1);
    const sprint0 = totalSprintCount(players0);
    const sprint1 = totalSprintCount(players1);
    const dist0 = totalDistanceM(players0);
    const dist1 = totalDistanceM(players1);
    const xgPerPoss0 = xgPerPossession(
      d.total_xg_team0,
      d.possession.team0_pct,
    );
    const xgPerPoss1 = xgPerPossession(
      d.total_xg_team1,
      d.possession.team1_pct,
    );
    const fieldTilt = fieldTiltFromZones();

    return {
      vc0,
      vc1,
      expDist0,
      expDist1,
      sprint0,
      sprint1,
      dist0,
      dist1,
      xgPerPoss0,
      xgPerPoss1,
      fieldTilt,
    };
  }, [d]);

  const fieldTiltVal = derived?.fieldTilt ?? data?.field_tilt_pct ?? null;
  const fieldTiltHome = fieldTiltVal ?? 50;
  const fieldTiltAway = fieldTiltVal != null ? 100 - fieldTiltVal : 50;

  const vcHome = derived?.vc0 ?? data?.vertical_compactness_m ?? null;
  const vcAway = derived?.vc1 ?? null;

  const xgPerPossHome = derived?.xgPerPoss0 ?? data?.xg_per_possession ?? null;
  const xgPerPossAway = derived?.xgPerPoss1 ?? null;

  const expDistHome = derived?.expDist0 ?? data?.explosive_distance_m ?? null;
  const expDistAway = derived?.expDist1 ?? null;

  const territorialStats = [
    {
      label: "Field Tilt (%)",
      home: fieldTiltVal != null ? fieldTiltVal : "—",
      away: fieldTiltVal != null ? fieldTiltAway : "—",
      homePercent: fieldTiltHome,
      icon: <Compass className="w-3 h-3 text-primary" />,
    },
    {
      label: "Deep Completions",
      home: d.deep_completions ?? "—",
      away: "—",
      homePercent: d.deep_completions
        ? Math.min((d.deep_completions / 20) * 100, 100)
        : 50,
      icon: <Target className="w-3 h-3 text-primary" />,
    },
    {
      label: "Vert. Compactness (m)",
      home: vcHome != null ? vcHome.toFixed(1) : "—",
      away: vcAway != null ? vcAway.toFixed(1) : "—",
      homePercent:
        vcHome != null && vcAway != null
          ? (vcHome / (vcHome + vcAway)) * 100
          : 50,
      icon: <Activity className="w-3 h-3 text-primary" />,
    },
  ];

  const creativeStats = [
    {
      label: "xG / Possession",
      home: xgPerPossHome != null ? xgPerPossHome.toFixed(3) : "—",
      away: xgPerPossAway != null ? xgPerPossAway.toFixed(3) : "—",
      homePercent:
        xgPerPossHome != null && xgPerPossAway != null
          ? (xgPerPossHome / (xgPerPossHome + xgPerPossAway + 0.001)) * 100
          : 50,
      icon: <Zap className="w-3 h-3 text-primary" />,
    },
    {
      label: "PPDA (Pressing)",
      home: d.ppda ?? "—",
      away: "—",
      homePercent: d.ppda != null ? Math.min((d.ppda / 20) * 100, 100) : 50,
      icon: <Swords className="w-3 h-3 text-primary" />,
    },
    {
      label: "Packing Rate",
      home: d.packing_rate ?? "—",
      away: "—",
      homePercent: d.packing_rate != null
        ? Math.min((d.packing_rate / 60) * 100, 100)
        : 50,
      icon: <Users className="w-3 h-3 text-primary" />,
    },
  ];

  const defensiveStats = [
    {
      label: "Att. 3rd Recoveries",
      home: d.attacking_third_recoveries ?? "—",
      away: "—",
      homePercent: d.attacking_third_recoveries != null
        ? Math.min((d.attacking_third_recoveries / 10) * 100, 100)
        : 50,
      icon: <Shield className="w-3 h-3 text-primary" />,
    },
    {
      label: "Def. Line Height (m)",
      home: d.defensive_line_height_m?.toFixed(1) ?? "—",
      away: "—",
      homePercent: (d.defensive_line_height_m / 105) * 100,
      icon: <TrendingUp className="w-3 h-3 text-primary" />,
    },
    {
      label: "Counter Threat",
      home: d.counter_attack_threat_score ?? "—",
      away: "—",
      homePercent: d.counter_attack_threat_score != null
        ? Math.min((d.counter_attack_threat_score / 10) * 100, 100)
        : 50,
      icon: <FastForward className="w-3 h-3 text-primary" />,
    },
  ];

  const physicalStats = [
    {
      label: "Total Distance (m)",
      home: derived?.dist0 != null ? Math.round(derived.dist0) : "—",
      away: derived?.dist1 != null ? Math.round(derived.dist1) : "—",
      homePercent:
        derived?.dist0 != null && derived?.dist1 != null
          ? (derived.dist0 / (derived.dist0 + derived.dist1)) * 100
          : 50,
      icon: <HeartPulse className="w-3 h-3 text-primary" />,
    },
    {
      label: "Explosive Dist (m)",
      home: expDistHome != null ? Math.round(expDistHome) : "—",
      away: expDistAway != null ? Math.round(expDistAway) : "—",
      homePercent:
        expDistHome != null && expDistAway != null
          ? (expDistHome / (expDistHome + expDistAway + 1)) * 100
          : 50,
      icon: <Zap className="w-3 h-3 text-primary" />,
    },
    {
      label: "Sprint Count",
      home: derived?.sprint0 ?? "—",
      away: derived?.sprint1 ?? "—",
      homePercent:
        derived?.sprint0 != null && derived?.sprint1 != null
          ? (derived.sprint0 / (derived.sprint0 + derived.sprint1 + 1)) * 100
          : 50,
      icon: <Activity className="w-3 h-3 text-primary" />,
    },
  ];

  return (
    <Card className="h-full border-border bg-card overflow-hidden flex flex-col">
      <CardHeader className="p-4 md:p-6 border-b border-border flex flex-row items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <CardTitle className="text-xl font-black uppercase tracking-tight text-foreground italic">
              Dynamic Metrics
            </CardTitle>
            {data ? (
              <Badge className="bg-green-500/10 text-green-500 border-green-500/20 text-[8px] font-black h-5 uppercase tracking-tighter">
                Live Feed
              </Badge>
            ) : (
              <Badge variant="outline" className="border-border text-muted-foreground font-black uppercase text-[9px]">
                Mock Data
              </Badge>
            )}
          </div>
          <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
            {d.possession.team0_name} vs{" "}
            {d.possession.team1_name}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-primary rounded-full" />
            <span className="text-[10px] font-black text-foreground/80 uppercase">
              Home
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-secondary rounded-full" />
            <span className="text-[10px] font-black text-foreground/80 uppercase">
              Away
            </span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-0 overflow-hidden">
        <ScrollArea className="h-full w-full">
          <div className="p-4 md:p-6 grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-10">
            <div className="space-y-4">
              <h3 className="text-xs font-black uppercase tracking-widest text-primary border-b border-zinc-800 pb-2 flex items-center gap-2">
                <Compass className="w-4 h-4" /> Advanced Possesion{" "}
              </h3>
              <div className="space-y-4">
                {territorialStats.map((stat) => (
                  <StatRow
                    key={stat.label}
                    label={stat.label}
                    homeValue={stat.home}
                    awayValue={stat.away}
                    homePercent={stat.homePercent}
                    icon={stat.icon}
                  />
                ))}
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="text-xs font-black uppercase tracking-widest text-blue-400 border-b border-zinc-800 pb-2 flex items-center gap-2">
                <Zap className="w-4 h-4" /> Chance Creation
              </h3>
              <div className="space-y-4">
                {creativeStats.map((stat) => (
                  <StatRow
                    key={stat.label}
                    label={stat.label}
                    homeValue={stat.home}
                    awayValue={stat.away}
                    homePercent={stat.homePercent}
                    icon={stat.icon}
                  />
                ))}
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="text-xs font-black uppercase tracking-widest text-red-400 border-b border-zinc-800 pb-2 flex items-center gap-2">
                <Shield className="w-4 h-4" /> Def & Transition
              </h3>
              <div className="space-y-4">
                {defensiveStats.map((stat) => (
                  <StatRow
                    key={stat.label}
                    label={stat.label}
                    homeValue={stat.home}
                    awayValue={stat.away}
                    homePercent={stat.homePercent}
                    icon={stat.icon}
                  />
                ))}
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="text-xs font-black uppercase tracking-widest text-yellow-500 border-b border-zinc-800 pb-2 flex items-center gap-2">
                <HeartPulse className="w-4 h-4" /> Fitness
              </h3>
              <div className="space-y-4">
                {physicalStats.map((stat) => (
                  <StatRow
                    key={stat.label}
                    label={stat.label}
                    homeValue={stat.home}
                    awayValue={stat.away}
                    homePercent={stat.homePercent}
                    icon={stat.icon}
                  />
                ))}
              </div>
            </div>
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
