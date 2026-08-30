"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Library, Menu, X } from "lucide-react";

export function Navigation({ mode }: { mode: "live" | "test" | "replay" }) {
  const navItems = [
    ...(mode === "live" ? [] : [{ path: "/matches", label: "Matches", icon: Library }]),
    { path: "/", label: "Live", icon: Activity },
  ];
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const isActive = (path: string) =>
    path === "/" ? pathname === "/" : pathname.startsWith(path);

  return (
    <header className="sticky top-0 z-40 w-full border-b border-white/10 bg-background/90 backdrop-blur-xl">
      <div className="app-container flex h-16 items-center gap-5">
        <Link href="/" className="flex min-w-0 items-center gap-3 sm:pr-5">
          <div className="grid h-9 w-9 shrink-0 place-items-center overflow-hidden rounded-sm bg-white p-1">
            <Image
              src="/university-of-saskatchewan.svg"
              alt="University of Saskatchewan"
              width={40}
              height={40}
              priority
            />
          </div>
          <div className="hidden min-w-0 border-l border-white/15 pl-3 sm:block">
            <p className="eyebrow text-primary">
              USask soccer
            </p>
            <p className="mt-1 truncate font-display text-lg font-semibold uppercase leading-none tracking-[0.04em] text-white">
              Game Analysis
            </p>
          </div>
        </Link>

        <nav className="hidden h-full items-stretch md:flex">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);

            return (
              <Link
                key={item.path}
                href={item.path}
                aria-current={active ? "page" : undefined}
                className={`relative flex items-center gap-2 px-4 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] transition-colors ${
                  active ? "text-white" : "text-muted-foreground hover:text-white"
                }`}
              >
                <Icon className={`h-3.5 w-3.5 ${active ? "text-primary" : ""}`} />
                {item.label}
                {active && <span className="absolute inset-x-4 bottom-0 h-0.5 bg-primary" />}
              </Link>
            );
          })}
        </nav>

        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="ml-auto flex h-9 w-9 items-center justify-center rounded-sm border border-white/10 text-muted-foreground transition hover:text-white md:hidden"
          aria-label="Toggle navigation menu"
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </button>
      </div>

      {mobileOpen && (
        <div className="border-t border-white/10 md:hidden">
          <nav className="app-container py-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);
              return (
                <Link
                  key={item.path}
                  href={item.path}
                  aria-current={active ? "page" : undefined}
                  onClick={() => setMobileOpen(false)}
                  className={`flex items-center gap-3 rounded-sm px-3 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] transition ${
                    active
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-white/[0.04] hover:text-white"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      )}
    </header>
  );
}
