import { cn } from "@/lib/utils";
import { priorityBand, PRIORITY_BAND_LABEL, type PriorityBand } from "./priority";

const BAND_CLASSES: Record<PriorityBand, string> = {
  hot: "border-danger-200 bg-danger-50 text-danger-700",
  warm: "border-warning-200 bg-warning-50 text-warning-700",
  standard: "border-structural-200 bg-structural-50 text-structural-700",
};

const BAND_DOT_CLASSES: Record<PriorityBand, string> = {
  hot: "bg-danger-500",
  warm: "bg-warning-500",
  standard: "bg-structural-500",
};

export interface PriorityChipProps {
  score: number;
  className?: string;
}

/** Priority-score pill, banded ≥70 hot / 40-69 warm / <40 standard (semantic colors, never brand). */
export function PriorityChip({ score, className }: PriorityChipProps) {
  const band = priorityBand(score);
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-full border px-3 py-1 text-caption font-semibold tabular-nums",
        BAND_CLASSES[band],
        className
      )}
    >
      <span className={cn("size-1.5 rounded-full", BAND_DOT_CLASSES[band])} aria-hidden="true" />
      {score} · {PRIORITY_BAND_LABEL[band]}
    </span>
  );
}
