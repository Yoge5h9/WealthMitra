import { cn } from "@/lib/utils";
import type { LeadFamily } from "@/lib/types";
import { FAMILY_LABEL, LOANS_TAGLINE } from "./text";

export type FamilyFilter = "all" | LeadFamily;

const TABS: { value: FamilyFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "investment_insurance", label: FAMILY_LABEL.investment_insurance },
  { value: "loans_cards", label: FAMILY_LABEL.loans_cards },
];

export interface FamilyTabsProps {
  value: FamilyFilter;
  onChange: (value: FamilyFilter) => void;
  counts: Record<FamilyFilter, number>;
  className?: string;
}

/** Family filter tabs — All / Investments & Insurance / Loans & Cards. */
export function FamilyTabs({ value, onChange, counts, className }: FamilyTabsProps) {
  return (
    <div className={className}>
      <div role="tablist" aria-label="Filter leads by family" className="flex items-center gap-1">
        {TABS.map((tab) => {
          const isActive = tab.value === value;
          return (
            <button
              key={tab.value}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => onChange(tab.value)}
              className={cn(
                "rounded-sm px-3 py-2 text-body-sm font-medium transition-colors duration-[var(--motion-micro)] ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
                isActive
                  ? "bg-structural-600 text-neutral-0"
                  : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
              )}
            >
              {tab.label}
              <span className={cn("ml-2 tabular-nums", isActive ? "text-structural-100" : "text-neutral-400")}>
                {counts[tab.value]}
              </span>
            </button>
          );
        })}
      </div>
      {value === "loans_cards" && (
        <p className="mt-2 text-caption italic text-neutral-500">{LOANS_TAGLINE}</p>
      )}
    </div>
  );
}
