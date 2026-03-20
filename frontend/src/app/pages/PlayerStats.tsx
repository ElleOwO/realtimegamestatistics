import { PlayerList } from '../components/PlayerList';
import { KPICard } from '../components/KPICard';
import { TrendingUp, Timer, Zap, Target } from 'lucide-react';

export function PlayerStats() {
  return (
    <div className="max-w-[1600px] mx-auto">
      {/* Page Header */}
      <div className="mb-4">
        <h1 className="text-2xl lg:text-3xl font-bold text-white">Player Statistics</h1>
        <p className="text-gray-400 text-sm">Individual performance metrics and analytics</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 mb-4 md:mb-6">
        <div className="h-28">
          <KPICard 
            title="Total Distance Run" 
            value="98.4km" 
            subtitle="Team aggregate"
          />
        </div>
        <div className="h-28">
          <KPICard 
            title="Avg Sprint Speed" 
            value="28.7km/h" 
            subtitle="Top speed recorded"
          />
        </div>
        <div className="h-28">
          <KPICard 
            title="Pass Accuracy" 
            value="82%" 
            subtitle="↑ 5% from last match"
          />
        </div>
        <div className="h-28">
          <KPICard 
            title="Shots on Target" 
            value="12/18" 
            subtitle="67% conversion"
          />
        </div>
      </div>

      {/* Player Performance Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
        {/* Player List */}
        <div className="lg:col-span-2 h-[600px] md:h-[700px]">
          <PlayerList />
        </div>

        {/* Player Insights Panel */}
        <div className="space-y-4">
          <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-2xl p-6">
            <h3 className="text-white font-bold text-lg mb-4">Top Performers</h3>
            
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-[#0B6A41] rounded-lg flex items-center justify-center flex-shrink-0">
                  <TrendingUp className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1">
                  <p className="text-white font-semibold text-sm">Most Sprints</p>
                  <p className="text-gray-400 text-xs">Johnson • 47 sprints</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-[#0B6A41] rounded-lg flex items-center justify-center flex-shrink-0">
                  <Zap className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1">
                  <p className="text-white font-semibold text-sm">Highest Work Rate</p>
                  <p className="text-gray-400 text-xs">Martinez • 12.3km</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-[#0B6A41] rounded-lg flex items-center justify-center flex-shrink-0">
                  <Target className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1">
                  <p className="text-white font-semibold text-sm">Best Pass Accuracy</p>
                  <p className="text-gray-400 text-xs">Chen • 94%</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-[#0B6A41] rounded-lg flex items-center justify-center flex-shrink-0">
                  <Timer className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1">
                  <p className="text-white font-semibold text-sm">Time in Attack Zone</p>
                  <p className="text-gray-400 text-xs">Williams • 18:23</p>
                </div>
              </div>
            </div>
          </div>

          {/* Substitution Recommendations */}
          <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-2xl p-6">
            <h3 className="text-white font-bold text-lg mb-4">Substitution Alerts</h3>
            
            <div className="space-y-3">
              <div className="bg-[#222] border border-yellow-500/20 rounded-lg p-4">
                <p className="text-yellow-500 font-semibold text-sm mb-1">⚠️ High Fatigue</p>
                <p className="text-gray-300 text-sm">#7 Martinez</p>
                <p className="text-gray-500 text-xs">Consider substitution at 70'</p>
              </div>

              <div className="bg-[#222] border border-red-500/20 rounded-lg p-4">
                <p className="text-red-500 font-semibold text-sm mb-1">🟡 Yellow Card Risk</p>
                <p className="text-gray-300 text-sm">#5 Thompson</p>
                <p className="text-gray-500 text-xs">3 fouls committed</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
