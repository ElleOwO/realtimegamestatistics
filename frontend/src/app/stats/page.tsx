"use client";

import { TraditionalStats } from "../components/TraditionalStats";
import { TeamStatComparison } from "../components/TeamStatComparison";
import { XGChart } from "../components/XGChart";
import { MatchTimeline } from "../components/MatchTimeline";
import { PlayerStatsTable } from "../components/PlayerStatsTable";
import { FieldTiltChart } from "../components/FieldTiltChart";
import { ThreatChart } from "../components/ThreatChart";

export default function MatchReports() {
  return (
    <div className="w-full h-full flex flex-col font-sans gap-6 p-4">
      {/* Top row: Traditional stats + Team comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[40vh] min-h-[350px]">
        <TraditionalStats />
        <TeamStatComparison />
      </div>

      {/* Middle row: xG + Field Tilt + Threat */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[45vh] min-h-[400px]">
        <XGChart />
        <FieldTiltChart />
        <ThreatChart />
      </div>

      {/* Bottom: Player stats table */}
      <div className="h-[50vh] min-h-[400px]">
        <PlayerStatsTable />
      </div>

      {/* Full width: Match timeline */}
      <div className="h-[30vh] min-h-[250px]">
        <MatchTimeline />
      </div>
    </div>
  );
}
