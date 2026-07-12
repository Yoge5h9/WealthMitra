import type { ReactElement } from "react";
import { CartesianGrid, ResponsiveContainer } from "recharts";
import type { TooltipContentProps } from "recharts";
import { cn } from "@/lib/utils";

/**
 * Categorical series palette pulled from the structural/brand/semantic/
 * neutral ramps only — no indigo/violet anywhere. Ordered so
 * the first two series (structural teal, brand orange) carry the most
 * visual weight before falling back to semantic and neutral tones.
 */
export const CHART_COLORS = [
  "var(--color-structural-500)",
  "var(--color-brand-500)",
  "var(--color-success-500)",
  "var(--color-warning-500)",
  "var(--color-structural-300)",
  "var(--color-neutral-400)",
] as const;

export function chartColor(index: number): string {
  return CHART_COLORS[index % CHART_COLORS.length];
}

/** Minimal 1px neutral grid — horizontal only, no vertical clutter. */
export function ChartGrid() {
  return (
    <CartesianGrid
      stroke="var(--color-neutral-200)"
      strokeWidth={1}
      strokeDasharray="0"
      vertical={false}
    />
  );
}

interface ChartTickProps {
  x?: number;
  y?: number;
  payload?: { value: string | number };
}

/** Custom axis tick: UI font, tabular numerals, muted neutral ink. */
export function ChartTick({ x = 0, y = 0, payload }: ChartTickProps) {
  return (
    <text
      x={x}
      y={y}
      dy={12}
      textAnchor="middle"
      className="fill-neutral-500 tabular-nums"
      style={{ fontFamily: "var(--font-ui)", fontSize: 12 }}
    >
      {payload?.value ?? ""}
    </text>
  );
}

export interface ChartTooltipProps extends Partial<TooltipContentProps<number, string>> {
  /** Formats each series value, e.g. formatINR. Defaults to raw value. */
  valueFormatter?: (value: number) => string;
}

/** Flat, bordered tooltip (a floating layer, so shadow-float is correct here). */
export function ChartTooltip({ active, payload, label, valueFormatter }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="rounded-sm border border-neutral-200 bg-neutral-0 px-3 py-2 text-caption shadow-float-sm">
      {label !== undefined && (
        <p className="mb-1 font-medium text-neutral-700">{label}</p>
      )}
      <ul className="space-y-1">
        {payload.map((entry, index) => {
          const numericValue = typeof entry.value === "number" ? entry.value : Number(entry.value);
          return (
            <li key={`${entry.dataKey ?? entry.name ?? index}`} className="flex items-center gap-2">
              <span
                className="size-2 shrink-0 rounded-full"
                style={{ background: entry.color ?? chartColor(index) }}
              />
              <span className="text-neutral-600">{entry.name}</span>
              <span className="ml-auto tabular-nums font-medium text-neutral-800">
                {valueFormatter && Number.isFinite(numericValue)
                  ? valueFormatter(numericValue)
                  : entry.value}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export interface ChartContainerProps {
  children: ReactElement;
  /** Fixed pixel height — Recharts requires a bounded height ancestor. */
  height?: number;
  className?: string;
}

/** ResponsiveContainer wrapper with the app's default chart height. */
export function ChartContainer({ children, height = 280, className }: ChartContainerProps) {
  return (
    <div className={cn("w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}
