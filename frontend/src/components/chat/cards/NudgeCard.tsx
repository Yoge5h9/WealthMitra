import { Bell, Heart } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { NudgeCard as NudgeCardData } from "./types";

/** Functional (actionable) vs relational (rapport) nudges must read as
 * visually distinct (Task 13/16 requirement) — functional gets the brand
 * accent bar (it wants a response), relational stays structural/neutral
 * (it's a check-in, not a nudge to act). */
export function NudgeCard({ card }: { card: NudgeCardData }) {
  const isFunctional = card.kind === "functional";
  return (
    <Card
      className={cn(
        "border-l-4 border-y border-r border-neutral-200",
        isFunctional ? "border-l-brand-500" : "border-l-structural-400"
      )}
    >
      <CardContent className="flex items-start gap-3 pt-4">
        <span
          className={cn(
            "flex size-9 shrink-0 items-center justify-center rounded-full",
            isFunctional ? "bg-brand-50 text-brand-700" : "bg-structural-50 text-structural-600"
          )}
        >
          {isFunctional ? <Bell size={16} strokeWidth={1.75} /> : <Heart size={16} strokeWidth={1.75} />}
        </span>
        <div className="min-w-0">
          <p className="text-body-sm font-semibold text-neutral-900">{card.title}</p>
          <p className="mt-1 text-body-sm text-neutral-600">{card.body}</p>
        </div>
      </CardContent>
    </Card>
  );
}
