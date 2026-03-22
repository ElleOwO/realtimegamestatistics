'use client';

import { PitchView } from './components/PitchView';

export default function LiveDashboard() {
  return (
    <div className="mx-auto max-w-[1700px] h-[calc(100vh-80px)] overflow-hidden flex flex-col items-center justify-center">
      <div className="w-full h-full max-h-[85vh]">
        <PitchView />
      </div>
    </div>
  );
}
