import { useState } from 'react';
import { Switch } from './ui/switch';
import { Label } from './ui/label';
import type { AnalyticsPlayer } from '../hooks/useAnalytics';

interface PitchViewProps {
  players?: AnalyticsPlayer[];
  ball?: [number, number] | null;
}

function toSvgX(xMeters: number): number {
  // Backend sends pitch coords in metres centered at (0,0); SVG uses 0..100.
  return ((xMeters + 52.5) / 105) * 100;
}

function toSvgY(yMeters: number): number {
  // Pitch width maps to SVG height of 60 units.
  return ((yMeters + 34) / 68) * 60;
}

export function PitchView({ players: livePlayers, ball }: PitchViewProps) {
  const [isHeatmap, setIsHeatmap] = useState(true);

  // Fallback positions keep the panel useful when live WS data is unavailable.
  const mockPlayers = [
    { id: 1, x: 15, y: 50, isDefender: true },
    { id: 2, x: 20, y: 25, isDefender: true },
    { id: 3, x: 20, y: 75, isDefender: true },
    { id: 4, x: 25, y: 40, isDefender: true },
    { id: 5, x: 25, y: 60, isDefender: true },
    { id: 6, x: 40, y: 35, isDefender: false },
    { id: 7, x: 40, y: 65, isDefender: false },
    { id: 8, x: 55, y: 50, isDefender: false },
    { id: 9, x: 65, y: 40, isDefender: false },
    { id: 10, x: 70, y: 55, isDefender: false },
  ];

  const players = livePlayers && livePlayers.length > 0
    ? livePlayers.map((p) => ({
        id: p.id,
        x: toSvgX(p.x_m),
        y: toSvgY(p.y_m),
        // Team 0 is currently treated as defensive unit in this visualization.
        isDefender: p.team === 0,
      }))
    : mockPlayers;

  const defenders = players.filter((p) => p.isDefender);

  const ballPoint = ball
    ? { x: toSvgX(ball[0]), y: toSvgY(ball[1]) }
    : null;

  // Sort by angle so the polygon wraps defenders in order instead of crossing itself.
  const defensePolygon = defenders
    .sort((a, b) => {
      const angleA = Math.atan2(a.y - 50, a.x - 20);
      const angleB = Math.atan2(b.y - 50, b.x - 20);
      return angleA - angleB;
    })
    .map(p => `${p.x}%,${p.y}%`)
    .join(' ');

  return (
    <div className="bg-[#1a1a1a] rounded-xl md:rounded-2xl p-4 md:p-6 h-full flex flex-col border border-[#2a2a2a]">
      <div className="flex items-center justify-between mb-3 md:mb-4 flex-wrap gap-2">
        <h2 className="text-white text-base md:text-lg font-semibold">Live Pitch View</h2>
        <div className="flex items-center gap-2 md:gap-3">
          <Label htmlFor="tracking-mode" className="text-xs md:text-sm text-gray-400 hidden sm:block">
            Live Tracking
          </Label>
          <Switch
            id="tracking-mode"
            checked={isHeatmap}
            onCheckedChange={setIsHeatmap}
            className="scale-110"
          />
          <Label htmlFor="tracking-mode" className="text-xs md:text-sm text-gray-400">
            Heatmap
          </Label>
        </div>
      </div>

      <div className="flex-1 relative bg-[#0a4d2e] rounded-lg md:rounded-xl overflow-hidden border-2 border-[#0B6A41]">
        {/* Soccer Pitch */}
        <svg className="w-full h-full" viewBox="0 0 100 60" preserveAspectRatio="none">
          {/* Pitch markings */}
          <rect x="0" y="0" width="100" height="60" fill="#0a4d2e" />
          
          {/* Center line */}
          <line x1="50" y1="0" x2="50" y2="60" stroke="#0B6A41" strokeWidth="0.3" />
          
          {/* Center circle */}
          <circle cx="50" cy="30" r="8" fill="none" stroke="#0B6A41" strokeWidth="0.3" />
          <circle cx="50" cy="30" r="0.5" fill="#0B6A41" />
          
          {/* Left penalty area */}
          <rect x="0" y="18" width="15" height="24" fill="none" stroke="#0B6A41" strokeWidth="0.3" />
          <rect x="0" y="24" width="5" height="12" fill="none" stroke="#0B6A41" strokeWidth="0.3" />
          
          {/* Right penalty area */}
          <rect x="85" y="18" width="15" height="24" fill="none" stroke="#0B6A41" strokeWidth="0.3" />
          <rect x="95" y="24" width="5" height="12" fill="none" stroke="#0B6A41" strokeWidth="0.3" />
          
          {/* Goals */}
          <rect x="0" y="27" width="1" height="6" fill="#0B6A41" />
          <rect x="99" y="27" width="1" height="6" fill="#0B6A41" />
        </svg>

        {/* Heatmap overlay */}
        {isHeatmap && (
          <div className="absolute inset-0">
            {/* Hot zones on right side */}
            <div className="absolute top-[15%] right-[5%] w-32 h-32 bg-red-500/30 rounded-full blur-3xl" />
            <div className="absolute top-[35%] right-[8%] w-40 h-40 bg-orange-500/25 rounded-full blur-3xl" />
            <div className="absolute top-[55%] right-[6%] w-36 h-36 bg-yellow-500/20 rounded-full blur-3xl" />
            <div className="absolute top-[25%] right-[15%] w-28 h-28 bg-red-600/25 rounded-full blur-2xl" />
          </div>
        )}

        {/* Players and defensive shape */}
        <div className="absolute inset-0">
          <svg className="w-full h-full" viewBox="0 0 100 60" preserveAspectRatio="none">
            {/* Defensive shape polygon */}
            {!isHeatmap && (
              <polygon
                points={defensePolygon}
                fill="#0B6A41"
                fillOpacity="0.15"
                stroke="#0B6A41"
                strokeWidth="0.4"
                strokeDasharray="1,1"
              />
            )}
            
            {/* Player dots */}
            {players.map(player => (
              <g key={player.id}>
                <circle
                  cx={player.x}
                  cy={player.y}
                  r="1.2"
                  fill={player.isDefender ? '#0B6A41' : '#ffffff'}
                  stroke="#000"
                  strokeWidth="0.2"
                />
                <circle
                  cx={player.x}
                  cy={player.y}
                  r="2"
                  fill="none"
                  stroke={player.isDefender ? '#0B6A41' : '#ffffff'}
                  strokeWidth="0.15"
                  opacity="0.5"
                />
              </g>
            ))}

            {ballPoint && (
              <g>
                <circle cx={ballPoint.x} cy={ballPoint.y} r="0.9" fill="#FFD700" stroke="#000" strokeWidth="0.2" />
                <circle cx={ballPoint.x} cy={ballPoint.y} r="1.6" fill="none" stroke="#FFD700" strokeWidth="0.15" opacity="0.7" />
              </g>
            )}
          </svg>
        </div>
      </div>
    </div>
  );
}
