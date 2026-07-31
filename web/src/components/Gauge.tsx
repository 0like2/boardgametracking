type Props = {
  label: string;
  value: number | null;
  max: number;
  color: string;
  /** Tick labels drawn above the rail, as on the printed card. */
  ticks?: number[];
  compact?: boolean;
};

export function Gauge({ label, value, max, color, ticks, compact }: Props) {
  const pct = value == null ? 0 : Math.max(0, Math.min(100, (value / max) * 100));

  return (
    <div className="flex items-center gap-2.5">
      <span
        className={`shrink-0 text-ink-dim ${compact ? "text-[10px]" : "text-xs"}`}
      >
        {label}
      </span>

      <div className="relative min-w-0 flex-1">
        {ticks && !compact && (
          <div className="mb-0.5 flex justify-between px-px text-[9px] leading-none text-ink-faint tnum">
            {ticks.map((t) => (
              <span key={t}>{t}</span>
            ))}
          </div>
        )}
        <div
          className={`w-full overflow-hidden rounded-full bg-line ${
            compact ? "h-1" : "h-1.5"
          }`}
        >
          <div
            className="h-full rounded-full transition-[width] duration-500"
            style={{ width: `${pct}%`, background: color }}
          />
        </div>
      </div>

      <span
        className={`shrink-0 font-bold tnum ${compact ? "text-xs" : "text-base"}`}
        style={{ color: value == null ? "var(--ink-faint)" : color }}
      >
        {value == null ? "—" : value.toFixed(1)}
      </span>
    </div>
  );
}
