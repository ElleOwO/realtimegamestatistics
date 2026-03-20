import { Outlet } from 'react-router';
import { Navigation } from '../components/Navigation';

export function RootLayout() {
  return (
    <div className="min-h-screen bg-[#0f0f0f] flex">
      <Navigation />
      
      {/* Main Content Area */}
      <main className="flex-1 md:ml-20 lg:ml-64 p-3 md:p-4 lg:p-6">
        <Outlet />
      </main>
    </div>
  );
}
