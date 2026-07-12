import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface SectionHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

/** Left-aligned section header with the display face — never centered. */
export function SectionHeader({ eyebrow, title, description, action, className }: SectionHeaderProps) {
  return (
    <div className={cn("flex items-start justify-between gap-4", className)}>
      <div>
        {eyebrow && (
          <span className="text-caption font-semibold uppercase tracking-wide text-structural-600">
            {eyebrow}
          </span>
        )}
        <h2 className="mt-1 font-display text-h3 font-semibold tracking-tight text-neutral-900">
          {title}
        </h2>
        {description && (
          <p className="mt-1 max-w-2xl text-body-sm text-neutral-600">{description}</p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
