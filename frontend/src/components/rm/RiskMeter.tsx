import { cn } from "@/lib/utils";

export interface RiskMeterProps {
  capacityScore: number;
  toleranceScore: number;
  band: string;
  className?: string;
}

const BAND_CHIP_CLASSES: Record<string, string> = {
  conservative: "border-structural-200 bg-structural-50 text-structural-700",
  moderate: "border-structural-300 bg-structural-100 text-structural-800",
  growth: "border-structural-500 bg-structural-600 text-neutral-0",
};

function clampPct(score: number): number {
  return Math.max(0, Math.min(100, score));
}

/**
 * Twin capacity/tolerance bars, both on the same 0–100 scale, so the lower
 * of the two — the one that actually governs `risk_band = f(min(capacity,
 * tolerance))` (backend `app/analytics/risk.py`) — is visually obvious
 * without needing a separate computed "effective score" field.
 */
export function RiskMeter({ capacityScore, toleranceScore, band, className }: RiskMeterProps) {
  const limiting = capacityScore <= toleranceScore ? "capacity" : "tolerance";
  const bandChipClass = BAND_CHIP_CLASSES[band] ?? BAND_CHIP_CLASSES.moderate;

  return (
    <div className={cn("space-y-3", className)}>
      <div className="space-y-2">
        <div className="space-y-1">
          <div className="flex items-center justify-between text-caption text-neutral-600">
            <span className="font-medium text-neutral-800">
              Capacity {limiting === "capacity" && <span className="text-structural-700">(limiting)</span>}
            </span>
            <span className="tabular-nums">{capacityScore}/100</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-100">
            <div
              className="h-full rounded-full bg-structural-600"
              style={{ width: `${clampPct(capacityScore)}%` }}
            />
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex items-center justify-between text-caption text-neutral-600">
            <span className="font-medium text-neutral-800">
              Tolerance {limiting === "tolerance" && <span className="text-structural-700">(limiting)</span>}
            </span>
            <span className="tabular-nums">{toleranceScore}/100</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-100">
            <div
              className="h-full rounded-full bg-structural-300"
              style={{ width: `${clampPct(toleranceScore)}%` }}
            />
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-2">
        <p className="text-caption text-neutral-500">
          Band set by <span className="tabular-nums font-medium text-neutral-700">min(capacity, tolerance)</span>
        </p>
        <span className={cn("shrink-0 rounded-full border px-3 py-1 text-caption font-semibold capitalize", bandChipClass)}>
          {band}
        </span>
      </div>
    </div>
  );
}
