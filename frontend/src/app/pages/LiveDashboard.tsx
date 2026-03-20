/**
 * LiveDashboard — Coach's Sideline Analytics View
 * 
 * Real-time soccer match analytics dashboard for iPad:
 * ✓ 3 KPI metric cards (possession %, transition speed, total xG)
 * ✓ Live pitch visualization (player positions, ball, team control zones)
 * ✓ AI tactical insights sidebar (Gemini 2.5 Flash + rule-based alerts)
 * ✓ Expected Goals (xG) timeline chart (shot history over match)
 * 
 * RESPONSIVE: Mobile (1 col) → Tablet (12 col) → Desktop (12 col)
 * 
 * DATA FLOW (future):
 *   WebSocket → useAnalytics() → LiveDashboard → Child Components
 */

import { PitchView } from '../components/PitchView';
import { KPICard } from '../components/KPICard';
import { XGChart } from '../components/XGChart';
import { AIInsights } from '../components/AIInsights';
import { useAnalytics } from '../hooks/useAnalytics';

function formatMetric(value: number | undefined, digits = 1): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '--';
  }
  return value.toFixed(digits);
}

export function LiveDashboard() {
  const { data, connected, error } = useAnalytics();

  const possessionPct = data?.possession?.team0_pct;
  const transitionSpeed = data?.transition_speed_s;
  const totalXg = data?.total_xg_team0;

  return (
    <div className="max-w-[1600px] mx-auto">
      {/* ═══════ PAGE HEADER ═══════ */}
      <div className="mb-4">
        <h1 className="text-2xl lg:text-3xl font-bold text-white">Live Match Analytics</h1>
        <p className="text-gray-400 text-sm">
          {connected ? 'Connected to live analytics stream' : 'Waiting for live analytics stream'}
          {error ? ` • ${error}` : ''}
        </p>
      </div>

      {/* Bento Grid Layout - Optimized for iPad Landscape */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-3 md:gap-4 lg:gap-6">
        {/* Top Row - 3 KPI Cards */}
        <div className="md:col-span-4 h-28 md:h-32">
          <KPICard 
            title="Live Ball Possession" 
            value={typeof possessionPct === 'number' ? `${formatMetric(possessionPct)}%` : '--'}
            subtitle={connected ? 'Live update' : 'Using fallback values'}
          />
        </div>
        <div className="md:col-span-4 h-28 md:h-32">
          <KPICard 
            title="Attacking Transition Speed" 
            value={typeof transitionSpeed === 'number' ? `${formatMetric(transitionSpeed)}s` : '--'}
            subtitle="Average time to attack"
          />
        </div>
        <div className="md:col-span-4 h-28 md:h-32">
          <KPICard 
            title="Total Expected Goals" 
            value={formatMetric(totalXg, 2)}
            subtitle="xG generated this match"
          />
        </div>

        {/* Main Content Row - Pitch View + AI Insights */}
        <div className="md:col-span-8 h-[400px] md:h-[450px] lg:h-[500px]">
          <PitchView players={data?.players} ball={data?.ball ?? null} />
        </div>
        <div className="md:col-span-4 h-[400px] md:h-[450px] lg:h-[500px]">
          <AIInsights insights={data?.insights} connected={connected} />
        </div>

        {/* Bottom Row - xG Chart (Full Width) */}
        <div className="md:col-span-12 h-[300px] md:h-[350px]">
          <XGChart data={data?.xg_timeline} />
        </div>
      </div>
    </div>
  );
}