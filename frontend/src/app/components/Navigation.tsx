import { Link, useLocation } from 'react-router';
import { Activity, BarChart3, Users, FileText, Menu } from 'lucide-react';
import { useState } from 'react';

export function Navigation() {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);

  const navItems = [
    { path: '/', label: 'Live Dashboard', icon: Activity },
    { path: '/players', label: 'Player Stats', icon: Users },
    { path: '/tactical', label: 'Tactical View', icon: BarChart3 },
    { path: '/reports', label: 'Match Reports', icon: FileText },
  ];

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="md:hidden fixed top-4 left-4 z-50 w-12 h-12 bg-[#1a1a1a] border border-[#2a2a2a] rounded-xl flex items-center justify-center hover:bg-[#222] transition-colors"
      >
        <Menu className="w-6 h-6 text-white" />
      </button>

      {/* Sidebar Navigation */}
      <nav
        className={`fixed left-0 top-0 h-full bg-[#1a1a1a] border-r border-[#2a2a2a] z-40 transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="w-64 md:w-20 lg:w-64 h-full flex flex-col p-4">
          {/* Logo */}
          <div className="mb-8 flex items-center gap-3">
            <div className="w-12 h-12 bg-[#0B6A41] rounded-xl flex items-center justify-center flex-shrink-0">
              <Activity className="w-7 h-7 text-white" />
            </div>
            <div className="block md:hidden lg:block">
              <h2 className="text-white font-bold text-lg">Analytics</h2>
              <p className="text-gray-400 text-xs">Coach Dashboard</p>
            </div>
          </div>

          {/* Navigation Items */}
          <div className="flex-1 space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setIsOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                    active
                      ? 'bg-[#0B6A41] text-white'
                      : 'text-gray-400 hover:bg-[#222] hover:text-white'
                  }`}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  <span className="block md:hidden lg:block font-medium">
                    {item.label}
                  </span>
                </Link>
              );
            })}
          </div>

          {/* Footer */}
          <div className="mt-auto pt-4 border-t border-[#2a2a2a]">
            <div className="px-4 py-3">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
                <span className="text-red-500 font-semibold text-sm block md:hidden lg:block">
                  LIVE
                </span>
              </div>
              <p className="text-xs text-gray-400 block md:hidden lg:block">
                U of S vs Calgary
              </p>
              <p className="text-xs text-gray-500 block md:hidden lg:block">
                62:34
              </p>
            </div>
          </div>
        </div>
      </nav>

      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/50 z-30"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
}
