import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { AlertTriangle, Inbox, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export type DataStateStatus = "loading" | "empty" | "error" | "success";

export interface DataStateAction {
  label: string;
  onClick: () => void;
}

export interface DataStateProps {
  status: DataStateStatus;
  children: ReactNode;
  /** Custom skeleton shaped like the real content. Falls back to a generic card skeleton. */
  skeleton?: ReactNode;
  emptyIcon?: LucideIcon;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: DataStateAction;
  errorTitle?: string;
  errorDescription?: string;
  onRetry?: () => void;
  className?: string;
}

function DefaultSkeleton() {
  return (
    <div className="animate-pulse space-y-3" aria-hidden="true">
      <div className="h-5 w-1/3 rounded-sm bg-neutral-200" />
      <div className="h-4 w-full rounded-sm bg-neutral-100" />
      <div className="h-4 w-5/6 rounded-sm bg-neutral-100" />
      <div className="flex gap-3 pt-1">
        <div className="h-16 flex-1 rounded-lg bg-neutral-100" />
        <div className="h-16 flex-1 rounded-lg bg-neutral-100" />
        <div className="h-16 flex-1 rounded-lg bg-neutral-100" />
      </div>
    </div>
  );
}

/**
 * Enforces the four mandatory data states for every
 * data-bearing view: loading / empty / error / populated. Views wrap
 * their query results in this instead of hand-rolling ad-hoc spinners.
 */
export function DataState({
  status,
  children,
  skeleton,
  emptyIcon: EmptyIcon = Inbox,
  emptyTitle = "Nothing here yet",
  emptyDescription,
  emptyAction,
  errorTitle = "Couldn't load this",
  errorDescription = "Something went wrong on our side. Your data is safe — try again.",
  onRetry,
  className,
}: DataStateProps) {
  if (status === "loading") {
    return <div className={className}>{skeleton ?? <DefaultSkeleton />}</div>;
  }

  if (status === "empty") {
    return (
      <div
        className={cn(
          "flex flex-col items-center gap-3 rounded-lg border border-dashed border-neutral-200 px-6 py-8 text-center",
          className
        )}
      >
        <span className="flex size-11 items-center justify-center rounded-full bg-neutral-100 text-neutral-500">
          <EmptyIcon size={20} strokeWidth={1.75} />
        </span>
        <div className="space-y-1">
          <p className="text-body-sm font-medium text-neutral-700">{emptyTitle}</p>
          {emptyDescription && (
            <p className="max-w-xs text-caption text-neutral-600">{emptyDescription}</p>
          )}
        </div>
        {emptyAction && (
          <Button size="touch" variant="outline" onClick={emptyAction.onClick}>
            {emptyAction.label}
          </Button>
        )}
      </div>
    );
  }

  if (status === "error") {
    return (
      <div
        className={cn(
          "flex flex-col items-center gap-3 rounded-lg border border-neutral-200 bg-neutral-50 px-6 py-8 text-center",
          className
        )}
      >
        <span className="flex size-11 items-center justify-center rounded-full bg-danger-50 text-danger-600">
          <AlertTriangle size={20} strokeWidth={1.75} />
        </span>
        <div className="space-y-1">
          <p className="text-body-sm font-medium text-neutral-700">{errorTitle}</p>
          <p className="max-w-xs text-caption text-neutral-600">{errorDescription}</p>
        </div>
        {onRetry && (
          <Button size="touch" variant="outline" className="gap-2" onClick={onRetry}>
            <RotateCcw size={16} strokeWidth={1.75} />
            Try again
          </Button>
        )}
      </div>
    );
  }

  return <>{children}</>;
}
