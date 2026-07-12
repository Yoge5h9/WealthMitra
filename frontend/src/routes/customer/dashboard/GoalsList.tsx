import { Target } from "lucide-react";
import { DataState } from "@/components/shared/DataState";
import { formatINR } from "@/lib/format";
import type { GoalEntry } from "./types";

export interface GoalsListProps {
  goals: GoalEntry[];
}

export function GoalsList({ goals }: GoalsListProps) {
  return (
    <DataState
      status={goals.length === 0 ? "empty" : "success"}
      emptyIcon={Target}
      emptyTitle="No goals set yet"
      emptyDescription="Goals you set in chat will show their progress here."
    >
      <ul className="space-y-3">
        {goals.map((goal) => {
          const pct = Math.min(Math.round(goal.progress_ratio * 100), 100);
          return (
            <li key={goal.name} className="rounded-lg border border-neutral-200 p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-700">
                    <Target size={15} strokeWidth={1.75} aria-hidden="true" />
                  </span>
                  <div>
                    <p className="text-body-sm font-medium text-neutral-900">{goal.name}</p>
                    <p className="text-caption text-neutral-500">{goal.horizon_years}-year horizon</p>
                  </div>
                </div>
                <span className="shrink-0 text-body-sm font-semibold tabular-nums text-neutral-900">{pct}%</span>
              </div>

              <div className="mt-2.5 h-2 w-full overflow-hidden rounded-full bg-neutral-100" aria-hidden="true">
                <div
                  className="h-full rounded-full bg-brand-500 transition-[width] duration-[var(--motion-screen)] ease-out"
                  style={{ width: `${pct}%` }}
                />
              </div>

              <div className="mt-2 flex items-center justify-between text-caption text-neutral-600">
                <span className="tabular-nums">
                  {formatINR(goal.saved_so_far, { compact: true })} of {formatINR(goal.target, { compact: true })}
                </span>
                <span className="tabular-nums">need {formatINR(goal.monthly_required_inr, { compact: true })}/mo</span>
              </div>
            </li>
          );
        })}
      </ul>
    </DataState>
  );
}
