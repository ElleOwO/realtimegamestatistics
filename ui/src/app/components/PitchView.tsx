"use client";

import { useState, useEffect } from "react";

export function PitchView() {
  const [isPortrait, setIsPortrait] = useState(false);

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

  const getCoords = (x: number, y: number) => {
    if (isPortrait) {
      return { cx: y, cy: 100 - x };
    }
    return { cx: x, cy: y };
  };

  const viewBox = isPortrait ? "-1 -1 62 102" : "-1 -1 102 62";
  const aspectClass = isPortrait ? "aspect-[60/100]" : "aspect-[100/60]";

  return (
    <div className="w-full h-full bg-background flex items-center justify-center p-4 overflow-hidden">
      <div className={`relative w-full h-full max-w-5xl max-h-full ${aspectClass} bg-[#072a1b] rounded-3xl border-2 border-[#0B6A41]/30 overflow-hidden flex items-center justify-center transition-all duration-500`}>
        {/* Pitch Markings */}
        <svg
          className="absolute inset-0 w-full h-full opacity-40 pointer-events-none p-1.5"
          viewBox={viewBox}
          preserveAspectRatio="xMidYMid meet"
        >
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
        </svg>

        {/* Players */}
        <svg
          className="absolute inset-0 w-full h-full p-1.5"
          viewBox={viewBox}
          preserveAspectRatio="xMidYMid meet"
        >
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
        </svg>
      </div>
    </div>
  );
}
