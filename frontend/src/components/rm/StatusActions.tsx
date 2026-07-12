import { Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { LeadStatus } from "@/lib/types";

const STAGES: LeadStatus[] = ["new", "contacted", "converted"];
const STAGE_LABEL: Record<LeadStatus, string> = { new: "New", contacted: "Contacted", converted: "Converted" };

export interface StatusActionsProps {
  status: LeadStatus;
  onChange: (status: LeadStatus) => void;
  pending?: boolean;
  className?: string;
}

/**
 * New → Contacted → Converted stepper. Only the immediate next stage renders
 * as the brand-colored primary action — one primary action per
 * screen; earlier/current stages stay secondary/ghost so an RM can still
 * correct a mis-click without a second orange button competing for attention.
 */
export function StatusActions({ status, onChange, pending = false, className }: StatusActionsProps) {
  const currentIndex = STAGES.indexOf(status);

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      {STAGES.map((stage, index) => {
        const isCurrent = stage === status;
        const isNext = index === currentIndex + 1;

        return (
          <Button
            key={stage}
            type="button"
            size="touch"
            variant={isCurrent ? "secondary" : isNext ? "default" : "outline"}
            disabled={pending || isCurrent}
            onClick={() => onChange(stage)}
            className="gap-2"
          >
            {isCurrent && <Check size={16} strokeWidth={2} aria-hidden="true" />}
            {STAGE_LABEL[stage]}
          </Button>
        );
      })}
      {pending && (
        <span className="inline-flex items-center gap-1 text-caption text-neutral-500">
          <Loader2 size={14} strokeWidth={2} className="animate-spin" aria-hidden="true" />
          Updating…
        </span>
      )}
    </div>
  );
}
