import { HeartHandshake } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DistressSupportCard as DistressSupportCardData } from "./types";

export interface DistressSupportCardProps {
  card: DistressSupportCardData;
  onPickOption: (option: string) => void;
}

/** Calm, supportive, and deliberately product-free — distress suppresses
 * all selling (CLAUDE.md §7 hard invariant), so this card carries neutral
 * structural styling only, never the brand-orange CTA treatment. */
export function DistressSupportCard({ card, onPickOption }: DistressSupportCardProps) {
  return (
    <Card className="border border-neutral-200 bg-neutral-0">
      <CardHeader>
        <div className="flex items-center gap-2 text-structural-600">
          <HeartHandshake size={20} strokeWidth={1.75} />
          <CardTitle>
            <span className="font-display text-h4 text-neutral-900">Let's take this one step at a time</span>
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-body-sm text-neutral-700">{card.message}</p>
        <div className="flex flex-col gap-2">
          {card.options.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => onPickOption(option)}
              className="min-h-11 rounded-sm border border-neutral-200 bg-neutral-0 px-4 text-left text-body-sm font-medium text-neutral-700 transition-colors duration-[var(--motion-micro)] ease-out hover:border-structural-300 hover:text-structural-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              {option}
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
