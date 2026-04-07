"use client";

import { PitchView } from "./components/PitchView";
import { useState } from "react";
import { Users, Activity, Grid3X3, GitBranch, Target } from "lucide-react";

export default function LiveDashboard() {
  const [showPlayers, setShowPlayers] = useState(true);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showZones, setShowZones] = useState(false);
  const [showPassing, setShowPassing] = useState(false);
  const [showBall, setShowBall] = useState(true);

  return (
    <div className="w-full h-full flex flex-col font-sans gap-3">
      {/* Pitch + Scoreboard overlay */}
      <div className="flex-1 min-h-0 relative overflow-hidden ">
        <PitchView
          showPlayers={showPlayers}
          showHeatmap={showHeatmap}
          showZones={showZones}
          showPassing={showPassing}
          showBall={showBall}
        />
      </div>

      {/* Control bar below pitch */}
      <div className="flex items-center justify-center gap-2 p-2 ">
        <ToggleBtn
          active={showPlayers}
          onClick={() => setShowPlayers(!showPlayers)}
          icon={<Users className="w-3.5 h-3.5" />}
          label="Players"
        />
        <ToggleBtn
          active={showBall}
          onClick={() => setShowBall(!showBall)}
          icon={<Target className="w-3.5 h-3.5" />}
          label="Ball"
        />
        <ToggleBtn
          active={showHeatmap}
          onClick={() => setShowHeatmap(!showHeatmap)}
          icon={<Activity className="w-3.5 h-3.5" />}
          label="Heatmap"
        />
        <ToggleBtn
          active={showZones}
          onClick={() => setShowZones(!showZones)}
          icon={<Grid3X3 className="w-3.5 h-3.5" />}
          label="Zones"
        />
        <ToggleBtn
          active={showPassing}
          onClick={() => setShowPassing(!showPassing)}
          icon={<GitBranch className="w-3.5 h-3.5" />}
          label="Passing"
        />
      </div>
    </div>
  );
}

function ToggleBtn({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest border transition-all ${
        active
          ? "bg-primary/15 text-primary border-primary/30"
          : "bg-transparent text-muted-foreground border-zinc-800 hover:text-foreground hover:border-zinc-700"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
