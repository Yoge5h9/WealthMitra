/**
 * Formatting helpers for money, deltas, and dates — the app's single
 * source of truth for Indian digit grouping and lakh/crore shorthand.
 */

const inrGrouped = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 0,
});

const inrCompact = new Intl.NumberFormat("en-IN", {
  notation: "compact",
  maximumFractionDigits: 1,
});

export interface FormatInrOptions {
  /** Use lakh/crore shorthand (₹1.2L / ₹2.4Cr) for space-tight spots. */
  compact?: boolean;
}

/**
 * Formats a rupee amount with Indian digit grouping, e.g. `123456` ->
 * `₹1,23,456`. Pass `{ compact: true }` for lakh/crore shorthand, e.g.
 * `2400000` -> `₹24L` (Intl's `en-IN` compact notation natively emits
 * "L"/"Cr"/"T" suffixes, so no manual lakh/crore math is needed here).
 */
export function formatINR(amount: number, options: FormatInrOptions = {}): string {
  if (!Number.isFinite(amount)) return "₹—";
  const sign = amount < 0 ? "-" : "";
  const abs = Math.abs(amount);
  const body = options.compact ? inrCompact.format(abs) : inrGrouped.format(abs);
  return `${sign}₹${body}`;
}

export type DeltaDirection = "up" | "down" | "flat";

export interface DeltaInfo {
  /** For choosing an arrow icon (ArrowUpRight/ArrowDownRight) and semantic color. */
  direction: DeltaDirection;
  /** Explicit sign — never rely on color alone (§9/§11 anti-slop). */
  sign: "+" | "-" | "";
  /** Ready-to-render string, e.g. "+₹12,340" or "+4.2%". */
  formatted: string;
}

export interface FormatDeltaOptions extends FormatInrOptions {
  /** Render as a percentage instead of a rupee amount. */
  percent?: boolean;
  /** Decimal places for percentage mode (default 1). */
  percentDigits?: number;
}

/**
 * Turns a signed change (rupees or percent) into direction + explicit sign
 * + a formatted string, so callers (MoneyText, chart tooltips, RM cards)
 * never have to re-derive color/arrow logic themselves.
 */
export function formatDelta(value: number, options: FormatDeltaOptions = {}): DeltaInfo {
  if (!Number.isFinite(value) || value === 0) {
    const magnitude = options.percent
      ? `${(0).toFixed(options.percentDigits ?? 1)}%`
      : formatINR(0, options);
    return { direction: "flat", sign: "", formatted: magnitude };
  }

  const direction: DeltaDirection = value > 0 ? "up" : "down";
  const sign: "+" | "-" = value > 0 ? "+" : "-";
  const abs = Math.abs(value);
  const magnitude = options.percent
    ? `${abs.toFixed(options.percentDigits ?? 1)}%`
    : formatINR(abs, options).replace("₹", "₹");

  return { direction, sign, formatted: `${sign}${magnitude}` };
}

export interface FormatDateOptions {
  /** Include a 24h time component, e.g. "12 Jul 2026, 14:05". */
  withTime?: boolean;
}

const dateOnlyFormatter = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

const dateTimeFormatter = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

/** Formats an ISO date/datetime string as en-IN, e.g. "12 Jul 2026". */
export function formatDate(iso: string, options: FormatDateOptions = {}): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "—";
  return (options.withTime ? dateTimeFormatter : dateOnlyFormatter).format(parsed);
}
