import { HelpCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ChatCard } from "@/lib/types";

/** Fallback for any `card_type` the UI doesn't have a dedicated renderer for
 * yet — renders the raw fields plainly instead of crashing the thread. */
export function GenericCard({ card }: { card: ChatCard }) {
  const { card_type, ...rest } = card;
  const entries = Object.entries(rest).filter(([, v]) => v !== undefined);

  return (
    <Card className="border border-neutral-200">
      <CardHeader>
        <div className="flex items-center gap-2 text-neutral-500">
          <HelpCircle size={18} strokeWidth={1.75} />
          <CardTitle>
            <span className="font-display text-h4 capitalize text-neutral-900">
              {card_type.replace(/_/g, " ")}
            </span>
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <dl className="space-y-1">
          {entries.map(([key, value]) => (
            <div key={key} className="flex items-start justify-between gap-3 text-body-sm">
              <dt className="text-neutral-500">{key.replace(/_/g, " ")}</dt>
              <dd className="text-right text-neutral-800">
                {typeof value === "object" ? JSON.stringify(value) : String(value)}
              </dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}
