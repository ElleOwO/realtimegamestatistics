import { XGChart } from '../components/XGChart';
import { KPICard } from '../components/KPICard';
import { Trophy, TrendingUp, Users, Target } from 'lucide-react';

export function MatchReports() {
  return (
    <div className="max-w-[1600px] mx-auto">
      {/* Page Header */}
      <div className="mb-4">
        <h1 className="text-2xl lg:text-3xl font-bold text-white">Match Reports</h1>
        <p className="text-gray-400 text-sm">Performance analytics and expected goals timeline</p>
      </div>

      {/* Match Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 mb-4 md:mb-6">
        <div className="h-28">
          <KPICard 
            title="Match Score" 
            value="2-1" 
            subtitle="U of S leading"
          />
        </div>
        <div className="h-28">
          <KPICard 
            title="Total Expected Goals" 
            value="1.84" 
            subtitle="vs Calgary 1.32 xG"
          />
        </div>
        <div className="h-28">
          <KPICard 
            title="Win Probability" 
            value="68%" 
            subtitle="Based on current metrics"
          />
        </div>
        <div className="h-28">
          <KPICard 
            title="Possession" 
            value="55%" 
            subtitle="↑ 3% from 1st half"
          />
        </div>
      </div>

      {/* Expected Goals Chart */}
      <div className="mb-4 md:mb-6">
        <div className="h-[350px] md:h-[400px]">
          <XGChart />
        </div>
      </div>

      {/* Match Statistics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        {/* Team Performance */}
        <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-[#0B6A41] rounded-lg flex items-center justify-center">
              <Trophy className="w-5 h-5 text-white" />
            </div>
            <h3 className="text-white font-bold text-lg">Team Performance</h3>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-400 text-sm">Shots on Target</span>
                <span className="text-white font-semibold">12 / 18</span>
              </div>
              <div className="h-2 bg-[#222] rounded-full overflow-hidden">
                <div className="h-full bg-[#0B6A41]" style={{ width: '67%' }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-400 text-sm">Pass Completion</span>
                <span className="text-white font-semibold">82%</span>
              </div>
              <div className="h-2 bg-[#222] rounded-full overflow-hidden">
                <div className="h-full bg-[#0B6A41]" style={{ width: '82%' }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-400 text-sm">Tackles Won</span>
                <span className="text-white font-semibold">76%</span>
              </div>
              <div className="h-2 bg-[#222] rounded-full overflow-hidden">
                <div className="h-full bg-[#0B6A41]" style={{ width: '76%' }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-400 text-sm">Aerial Duels</span>
                <span className="text-white font-semibold">58%</span>
              </div>
              <div className="h-2 bg-[#222] rounded-full overflow-hidden">
                <div className="h-full bg-[#0B6A41]" style={{ width: '58%' }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-400 text-sm">Defensive Actions</span>
                <span className="text-white font-semibold">34 actions</span>
              </div>
              <div className="h-2 bg-[#222] rounded-full overflow-hidden">
                <div className="h-full bg-[#0B6A41]" style={{ width: '89%' }} />
              </div>
            </div>
          </div>
        </div>

        {/* Key Moments */}
        <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-[#0B6A41] rounded-lg flex items-center justify-center">
              <Target className="w-5 h-5 text-white" />
            </div>
            <h3 className="text-white font-bold text-lg">Key Moments</h3>
          </div>

          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-16 text-center">
                <div className="text-[#0B6A41] font-bold text-lg">18'</div>
                <div className="text-gray-500 text-xs">1st Half</div>
              </div>
              <div className="flex-1">
                <div className="bg-[#0B6A41]/10 border border-[#0B6A41]/30 rounded-lg p-3">
                  <p className="text-white font-semibold text-sm mb-1">⚽ GOAL - Williams</p>
                  <p className="text-gray-400 text-xs">Header from corner • xG: 0.42</p>
                </div>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-shrink-0 w-16 text-center">
                <div className="text-[#0B6A41] font-bold text-lg">34'</div>
                <div className="text-gray-500 text-xs">1st Half</div>
              </div>
              <div className="flex-1">
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                  <p className="text-white font-semibold text-sm mb-1">⚽ GOAL - Calgary</p>
                  <p className="text-gray-400 text-xs">Counter attack • xG: 0.68</p>
                </div>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-shrink-0 w-16 text-center">
                <div className="text-[#0B6A41] font-bold text-lg">51'</div>
                <div className="text-gray-500 text-xs">2nd Half</div>
              </div>
              <div className="flex-1">
                <div className="bg-[#0B6A41]/10 border border-[#0B6A41]/30 rounded-lg p-3">
                  <p className="text-white font-semibold text-sm mb-1">⚽ GOAL - Martinez</p>
                  <p className="text-gray-400 text-xs">Long shot from edge of box • xG: 0.18</p>
                </div>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-shrink-0 w-16 text-center">
                <div className="text-yellow-500 font-bold text-lg">58'</div>
                <div className="text-gray-500 text-xs">2nd Half</div>
              </div>
              <div className="flex-1">
                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3">
                  <p className="text-white font-semibold text-sm mb-1">🟡 Yellow Card - Thompson</p>
                  <p className="text-gray-400 text-xs">Tactical foul in midfield</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Additional Match Stats */}
      <div className="mt-4 md:mt-6 grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-[#0B6A41]" />
            <p className="text-gray-400 text-xs">Corners</p>
          </div>
          <p className="text-white font-bold text-2xl">8</p>
          <p className="text-gray-500 text-xs">vs Calgary 4</p>
        </div>

        <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-[#0B6A41]" />
            <p className="text-gray-400 text-xs">Offsides</p>
          </div>
          <p className="text-white font-bold text-2xl">3</p>
          <p className="text-gray-500 text-xs">vs Calgary 5</p>
        </div>

        <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-4 h-4 text-[#0B6A41]" />
            <p className="text-gray-400 text-xs">Fouls</p>
          </div>
          <p className="text-white font-bold text-2xl">11</p>
          <p className="text-gray-500 text-xs">vs Calgary 14</p>
        </div>

        <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Trophy className="w-4 h-4 text-[#0B6A41]" />
            <p className="text-gray-400 text-xs">Saves</p>
          </div>
          <p className="text-white font-bold text-2xl">6</p>
          <p className="text-gray-500 text-xs">Goalkeeper</p>
        </div>
      </div>
    </div>
  );
}
