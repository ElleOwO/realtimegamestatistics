import { PitchView } from '../components/PitchView';
import { AIInsights } from '../components/AIInsights';
import { KPICard } from '../components/KPICard';

export function TacticalView() {
  return (
    <div className="max-w-[1600px] mx-auto">
      {/* Page Header */}
      <div className="mb-4">
        <h1 className="text-2xl lg:text-3xl font-bold text-white">Tactical Analysis</h1>
        <p className="text-gray-400 text-sm">Formation insights and AI-powered recommendations</p>
      </div>

      {/* Tactical Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4 mb-4 md:mb-6">
        <div className="h-28">
          <KPICard 
            title="Formation Effectiveness" 
            value="78%" 
            subtitle="4-3-3 stability rating"
          />
        </div>
        <div className="h-28">
          <KPICard 
            title="Defensive Line Height" 
            value="42m" 
            subtitle="Average from goal line"
          />
        </div>
        <div className="h-28">
          <KPICard 
            title="Width of Attack" 
            value="54m" 
            subtitle="Average spread"
          />
        </div>
      </div>

      {/* Main Tactical Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
        {/* Pitch View - Larger */}
        <div className="lg:col-span-2 h-[500px] md:h-[600px] lg:h-[700px]">
          <PitchView />
        </div>

        {/* AI Insights - Full Height */}
        <div className="h-[500px] md:h-[600px] lg:h-[700px]">
          <AIInsights />
        </div>
      </div>

      {/* Formation Comparison */}
      <div className="mt-4 md:mt-6 grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
        <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-2xl p-6">
          <h3 className="text-white font-bold text-lg mb-4">Current Formation: 4-3-3</h3>
          
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">Offensive Pressure</span>
              <div className="flex-1 mx-4 h-2 bg-[#222] rounded-full overflow-hidden">
                <div className="h-full bg-[#0B6A41]" style={{ width: '72%' }} />
              </div>
              <span className="text-white font-semibold text-sm">72%</span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">Defensive Coverage</span>
              <div className="flex-1 mx-4 h-2 bg-[#222] rounded-full overflow-hidden">
                <div className="h-full bg-[#0B6A41]" style={{ width: '65%' }} />
              </div>
              <span className="text-white font-semibold text-sm">65%</span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">Width Utilization</span>
              <div className="flex-1 mx-4 h-2 bg-[#222] rounded-full overflow-hidden">
                <div className="h-full bg-[#0B6A41]" style={{ width: '81%' }} />
              </div>
              <span className="text-white font-semibold text-sm">81%</span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-gray-400 text-sm">Midfield Control</span>
              <div className="flex-1 mx-4 h-2 bg-[#222] rounded-full overflow-hidden">
                <div className="h-full bg-[#0B6A41]" style={{ width: '58%' }} />
              </div>
              <span className="text-white font-semibold text-sm">58%</span>
            </div>
          </div>
        </div>

        <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-2xl p-6">
          <h3 className="text-white font-bold text-lg mb-4">Tactical Adjustments</h3>
          
          <div className="space-y-3">
            <div className="bg-[#222] border border-[#0B6A41]/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 rounded-full bg-[#0B6A41] mt-1.5 flex-shrink-0" />
                <div>
                  <p className="text-white font-semibold text-sm mb-1">Press Higher</p>
                  <p className="text-gray-400 text-xs">Push defensive line to 48m to exploit Calgary's slow buildup</p>
                </div>
              </div>
            </div>

            <div className="bg-[#222] border border-[#0B6A41]/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 rounded-full bg-[#0B6A41] mt-1.5 flex-shrink-0" />
                <div>
                  <p className="text-white font-semibold text-sm mb-1">Switch to 4-2-3-1</p>
                  <p className="text-gray-400 text-xs">Add defensive midfielder to control central areas</p>
                </div>
              </div>
            </div>

            <div className="bg-[#222] border border-yellow-500/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 rounded-full bg-yellow-500 mt-1.5 flex-shrink-0" />
                <div>
                  <p className="text-white font-semibold text-sm mb-1">Exploit Left Flank</p>
                  <p className="text-gray-400 text-xs">Calgary's RB showing signs of fatigue - increase left wing attacks</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
