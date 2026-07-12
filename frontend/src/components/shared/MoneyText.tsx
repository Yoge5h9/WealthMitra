import { ArrowDownRight, ArrowUpRight, Info } from "lucide-react";
import { Tooltip } from "radix-ui";
import { cn } from "@/lib/utils";
import { formatDelta, formatINR, type FormatInrOptions } from "@/lib/format";

export type MoneyTextSize = "sm" | "md" | "lg" | "xl" | "hero";

const SIZE_CLASSES: Record<MoneyTextSize, string> = {
  sm: "text-body-sm font-medium",
  md: "text-body font-semibold",
  lg: "text-h4 font-semibold",
  xl: "text-h2 font-display font-bold",
  // The hero net-worth figure alone uses the display face (Space Grotesk) —
  // every other money figure stays on IBM Plex Sans for its real tabular
  // lining digits.
  hero: "text-display font-display font-bold",
};

const DELTA_TEXT_CLASSES: Record<MoneyTextSize, string> = {
  sm: "text-caption",
  md: "text-body-sm",
  lg: "text-body-sm",
  xl: "text-body",
  hero: "text-lg",
};

export interface MoneyTextProps {
  value: number;
  size?: MoneyTextSize;
  compact?: FormatInrOptions["compact"];
  /** Rupee delta since a reference period (e.g. last month). */
  delta?: number;
  /** Percent delta — mutually exclusive with `delta` (percent wins if both given). */
  deltaPercent?: number;
  /** Tap/hover affordance explaining where this number came from (§12 trust cues). */
  whyThisNumber?: string;
  className?: string;
}

export function MoneyText({
  value,
  size = "md",
  compact = false,
  delta,
  deltaPercent,
  whyThisNumber,
  className,
}: MoneyTextProps) {
  const hasDelta = delta !== undefined || deltaPercent !== undefined;
  const deltaInfo = hasDelta
    ? deltaPercent !== undefined
      ? formatDelta(deltaPercent, { percent: true })
      : formatDelta(delta ?? 0, { compact })
    : null;

  return (
    // `flex` (not `inline-flex`) so consecutive MoneyText siblings stack as
    // separate rows under a parent's `space-y-*` — the overwhelmingly common
    // usage (stat rows, hero figures, table cells) rather than mid-sentence.
    <span className={cn("flex items-baseline gap-2", className)}>
      <span className={cn("tabular-nums", SIZE_CLASSES[size])}>
        {formatINR(value, { compact })}
      </span>

      {deltaInfo && deltaInfo.direction !== "flat" && (
        <span
          className={cn(
            "inline-flex items-center gap-1 font-medium tabular-nums",
            DELTA_TEXT_CLASSES[size],
            deltaInfo.direction === "up" ? "text-success-600" : "text-danger-600"
          )}
        >
          {deltaInfo.direction === "up" ? (
            <ArrowUpRight size={14} strokeWidth={2} aria-hidden="true" />
          ) : (
            <ArrowDownRight size={14} strokeWidth={2} aria-hidden="true" />
          )}
          {deltaInfo.formatted}
        </span>
      )}

      {whyThisNumber && (
        <Tooltip.Provider delayDuration={200}>
          <Tooltip.Root>
            <Tooltip.Trigger asChild>
              <button
                type="button"
                aria-label="Why this number"
                className="inline-flex size-5 shrink-0 items-center justify-center rounded-full text-neutral-500 transition-colors duration-[var(--motion-micro)] ease-out hover:text-structural-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
              >
                <Info size={14} strokeWidth={1.75} />
              </button>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                side="top"
                sideOffset={6}
                className="z-50 max-w-64 rounded-sm border border-neutral-200 bg-neutral-0 px-3 py-2 text-caption text-neutral-700 shadow-float-md"
              >
                {whyThisNumber}
                <Tooltip.Arrow className="fill-neutral-0" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        </Tooltip.Provider>
      )}
    </span>
  );
}
