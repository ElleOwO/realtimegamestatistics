"use client";

import { TraditionalStats } from "../components/TraditionalStats";
import { TeamStatComparison } from "../components/TeamStatComparison";
import { XGChart } from "../components/XGChart";
import { MatchTimeline } from "../components/MatchTimeline";
import { PlayerStatsTable } from "../components/PlayerStatsTable";

export default function MatchReports() {
  return (
    <div className="w-full h-full flex flex-col font-sans gap-6 p-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[40vh] min-h-[350px]">
        <TraditionalStats />
        <TeamStatComparison />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[45vh] min-h-[400px]">
        <XGChart />
        <MatchTimeline />
      </div>
      <div className="h-[50vh] min-h-[400px]">
        <PlayerStatsTable />
      </div>
    </div>
  );
}
