"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AnalyticsPayload } from "../../hooks/useAnalytics";
import { EmptyState, LiveBadge, Panel } from "./Panel";

interface TimelinePoint {
  minute: number;
  team0_xg: number;
  team1_xg: number;
}

/**
 * Cumulative xG race chart (part of ChatGPT's chance-quality category).
 * Data: reviewed and provisional shot events in the V2 payload.
 */
export function XgTimelineChart({
  data,
  teamNames,
}: {
  data: AnalyticsPayload | null;
  teamNames: [string, string];
}) {
  let team0 = 0;
  let team1 = 0;
  const timeline: TimelinePoint[] = [{ minute: 0, team0_xg: 0, team1_xg: 0 }];
  for (const shot of [...(data?.chance_quality.shots ?? [])].sort((a, b) => a.timestamp_ms - b.timestamp_ms)) {
    if (shot.team === "team0") team0 += shot.xg;
    else team1 += shot.xg;
    timeline.push({ minute: (shot.match_clock_s ?? shot.timestamp_ms / 1000) / 60, team0_xg: team0, team1_xg: team1 });
  }

  return (
    <Panel
      title="xG Timeline"
      badge={timeline.length > 1 ? <LiveBadge /> : undefined}
      className="h-full flex flex-col"
      bodyClassName="flex-1 min-h-0"
    >
      {timeline.length <= 1 ? (
        <EmptyState hint="Cumulative xG appears here after the first detected shot" />
      ) : (
        <div className="h-full min-h-36">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={timeline}
              margin={{ top: 4, right: 8, bottom: 0, left: -18 }}
            >
              <CartesianGrid stroke="#3b3b3b" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="minute"
                stroke="#a3a3a3"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(m: number) => `${Math.floor(m)}'`}
              />
              <YAxis
                stroke="#a3a3a3"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => v.toFixed(1)}
              />
              <Tooltip
                contentStyle={{
                  background: "#2f2f2f",
                  border: "1px solid #424242",
                  borderRadius: "0.75rem",
                  fontSize: 12,
                }}
                labelStyle={{ color: "#a3a3a3" }}
                formatter={(value, name) => [
                  typeof value === "number" ? value.toFixed(2) : value,
                  name === "team0_xg" ? teamNames[0] : teamNames[1],
                ]}
                labelFormatter={(m) => `${Math.floor(Number(m))}'`}
              />
              <Area
                type="stepAfter"
                dataKey="team0_xg"
                stroke="#0B6A41"
                fill="#0B6A41"
                fillOpacity={0.25}
                strokeWidth={2}
                isAnimationActive={false}
              />
              <Area
                type="stepAfter"
                dataKey="team1_xg"
                stroke="#DBCC52"
                fill="#DBCC52"
                fillOpacity={0.15}
                strokeWidth={2}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </Panel>
  );
}
