import { Target } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MoneyText } from "@/components/shared/MoneyText";
import { formatINR } from "@/lib/format";
import type { GoalCard as GoalCardData } from "./types";

export function GoalCard({ card }: { card: GoalCardData }) {
  const progress = card.target > 0 ? Math.min(100, Math.round((card.saved_so_far / card.target) * 100)) : 0;

  return (
    <Card className="border border-neutral-200">
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-brand-700">
            <Target size={18} strokeWidth={1.75} />
            <CardTitle>
              <span className="font-display text-h4 text-neutral-900">{card.name}</span>
            </CardTitle>
          </div>
          <span className="text-caption text-neutral-500">{card.horizon_years}y horizon</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex items-baseline justify-between">
          <MoneyText value={card.saved_so_far} size="md" compact />
          <span className="text-caption tabular-nums text-neutral-500">of {formatINR(card.target, { compact: true })}</span>
        </div>
        <div
          className="h-2 w-full overflow-hidden rounded-full bg-neutral-100"
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="h-full w-full origin-left rounded-full bg-brand-500 transition-transform duration-[var(--motion-state)] ease-out"
            style={{ transform: `scaleX(${progress / 100})` }}
          />
        </div>
        <p className="text-caption tabular-nums text-neutral-500">{progress}% there</p>
      </CardContent>
    </Card>
  );
}
