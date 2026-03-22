'use client';

import { PitchView } from './components/PitchView';

export default function LiveDashboard() {
  return (
    <div className="mx-auto max-w-[1700px] h-[calc(100vh-80px)] lg:h-[calc(100vh-120px)] flex flex-col items-center justify-center">
      <div className="w-full h-full">
        <PitchView />
      </div>
    </div>
  );
}
