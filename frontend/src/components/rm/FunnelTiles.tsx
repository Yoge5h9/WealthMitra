import { ChevronRight, CircleDot, PhoneCall, Trophy } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LeadStatus } from "@/lib/types";

export interface FunnelTilesProps {
  counts: Record<LeadStatus, number>;
  className?: string;
}

// Icon-circle fills use the 600 shades: white 14px icons on the 500 shades
// sit below the 3:1 small-icon contrast floor (warning-500 is ~2.1:1).
const STAGES: { status: LeadStatus; label: string; icon: typeof CircleDot; accent: string; dot: string }[] = [
  { status: "new", label: "New", icon: CircleDot, accent: "border-structural-200", dot: "bg-structural-600" },
  { status: "contacted", label: "Contacted", icon: PhoneCall, accent: "border-warning-200", dot: "bg-warning-600" },
  { status: "converted", label: "Converted", icon: Trophy, accent: "border-success-200", dot: "bg-success-600" },
];

/** New → Contacted → Converted pipeline summary, updated live as statuses change. */
export function FunnelTiles({ counts, className }: FunnelTilesProps) {
  return (
    <div className={cn("flex min-w-0 items-stretch gap-1.5", className)}>
      {STAGES.map((stage, index) => (
        <div key={stage.status} className="flex min-w-0 flex-1 items-center gap-1.5">
          <div
            className={cn(
              "flex min-w-0 flex-1 items-center gap-2 rounded-lg border bg-neutral-0 px-2.5 py-2",
              stage.accent
            )}
          >
            <span className={cn("flex size-6 shrink-0 items-center justify-center rounded-full", stage.dot)}>
              <stage.icon size={13} strokeWidth={2} className="text-neutral-0" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <p className="text-body font-display font-semibold leading-none tabular-nums text-neutral-900">
                {counts[stage.status]}
              </p>
              <p className="mt-0.5 truncate text-caption text-neutral-600">{stage.label}</p>
            </div>
          </div>
          {index < STAGES.length - 1 && (
            <ChevronRight size={14} strokeWidth={1.75} className="shrink-0 text-neutral-300" aria-hidden="true" />
          )}
        </div>
      ))}
    </div>
  );
}
