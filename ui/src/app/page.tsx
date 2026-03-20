'use client';

import { PitchView } from './components/PitchView';
import { MatchControl } from './components/MatchControl';

export default function LiveDashboard() {
  return (
    <div className="mx-auto max-w-[1700px] space-y-6 pb-12">
      {/* Real-time Match Command Center Header */}
      <MatchControl />

      <div className="w-full h-[650px] xl:h-[750px]">
        <PitchView />
      </div>
    </div>
  );
}
