/**
 * Two-team comparison row in the style of a broadcast stat block:
 *   value0  LABEL  value1, with a proportional green/gold split bar.
 */
export function StatCompareBar({
  label,
  value0,
  value1,
  muted = false,
}: {
  label: string;
  value0: number | string;
  value1: number | string;
  /** Muted row = metric unavailable yet (values shown as-is, no bar). */
  muted?: boolean;
}) {
  const n0 = typeof value0 === "number" ? value0 : NaN;
  const n1 = typeof value1 === "number" ? value1 : NaN;
  const total = n0 + n1;
  const ratio0 = !muted && Number.isFinite(total) && total > 0 ? n0 / total : 0.5;

  return (
    <div className={muted ? "opacity-40" : ""}>
      <div className="flex items-baseline justify-between stat-numerals">
        <span className="text-sm font-black text-primary">{value0}</span>
        <span className="text-[9px] font-black uppercase tracking-[0.18em] text-muted-foreground">
          {label}
        </span>
        <span className="text-sm font-black text-secondary">{value1}</span>
      </div>
      {!muted && (
        <div className="mt-1 flex h-1 overflow-hidden rounded-full bg-zinc-800">
          <div
            className="bg-primary transition-all duration-500"
            style={{ width: `${ratio0 * 100}%` }}
          />
          <div className="flex-1 bg-secondary/70 transition-all duration-500" />
        </div>
      )}
    </div>
  );
}
