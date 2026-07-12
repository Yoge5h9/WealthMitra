import { Target } from "lucide-react";
import { DataState } from "@/components/shared/DataState";
import { formatINR } from "@/lib/format";
import { t, type LanguageCode } from "@/lib/i18n";
import type { GoalEntry } from "./types";

export interface GoalsListProps {
  goals: GoalEntry[];
  language: LanguageCode;
}

export function GoalsList({ goals, language }: GoalsListProps) {
  return (
    <DataState
      status={goals.length === 0 ? "empty" : "success"}
      emptyIcon={Target}
      emptyTitle={t(language, "dashboard.goals.empty")}
      emptyDescription={t(language, "dashboard.goals.emptyDesc")}
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
                    <p className="text-caption text-neutral-500">
                      {t(language, "dashboard.goals.horizon", { years: goal.horizon_years })}
                    </p>
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
                  {t(language, "dashboard.goals.progress", {
                    saved: formatINR(goal.saved_so_far, { compact: true }),
                    target: formatINR(goal.target, { compact: true }),
                  })}
                </span>
                <span className="tabular-nums">
                  {t(language, "dashboard.goals.need", { amount: formatINR(goal.monthly_required_inr, { compact: true }) })}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </DataState>
  );
}
