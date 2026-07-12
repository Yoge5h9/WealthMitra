import { ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TrustFooterProps {
  className?: string;
}

/**
 * The standing trust cue every data-bearing surface carries —
 * every figure on screen is tool-computed, never a model guess.
 */
export function TrustFooter({ className }: TrustFooterProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 border-t border-neutral-200 px-4 py-3 text-caption text-neutral-600",
        className
      )}
    >
      <ShieldCheck
        size={16}
        strokeWidth={1.75}
        className="shrink-0 text-structural-600"
        aria-hidden="true"
      />
      <span>Every figure computed from your data · tap any number to see why</span>
    </div>
  );
}
