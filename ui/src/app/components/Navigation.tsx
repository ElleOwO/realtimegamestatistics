'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity,
  BarChart3,
  FileText,
  ShieldCheck,
  TimerReset,
  Users,
  LayoutGrid,
} from 'lucide-react';

const navItems = [
  { path: '/', label: 'Overview', icon: Activity },
  { path: '/players', label: 'Squad', icon: Users },
  { path: '/stats', label: 'Stats', icon: BarChart3 },
];

export function Navigation() {
  const pathname = usePathname();
  const isActive = (path: string) => (path === '/' ? pathname === '/' : pathname.startsWith(path));

  return (
    <header className="sticky top-0 z-40 w-full border-b border-zinc-800 bg-background/95 backdrop-blur">
      <div className="flex h-16 items-center px-4 md:px-6 gap-6">
        <div className="flex items-center gap-3 pr-6 border-r border-zinc-800">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600 text-white">
            <LayoutGrid className="h-4 w-4" />
          </div>
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-emerald-500">RTGS v2.4</p>
            <h2 className="text-sm font-black text-zinc-100 tracking-tight uppercase">Command</h2>
          </div>
        </div>

        <nav className="flex items-center gap-1 flex-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);

            return (
              <Link
                key={item.path}
                href={item.path}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-bold transition-colors ${
                  active
                    ? 'bg-emerald-600/10 text-emerald-500'
                    : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden md:inline-block uppercase tracking-tight">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-4 border-l border-zinc-800 pl-6">
          <div className="hidden md:flex items-center gap-2 text-emerald-500">
            <ShieldCheck className="h-4 w-4" />
            <span className="text-[9px] font-black uppercase tracking-widest">Feed Secure</span>
          </div>
          <div className="flex items-center gap-3">
             <div className="text-right hidden sm:block">
                <p className="text-[9px] font-black uppercase tracking-widest text-zinc-400">Target Match</p>
                <p className="text-xs font-black text-zinc-100 uppercase tracking-tight">US vs Calgary</p>
             </div>
             <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-600/10 border border-emerald-600/20">
                <TimerReset className="h-3 w-3 text-emerald-500" />
                <span className="text-[10px] font-black text-emerald-500">62:34'</span>
             </div>
          </div>
        </div>
      </div>
    </header>
  );
}
