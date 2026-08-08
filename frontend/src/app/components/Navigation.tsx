"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Library, Menu, X } from "lucide-react";
import { useSocket } from "./SocketProvider";

const navItems = [
  { path: "/matches", label: "Matches", icon: Library },
  { path: "/", label: "Live", icon: Activity },
];

export function Navigation() {
  const pathname = usePathname();
  const { isConnected } = useSocket();
  const [mobileOpen, setMobileOpen] = useState(false);
  const isActive = (path: string) =>
    path === "/" ? pathname === "/" : pathname.startsWith(path);

  return (
    <header className="sticky top-0 z-40 w-full border-b border-zinc-800 bg-background">
      <div className="flex h-20 items-center px-4 md:px-6 gap-4 md:gap-8">
        {/* Left Section: Logo & Nav Links */}
        <div className="flex items-center gap-4 md:gap-8">
          <div className="flex items-center gap-3 pr-4 md:pr-8 border-r border-zinc-800">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white overflow-hidden border border-zinc-800">
              <img
                src="/university-of-saskatchewan.svg"
                alt="University of Saskatchewan Logo"
                className="w-full h-full object-contain"
              />
            </div>
            <div className="hidden sm:block">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-primary leading-none mb-1">
                Dashboard
              </p>
              <h2 className="text-sm font-black text-foreground tracking-tight uppercase leading-none">
                USASK Women&apos;s Soccer
              </h2>
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
                      ? "bg-primary/10 text-primary border border-primary/20"
                      : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span className="uppercase tracking-widest">
                    {item.label}
                  </span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right: live status + mobile menu button */}
        <div className="flex flex-1 items-center justify-end gap-2">
          <span
            className={`flex items-center gap-2 rounded-full border px-4 py-2 text-[10px] font-black uppercase tracking-[0.18em] ${
              isConnected
                ? "border-primary/30 bg-primary/10 text-primary"
                : "border-zinc-700 bg-card text-muted-foreground"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                isConnected ? "bg-primary animate-pulse" : "bg-zinc-600"
              }`}
            />
            {isConnected ? "Live feed" : "Offline"}
          </span>
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden flex h-10 w-10 items-center justify-center rounded-xl border border-zinc-800 text-muted-foreground hover:text-foreground"
            aria-label="Toggle navigation menu"
          >
            {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Mobile nav dropdown */}
      {mobileOpen && (
        <nav className="md:hidden border-t border-zinc-800 px-4 py-2 flex flex-col gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                href={item.path}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                  active
                    ? "bg-primary/10 text-primary border border-primary/20"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
