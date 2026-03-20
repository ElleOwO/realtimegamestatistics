import { AlertCircle, Brain, TrendingUp } from 'lucide-react';
import type { AnalyticsInsight } from '../hooks/useAnalytics';

interface AIInsightsProps {
  insights?: AnalyticsInsight[];
  connected?: boolean;
}

export function AIInsights({ insights: liveInsights, connected = false }: AIInsightsProps) {
  const fallbackInsights = [
    {
      type: 'alert',
      title: 'Defensive Vulnerability Detected',
      body: 'Opponent is exploiting the right flank. Defensive convex hull is stretched. Recommend instructing the midfield to drop deeper to cover the right zone.',
      severity: 'high'
    },
    {
      type: 'tactical',
      title: 'Possession Pattern Analysis',
      body: 'Team is maintaining strong possession in the middle third but struggling to penetrate the final third. Consider width expansion.',
      severity: 'medium'
    }
  ];

  const insights = liveInsights && liveInsights.length > 0 ? liveInsights : fallbackInsights;

  return (
    <div className="bg-[#1a1a1a] rounded-xl md:rounded-2xl p-4 md:p-6 h-full flex flex-col border border-[#2a2a2a]">
      <div className="flex items-center gap-2 mb-3 md:mb-4">
        <Brain className="w-4 h-4 md:w-5 md:h-5 text-[#0B6A41]" />
        <h2 className="text-white text-base md:text-lg font-semibold">AI Coach Insights</h2>
      </div>

      <div className="space-y-3 md:space-y-4 flex-1 overflow-y-auto">
        {insights.map((insight, index) => {
          const severity =
            (insight as { severity?: string }).severity ??
            (insight.type === 'warning' || insight.type === 'alert' ? 'high' : 'medium');

          return (
          <div 
            key={index} 
            className={`p-3 md:p-4 rounded-lg md:rounded-xl border-l-4 ${
              severity === 'high' 
                ? 'bg-red-950/20 border-red-500' 
                : 'bg-[#0B6A41]/10 border-[#0B6A41]'
            }`}
          >
            <div className="flex items-start gap-2 md:gap-3">
              {severity === 'high' ? (
                <AlertCircle className="w-4 h-4 md:w-5 md:h-5 text-red-500 flex-shrink-0 mt-0.5" />
              ) : (
                <TrendingUp className="w-4 h-4 md:w-5 md:h-5 text-[#0B6A41] flex-shrink-0 mt-0.5" />
              )}
              <div className="flex-1">
                <h3 className={`font-semibold mb-1 text-sm md:text-base ${
                  severity === 'high' ? 'text-red-400' : 'text-[#0B6A41]'
                }`}>
                  {insight.title}
                </h3>
                <p className="text-gray-300 text-xs md:text-sm leading-relaxed">
                  {insight.body}
                </p>
              </div>
            </div>
          </div>
          );
        })}

        <div className="p-3 md:p-4 rounded-lg md:rounded-xl bg-[#0a4d2e]/20 border border-[#0B6A41]/30">
          <div className="flex items-start gap-2 md:gap-3">
            <div className="w-2 h-2 rounded-full bg-[#0B6A41] mt-2 animate-pulse" />
            <div className="flex-1">
              <p className="text-gray-400 text-xs md:text-sm italic">
                {connected ? 'AI model analyzing live data stream...' : 'Waiting for live analytics stream...'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
