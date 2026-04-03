"use client";

import { useState, useEffect, useMemo } from "react";
import { useSocket } from "./SocketProvider";

interface PitchViewProps {
  showPlayers: boolean;
  showHeatmap: boolean;
  showZones: boolean;
  showPassing: boolean;
  showBall: boolean;
}

interface PlayerPos {
  id: number;
  x: number;
  y: number;
  position: string;
}

type Formation = "4-3-3" | "4-4-2" | "3-5-2" | "5-4-1";

const FORMATIONS: Record<Formation, PlayerPos[]> = {
  "4-3-3": [
    { id: 1, x: 8, y: 30, position: "GK" },
    { id: 2, x: 22, y: 12, position: "LB" },
    { id: 3, x: 22, y: 48, position: "RB" },
    { id: 4, x: 18, y: 24, position: "CB" },
    { id: 5, x: 18, y: 36, position: "CB" },
    { id: 6, x: 35, y: 30, position: "CDM" },
    { id: 7, x: 45, y: 15, position: "LCM" },
    { id: 8, x: 45, y: 45, position: "RCM" },
    { id: 9, x: 55, y: 30, position: "CAM" },
    { id: 10, x: 75, y: 15, position: "LW" },
    { id: 11, x: 75, y: 45, position: "RW" },
    { id: 12, x: 85, y: 30, position: "ST" },
  ],
  "4-4-2": [
    { id: 1, x: 8, y: 30, position: "GK" },
    { id: 2, x: 22, y: 12, position: "LB" },
    { id: 3, x: 22, y: 48, position: "RB" },
    { id: 4, x: 18, y: 24, position: "CB" },
    { id: 5, x: 18, y: 36, position: "CB" },
    { id: 6, x: 45, y: 22, position: "LM" },
    { id: 7, x: 45, y: 38, position: "RM" },
    { id: 8, x: 40, y: 26, position: "CM" },
    { id: 9, x: 40, y: 34, position: "CM" },
    { id: 10, x: 80, y: 25, position: "ST" },
    { id: 11, x: 80, y: 35, position: "ST" },
  ],
  "3-5-2": [
    { id: 1, x: 8, y: 30, position: "GK" },
    { id: 2, x: 20, y: 30, position: "CB" },
    { id: 3, x: 20, y: 18, position: "CB" },
    { id: 4, x: 20, y: 42, position: "CB" },
    { id: 5, x: 45, y: 10, position: "LWB" },
    { id: 6, x: 45, y: 50, position: "RWB" },
    { id: 7, x: 35, y: 30, position: "CDM" },
    { id: 8, x: 50, y: 22, position: "CM" },
    { id: 9, x: 50, y: 38, position: "CM" },
    { id: 10, x: 80, y: 25, position: "ST" },
    { id: 11, x: 80, y: 35, position: "ST" },
  ],
  "5-4-1": [
    { id: 1, x: 8, y: 30, position: "GK" },
    { id: 2, x: 20, y: 30, position: "CB" },
    { id: 3, x: 20, y: 18, position: "CB" },
    { id: 4, x: 20, y: 42, position: "CB" },
    { id: 5, x: 25, y: 10, position: "LWB" },
    { id: 6, x: 25, y: 50, position: "RWB" },
    { id: 7, x: 45, y: 22, position: "LM" },
    { id: 8, x: 45, y: 38, position: "RM" },
    { id: 9, x: 40, y: 26, position: "CM" },
    { id: 10, x: 40, y: 34, position: "CM" },
    { id: 11, x: 85, y: 30, position: "ST" },
  ],
};

export function PitchView({ showPlayers, showHeatmap, showZones, showPassing, showBall }: PitchViewProps) {
  const { data: realtimeData } = useSocket();
  const [isPortrait, setIsPortrait] = useState(false);

  useEffect(() => {
    const checkOrientation = () => {
      setIsPortrait(window.innerHeight > window.innerWidth);
    };
    checkOrientation();
    window.addEventListener("resize", checkOrientation);
    return () => window.removeEventListener("resize", checkOrientation);
  }, []);

  const mapMetresToSvg = (x_m: number, y_m: number) => {
    const x = ((x_m + 52.5) / 105) * 100;
    const y = ((y_m + 34) / 68) * 60;
    return { x, y };
  };

  const getCoords = (x: number, y: number) => {
    if (isPortrait) {
      return { cx: y, cy: 100 - x };
    }
    return { cx: x, cy: y };
  };

  const viewBox = isPortrait ? "-1 -1 62 102" : "-1 -1 102 62";

  const heatPoints = useMemo(() => {
    if (!realtimeData?.heatmaps) {
      return [
        { x: 50, y: 30, r: 15, opacity: 0.3 },
        { x: 75, y: 15, r: 12, opacity: 0.4 },
        { x: 75, y: 45, r: 12, opacity: 0.4 },
        { x: 85, y: 30, r: 10, opacity: 0.5 },
        { x: 35, y: 30, r: 18, opacity: 0.25 },
      ];
    }
    const points: { x: number; y: number; r: number; opacity: number }[] = [];
    const team0 = realtimeData.heatmaps.team0;
    if (team0) {
      for (let row = 0; row < team0.length; row++) {
        for (let col = 0; col < team0[row].length; col++) {
          if (team0[row][col] > 0) {
            const x = (col / team0[row].length) * 100;
            const y = (row / team0.length) * 60;
            const intensity = Math.min(team0[row][col] / 100, 1);
            points.push({ x, y, r: 3 + intensity * 8, opacity: intensity * 0.6 });
          }
        }
      }
    }
    return points;
  }, [realtimeData?.heatmaps]);

  const passingLines = useMemo(() => {
    if (!realtimeData?.players) return [];
    const team0Players = realtimeData.players.filter((p) => p.team === 0);
    const team1Players = realtimeData.players.filter((p) => p.team === 1);
    const lines: { x1: number; y1: number; x2: number; y2: number; team: number; strength: number }[] = [];

    const addLines = (players: typeof realtimeData.players) => {
      for (let i = 0; i < players.length; i++) {
        for (let j = i + 1; j < players.length; j++) {
          const p1 = players[i];
          const p2 = players[j];
          const dist = Math.sqrt(Math.pow(p1.x_m - p2.x_m, 2) + Math.pow(p1.y_m - p2.y_m, 2));
          if (dist < 25) {
            const strength = Math.max(0, 1 - dist / 25);
            lines.push({
              x1: p1.x_m,
              y1: p1.y_m,
              x2: p2.x_m,
              y2: p2.y_m,
              team: p1.team,
              strength,
            });
          }
        }
      }
    };

    addLines(team0Players);
    addLines(team1Players);
    return lines;
  }, [realtimeData?.players]);

  return (
    <div className="relative w-full h-full bg-[#072a1b] flex items-center justify-center overflow-hidden">
      <svg
        className="w-full h-full"
        viewBox={viewBox}
        preserveAspectRatio="xMidYMid meet"
      >
          {/* Tactical Zones Layer */}
          {showZones && (
            <g className="opacity-30">
              {isPortrait ? (
                <>
                  <line x1="0" y1="33.3" x2="60" y2="33.3" stroke="#DBCC52" strokeWidth="0.2" strokeDasharray="1 1" />
                  <line x1="0" y1="66.6" x2="60" y2="66.6" stroke="#DBCC52" strokeWidth="0.2" strokeDasharray="1 1" />
                  <line x1="12" y1="0" x2="12" y2="100" stroke="#DBCC52" strokeWidth="0.1" strokeDasharray="0.5 0.5" />
                  <line x1="24" y1="0" x2="24" y2="100" stroke="#DBCC52" strokeWidth="0.1" strokeDasharray="0.5 0.5" />
                  <line x1="36" y1="0" x2="36" y2="100" stroke="#DBCC52" strokeWidth="0.1" strokeDasharray="0.5 0.5" />
                  <line x1="48" y1="0" x2="48" y2="100" stroke="#DBCC52" strokeWidth="0.1" strokeDasharray="0.5 0.5" />
                </>
              ) : (
                <>
                  <line x1="33.3" y1="0" x2="33.3" y2="60" stroke="#DBCC52" strokeWidth="0.2" strokeDasharray="1 1" />
                  <line x1="66.6" y1="0" x2="66.6" y2="60" stroke="#DBCC52" strokeWidth="0.2" strokeDasharray="1 1" />
                  <line x1="0" y1="12" x2="100" y2="12" stroke="#DBCC52" strokeWidth="0.1" strokeDasharray="0.5 0.5" />
                  <line x1="0" y1="24" x2="100" y2="24" stroke="#DBCC52" strokeWidth="0.1" strokeDasharray="0.5 0.5" />
                  <line x1="0" y1="36" x2="100" y2="36" stroke="#DBCC52" strokeWidth="0.1" strokeDasharray="0.5 0.5" />
                  <line x1="0" y1="48" x2="100" y2="48" stroke="#DBCC52" strokeWidth="0.1" strokeDasharray="0.5 0.5" />
                </>
              )}
            </g>
          )}

          {/* Pitch Markings Layer */}
          <g className="opacity-40">
            {isPortrait ? (
              <>
                <rect x="0" y="0" width="60" height="100" fill="none" stroke="#0B6A41" strokeWidth="0.4" />
                <line x1="0" y1="50" x2="60" y2="50" stroke="#0B6A41" strokeWidth="0.4" />
                <circle cx="30" cy="50" r="8" fill="none" stroke="#0B6A41" strokeWidth="0.4" />
                <rect x="15" y="84" width="30" height="16" fill="none" stroke="#0B6A41" strokeWidth="0.4" />
                <rect x="15" y="0" width="30" height="16" fill="none" stroke="#0B6A41" strokeWidth="0.4" />
                <rect x="24" y="94" width="12" height="6" fill="none" stroke="#0B6A41" strokeWidth="0.4" />
                <rect x="24" y="0" width="12" height="6" fill="none" stroke="#0B6A41" strokeWidth="0.4" />
              </>
            ) : (
              <>
                <rect x="0" y="0" width="100" height="60" fill="none" stroke="#0B6A41" strokeWidth="0.3" />
                <line x1="50" y1="0" x2="50" y2="60" stroke="#0B6A41" strokeWidth="0.3" />
                <circle cx="50" cy="30" r="8" fill="none" stroke="#0B6A41" strokeWidth="0.3" />
                <rect x="0" y="15" width="16" height="30" fill="none" stroke="#0B6A41" strokeWidth="0.3" />
                <rect x="84" y="15" width="16" height="30" fill="none" stroke="#0B6A41" strokeWidth="0.3" />
                <rect x="0" y="24" width="6" height="12" fill="none" stroke="#0B6A41" strokeWidth="0.3" />
                <rect x="94" y="24" width="6" height="12" fill="none" stroke="#0B6A41" strokeWidth="0.3" />
              </>
            )}
          </g>

          {/* Heatmap Layer */}
          {showHeatmap && (
            <g className="transition-opacity duration-500">
              {heatPoints.map((point, i) => {
                const { cx, cy } = getCoords(point.x, point.y);
                return (
                  <circle
                    key={`heat-${i}`}
                    cx={cx}
                    cy={cy}
                    r={point.r}
                    fill="url(#heatGradient)"
                    opacity={point.opacity}
                  />
                );
              })}
              <defs>
                <radialGradient id="heatGradient">
                  <stop offset="0%" stopColor="#DBCC52" />
                  <stop offset="100%" stopColor="#DBCC52" stopOpacity="0" />
                </radialGradient>
              </defs>
            </g>
          )}

          {/* Passing Patterns Layer */}
          {showPassing && passingLines.length > 0 && (
            <g className="transition-opacity duration-500">
              {passingLines.map((line, i) => {
                const p1 = mapMetresToSvg(line.x1, line.y1);
                const p2 = mapMetresToSvg(line.x2, line.y2);
                const { cx: x1, cy: y1 } = getCoords(p1.x, p1.y);
                const { cx: x2, cy: y2 } = getCoords(p2.x, p2.y);
                return (
                  <line
                    key={`pass-${i}`}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke={line.team === 0 ? "#0B6A41" : "#FF1493"}
                    strokeWidth={0.3 + line.strength * 0.7}
                    opacity={0.2 + line.strength * 0.5}
                    strokeDasharray={line.strength > 0.5 ? "none" : "1 0.5"}
                  />
                );
              })}
            </g>
          )}

          {/* Ball Layer */}
          {showBall && realtimeData?.ball && (
            <g>
              {(() => {
                const mapped = mapMetresToSvg(realtimeData.ball[0], realtimeData.ball[1]);
                const { cx, cy } = getCoords(mapped.x, mapped.y);
                return (
                  <circle
                    cx={cx}
                    cy={cy}
                    r="1.2"
                    fill="#FFF"
                    stroke="#000"
                    strokeWidth="0.3"
                    className="transition-all duration-300 ease-linear"
                  />
                );
              })()}
            </g>
          )}

          {/* Players Layer */}
          {showPlayers && (
            <g className="transition-opacity duration-500">
              {realtimeData
                ? realtimeData.players.map((p) => {
                    const mapped = mapMetresToSvg(p.x_m, p.y_m);
                    const { cx, cy } = getCoords(mapped.x, mapped.y);
                    return (
                      <g
                        key={`player-${p.id}`}
                        className="transition-all duration-300 ease-linear"
                      >
                        <circle
                          cx={cx}
                          cy={cy}
                          r="1.8"
                          fill={p.team === 0 ? "#0B6A41" : "#FF1493"}
                          stroke="#FFF"
                          strokeWidth="0.3"
                          className={p.is_sprinting ? "animate-pulse" : ""}
                        />
                        <text
                          x={cx}
                          y={cy - 3}
                          textAnchor="middle"
                          fill="#FFF"
                          fontSize="1.5"
                          fontWeight="black"
                          className="uppercase tracking-tighter opacity-95 select-none font-sans"
                        >
                          {p.id}
                        </text>
                      </g>
                    );
                  })
                : FORMATIONS["4-3-3"].map((p) => {
                    const { cx, cy } = getCoords(p.x, p.y);
                    return (
                      <g
                        key={`formation-${p.id}`}
                        className="transition-all duration-700 ease-in-out"
                      >
                        <circle
                          cx={cx}
                          cy={cy}
                          r="1.8"
                          fill="#0B6A41"
                          stroke="#000"
                          strokeWidth="0.2"
                        />
                        <text
                          x={cx}
                          y={cy - 3}
                          textAnchor="middle"
                          fill="#ececec"
                          fontSize="1.8"
                          fontWeight="black"
                          className="uppercase tracking-tighter opacity-95 select-none font-sans"
                        >
                          {p.position}
                        </text>
                      </g>
                    );
                  })}
            </g>
          )}
        </svg>
    </div>
  );
}
