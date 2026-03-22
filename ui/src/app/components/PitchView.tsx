"use client";

export function PitchView() {
  // Home Team (US) - Set up in a 4-3-3 formation
  const players = [
    { id: 1, x: 8, y: 30, position: 'GK' },
    { id: 2, x: 22, y: 12, position: 'LB' },
    { id: 3, x: 22, y: 48, position: 'RB' },
    { id: 4, x: 18, y: 24, position: 'CB' },
    { id: 5, x: 18, y: 36, position: 'CB' },
    { id: 6, x: 35, y: 30, position: 'CDM' },
    { id: 7, x: 45, y: 15, position: 'LCM' },
    { id: 8, x: 45, y: 45, position: 'RCM' },
    { id: 9, x: 55, y: 30, position: 'CAM' },
    { id: 10, x: 75, y: 15, position: 'LW' },
    { id: 11, x: 75, y: 45, position: 'RW' },
    { id: 12, x: 85, y: 30, position: 'ST' },
  ];

  return (
    <div className="w-full h-full bg-[#051f14] flex items-center justify-center relative p-8 rounded-[2.5rem] border border-zinc-800/50 shadow-2xl overflow-hidden">
      <div className="relative w-full max-w-5xl aspect-[100/60] bg-[#072a1b] rounded-3xl shadow-2xl border-2 border-emerald-900/50 overflow-hidden">
        {/* Pitch Markings */}
        <svg className="absolute inset-0 w-full h-full opacity-30 pointer-events-none" viewBox="0 0 100 60" preserveAspectRatio="none">
          <rect x="0" y="0" width="100" height="60" fill="none" stroke="#10b981" strokeWidth="0.2" />
          <line x1="50" y1="0" x2="50" y2="60" stroke="#10b981" strokeWidth="0.2" />
          <circle cx="50" cy="30" r="8" fill="none" stroke="#10b981" strokeWidth="0.2" />
          <rect x="0" y="15" width="16" height="30" fill="none" stroke="#10b981" strokeWidth="0.2" />
          <rect x="84" y="15" width="16" height="30" fill="none" stroke="#10b981" strokeWidth="0.2" />
          <rect x="0" y="24" width="6" height="12" fill="none" stroke="#10b981" strokeWidth="0.2" />
          <rect x="94" y="24" width="6" height="12" fill="none" stroke="#10b981" strokeWidth="0.2" />
        </svg>

        {/* Tactical Overlays */}
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 60" preserveAspectRatio="none">
           {/* Home Players ONLY */}
           {players.map(p => (
             <g key={p.id}>
                <circle cx={p.x} cy={p.y} r="1.5" fill="#10b981" stroke="#000" strokeWidth="0.1" />
                <text x={p.x} y={p.y - 2.5} textAnchor="middle" fill="#ececec" fontSize="1.5" fontWeight="black" className="uppercase tracking-tighter opacity-90 drop-shadow-md">
                  {p.position}
                </text>
             </g>
           ))}
        </svg>
      </div>
    </div>
  );
}
