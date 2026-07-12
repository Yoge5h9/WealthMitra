import { ShieldCheck } from "lucide-react";
import { Tooltip } from "radix-ui";
import { cn } from "@/lib/utils";
import { t, type LanguageCode } from "@/lib/i18n";

export interface TrustFooterProps {
  className?: string;
  /** "full" (default) renders the standing full-width trust line. "minimal"
   * shrinks it to an unobtrusive icon-only cue (same message on hover/focus
   * via tooltip) — for surfaces tight on vertical space, e.g. the customer
   * chat composer bar. */
  variant?: "full" | "minimal";
  language?: LanguageCode;
}

/**
 * The standing trust cue every data-bearing surface carries —
 * every figure on screen is tool-computed, never a model guess.
 */
export function TrustFooter({ className, variant = "full", language = "en" }: TrustFooterProps) {
  if (variant === "minimal") {
    return (
      <div className={cn("flex justify-center border-t border-neutral-200 py-1.5", className)}>
        <Tooltip.Provider delayDuration={200}>
          <Tooltip.Root>
            <Tooltip.Trigger asChild>
              <button
                type="button"
                aria-label={t(language, "trust.tooltip")}
                className="flex size-8 items-center justify-center rounded-full text-neutral-400 transition-colors duration-[var(--motion-micro)] ease-out hover:text-structural-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
              >
                <ShieldCheck size={15} strokeWidth={1.75} aria-hidden="true" />
              </button>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                side="top"
                sideOffset={6}
                className="z-50 max-w-64 rounded-sm border border-neutral-200 bg-neutral-0 px-3 py-2 text-caption text-neutral-700 shadow-float-md"
              >
                {t(language, "trust.tooltip")}
                <Tooltip.Arrow className="fill-neutral-0" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        </Tooltip.Provider>
      </div>
    );
  }

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
      <span>{t(language, "trust.full")}</span>
    </div>
  );
}
