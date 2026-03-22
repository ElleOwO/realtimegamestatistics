'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity,
  BarChart3,
  ShieldCheck,
  TimerReset,
  Users,
  TrendingUp,
} from 'lucide-react';
import { Badge } from './ui/badge';

const navItems = [
  { path: '/', label: 'Overview', icon: Activity },
  { path: '/players', label: 'Squad', icon: Users },
  { path: '/stats', label: 'Stats', icon: BarChart3 },
];

export function Navigation() {
  const pathname = usePathname();
  const isActive = (path: string) => (path === '/' ? pathname === '/' : pathname.startsWith(path));

  return (
    <header className="sticky top-0 z-40 w-full border-b border-zinc-800 bg-background">
      <div className="flex h-20 items-center px-4 md:px-6 gap-8">
        {/* Left Section: Logo & Nav Links */}
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-3 pr-8 border-r border-zinc-800">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white overflow-hidden border border-zinc-800">
              <img 
                src="/university-of-saskatchewan.svg" 
                alt="University of Saskatchewan Logo" 
                className="w-full h-full object-contain"
              />
            </div>
            <div className="hidden sm:block">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-emerald-500 leading-none mb-1">RTGS v2.4</p>
              <h2 className="text-sm font-black text-zinc-100 tracking-tight uppercase leading-none">Command</h2>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);

              return (
                <Link
                  key={item.path}
                  href={item.path}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-black transition-all ${
                    active
                      ? 'bg-emerald-600/10 text-emerald-500 border border-emerald-600/20'
                      : 'text-zinc-500 hover:bg-zinc-800/50 hover:text-zinc-200'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span className="uppercase tracking-widest">{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right Section: Score & Stats (Pushed to end) */}
        <div className="flex items-center gap-8 flex-1 justify-end">
          {/* Stats Segment */}
          <div className="hidden lg:flex items-center gap-6 px-8 h-10 border-r border-zinc-800">
            <div className="flex flex-col">
              <div className="flex items-center gap-2 mb-0.5">
                <TrendingUp className="w-3 h-3 text-emerald-500" />
                <span className="text-[9px] font-black uppercase tracking-widest text-zinc-500">Momentum</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-20 h-1.5 bg-zinc-800 rounded-full overflow-hidden flex">
                  <div className="h-full bg-emerald-500 w-[62%]" />
                </div>
                <span className="text-[10px] font-black text-zinc-300">+12.4%</span>
              </div>
            </div>
            <div className="flex flex-col border-l border-zinc-800 pl-6">
              <span className="text-[9px] font-black uppercase tracking-widest text-zinc-500 mb-0.5">Team xG</span>
              <span className="text-xs font-black text-emerald-500">1.84</span>
            </div>
          </div>

          {/* Score Segment */}
          <div className="flex items-center gap-4 bg-zinc-900/50 px-5 py-2.5 rounded-2xl border border-zinc-800">
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-full bg-zinc-100 text-zinc-900 flex items-center justify-center font-black text-[10px] border border-zinc-300">US</div>
              <span className="text-xl font-black tracking-tighter text-white">2</span>
            </div>
            <div className="text-zinc-700 font-bold text-sm">VS</div>
            <div className="flex items-center gap-3">
              <span className="text-xl font-black tracking-tighter text-white">1</span>
              <div className="w-7 h-7 rounded-full bg-zinc-800 text-zinc-400 flex items-center justify-center font-black text-[10px] border border-zinc-700">CG</div>
            </div>
          </div>

          {/* Status & Time Segment */}
          <div className="flex items-center gap-4 border-l border-zinc-800 pl-8">
            <div className="hidden xl:flex flex-col items-end">
              <div className="flex items-center gap-1.5 text-emerald-500 mb-0.5">
                <ShieldCheck className="h-3 w-3" />
                <span className="text-[9px] font-black uppercase tracking-widest">Feed Secure</span>
              </div>
              <Badge className="bg-emerald-600/10 text-emerald-500 border-none text-[8px] font-black uppercase h-4 px-1.5">Live</Badge>
            </div>
            <div className="flex items-center gap-2.5 px-4 py-2 rounded-xl bg-zinc-900 border border-zinc-800">
              <TimerReset className="h-4 w-4 text-emerald-500" />
              <span className="text-sm font-black font-mono text-zinc-100 tracking-wider">62:34</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
