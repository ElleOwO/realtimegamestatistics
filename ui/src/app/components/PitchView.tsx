"use client";

import { useState, useEffect } from "react";
import { Activity, Share2, Grid3X3, Users, Settings2 } from "lucide-react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";

export function PitchView() {
  const [isPortrait, setIsPortrait] = useState(false);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showPassing, setShowPassing] = useState(false);
  const [showZones, setShowZones] = useState(false);
  const [showPlayers, setShowPlayers] = useState(true);

  useEffect(() => {
    const checkOrientation = () => {
      setIsPortrait(window.innerHeight > window.innerWidth);
    };
    
    checkOrientation();
    window.addEventListener("resize", checkOrientation);
    return () => window.removeEventListener("resize", checkOrientation);
  }, []);

  // Home Team (US) - Set up in a 4-3-3 formation
  const players = [
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
  ];

  // Passing connections (mock data)
  const passes = [
    { from: 6, to: 9, weight: 12 },
    { from: 9, to: 12, weight: 8 },
    { from: 10, to: 12, weight: 5 },
    { from: 11, to: 12, weight: 6 },
    { from: 4, to: 6, weight: 15 },
    { from: 5, to: 6, weight: 14 },
    { from: 2, to: 10, weight: 9 },
    { from: 3, to: 11, weight: 7 },
  ];

  // Heatmap points (mock data)
  const heatPoints = [
    { x: 50, y: 30, r: 15, opacity: 0.3 },
    { x: 75, y: 15, r: 12, opacity: 0.4 },
    { x: 75, y: 45, r: 12, opacity: 0.4 },
    { x: 85, y: 30, r: 10, opacity: 0.5 },
    { x: 35, y: 30, r: 18, opacity: 0.25 },
  ];

  const getCoords = (x: number, y: number) => {
    if (isPortrait) {
      return { cx: y, cy: 100 - x };
    }
    return { cx: x, cy: y };
  };

  const viewBox = isPortrait ? "-1 -1 62 102" : "-1 -1 102 62";
  const aspectClass = isPortrait ? "aspect-[60/100]" : "aspect-[100/60]";

  return (
    <div className="w-full h-full bg-background flex flex-col items-center justify-center p-4 overflow-hidden gap-4">
      {/* Pitch Controls */}
      <div className="flex items-center gap-3 bg-card p-2 px-4 rounded-2xl border border-border shadow-lg">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="h-9 gap-2 text-foreground/80 hover:text-primary transition-colors">
              <Settings2 className="w-4 h-4" />
              <span className="text-[10px] font-black uppercase tracking-widest">Display Options</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-56 bg-card border-border">
            <DropdownMenuLabel className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Tactical Layers</DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-border" />
            <DropdownMenuCheckboxItem
              checked={showPlayers}
              onCheckedChange={setShowPlayers}
              className="text-xs font-bold uppercase tracking-tight focus:bg-primary/10 focus:text-primary"
            >
              <Users className="w-3.5 h-3.5 mr-2" />
              Player Positions
            </DropdownMenuCheckboxItem>
            <DropdownMenuCheckboxItem
              checked={showHeatmap}
              onCheckedChange={setShowHeatmap}
              className="text-xs font-bold uppercase tracking-tight focus:bg-primary/10 focus:text-primary"
            >
              <Activity className="w-3.5 h-3.5 mr-2" />
              Heatmap (Match Load)
            </DropdownMenuCheckboxItem>
            <DropdownMenuCheckboxItem
              checked={showPassing}
              onCheckedChange={setShowPassing}
              className="text-xs font-bold uppercase tracking-tight focus:bg-primary/10 focus:text-primary"
            >
              <Share2 className="w-3.5 h-3.5 mr-2" />
              Passing Patterns
            </DropdownMenuCheckboxItem>
            <DropdownMenuCheckboxItem
              checked={showZones}
              onCheckedChange={setShowZones}
              className="text-xs font-bold uppercase tracking-tight focus:bg-primary/10 focus:text-primary"
            >
              <Grid3X3 className="w-3.5 h-3.5 mr-2" />
              Tactical Zones
            </DropdownMenuCheckboxItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <div className="h-4 w-px bg-border mx-1" />

        <div className="flex items-center gap-2">
          {showHeatmap && <Badge className="bg-primary/10 text-primary border-primary/20 text-[8px] font-black h-5 uppercase tracking-tighter">Heatmap Active</Badge>}
          {showPassing && <Badge className="bg-secondary/10 text-secondary border-secondary/20 text-[8px] font-black h-5 uppercase tracking-tighter">Pass Map Active</Badge>}
          {showZones && <Badge className="bg-foreground/5 text-foreground/40 border-border text-[8px] font-black h-5 uppercase tracking-tighter">Zones Active</Badge>}
        </div>
      </div>

      <div className={`relative w-full h-full max-w-5xl max-h-full ${aspectClass} bg-[#072a1b] rounded-3xl border-2 border-[#0B6A41]/30 overflow-hidden flex items-center justify-center transition-all duration-500`}>
        {/* Pitch Layers */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none p-1.5"
          viewBox={viewBox}
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Tactical Zones Layer */}
          {showZones && (
            <g className="opacity-30">
              {/* Thirds */}
              {isPortrait ? (
                <>
                  <line x1="0" y1="33.3" x2="60" y2="33.3" stroke="#DBCC52" strokeWidth="0.2" strokeDasharray="1 1" />
                  <line x1="0" y1="66.6" x2="60" y2="66.6" stroke="#DBCC52" strokeWidth="0.2" strokeDasharray="1 1" />
                  {/* Channels/Half-spaces */}
                  <line x1="12" y1="0" x2="12" y2="100" stroke="#DBCC52" strokeWidth="0.1" strokeDasharray="0.5 0.5" />
                  <line x1="24" y1="0" x2="24" y2="100" stroke="#DBCC52" strokeWidth="0.1" strokeDasharray="0.5 0.5" />
                  <line x1="36" y1="0" x2="36" y2="100" stroke="#DBCC52" strokeWidth="0.1" strokeDasharray="0.5 0.5" />
                  <line x1="48" y1="0" x2="48" y2="100" stroke="#DBCC52" strokeWidth="0.1" strokeDasharray="0.5 0.5" />
                </>
              ) : (
                <>
                  <line x1="33.3" y1="0" x2="33.3" y2="60" stroke="#DBCC52" strokeWidth="0.2" strokeDasharray="1 1" />
                  <line x1="66.6" y1="0" x2="66.6" y2="60" stroke="#DBCC52" strokeWidth="0.2" strokeDasharray="1 1" />
                  {/* Channels/Half-spaces */}
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
          {showPassing && (
            <g className="transition-opacity duration-500">
              {passes.map((pass, i) => {
                const fromP = players.find(p => p.id === pass.from)!;
                const toP = players.find(p => p.id === pass.to)!;
                const { cx: x1, cy: y1 } = getCoords(fromP.x, fromP.y);
                const { cx: x2, cy: y2 } = getCoords(toP.x, toP.y);
                return (
                  <line
                    key={`pass-${i}`}
                    x1={x1} y1={y1} x2={x2} y2={y2}
                    stroke="#DBCC52"
                    strokeWidth={pass.weight / 15}
                    strokeLinecap="round"
                    opacity="0.4"
                    strokeDasharray={`${pass.weight/2} 1`}
                  />
                );
              })}
            </g>
          )}

          {/* Players Layer */}
          {showPlayers && (
            <g className="transition-opacity duration-500">
              {players.map((p) => {
                const { cx, cy } = getCoords(p.x, p.y);
                return (
                  <g key={p.id} className="transition-all duration-700 ease-in-out">
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
    </div>
  );
}
