import type { ReactNode } from "react";

/** Shared card shell for the six live-dashboard panels. */
export function Panel({
  title,
  badge,
  children,
  className,
  bodyClassName,
}: {
  title: string;
  badge?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section
      className={`rounded-xl border border-zinc-800 bg-card ${className ?? ""}`}
    >
      <header className="flex items-center justify-between gap-2 border-b border-zinc-800/60 px-4 py-2.5">
        <h3 className="text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">
          {title}
        </h3>
        {badge}
      </header>
      <div className={`px-4 py-3 ${bodyClassName ?? ""}`}>{children}</div>
    </section>
  );
}

/** Data is computed live from the payload stream. */
export function LiveBadge() {
  return (
    <span className="rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-[9px] font-black uppercase tracking-widest text-primary">
      Live
    </span>
  );
}

/** Metric is specified but needs a backend payload extension. */
export function PendingBadge() {
  return (
    <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[9px] font-black uppercase tracking-widest text-amber-400">
      Pending backend
    </span>
  );
}

/** Honest empty state shown when no payload has arrived. */
export function EmptyState({ hint }: { hint?: string }) {
  return (
    <p className="py-2 text-center text-xs text-muted-foreground">
      Waiting for live feed…
      {hint && <span className="mt-1 block text-[10px] opacity-70">{hint}</span>}
    </p>
  );
}
