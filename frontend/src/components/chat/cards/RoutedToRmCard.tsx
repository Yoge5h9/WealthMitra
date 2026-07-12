import { Landmark, UserRound } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RoutedToRmCard as RoutedToRmCardData } from "./types";

const FAMILY_LABEL: Record<RoutedToRmCardData["family"], string> = {
  investment_insurance: "Investments & Insurance",
  loans_cards: "Loans & Cards",
};

/** Never a black-box "contact your RM" — always names what triggered the
 * hand-off and what happens next. */
export function RoutedToRmCard({ card }: { card: RoutedToRmCardData }) {
  return (
    <Card className="border border-structural-200 bg-structural-50">
      <CardHeader>
        <div className="flex items-center gap-2 text-structural-700">
          <UserRound size={20} strokeWidth={1.75} />
          <CardTitle>
            <span className="font-display text-h4 text-neutral-900">Routed to your Relationship Manager</span>
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-structural-100 px-2 py-1 text-caption font-semibold text-structural-700">
            <Landmark size={12} strokeWidth={2} aria-hidden="true" />
            {FAMILY_LABEL[card.family]}
          </span>
          <span className="rounded-full bg-neutral-100 px-2 py-1 text-caption font-medium text-neutral-600">
            Lead {card.lead_id}
          </span>
        </div>

        <p className="text-body-sm text-neutral-700">{card.what_happens_next}</p>

        {card.recommendations && card.recommendations.length > 0 && (
          <div className="space-y-2">
            <p className="text-caption font-medium text-neutral-600">Options for your RM to review</p>
            {card.recommendations.map((offer) => (
              <div key={offer.id} className="rounded-sm border border-neutral-200 bg-neutral-0 px-3 py-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-body-sm font-medium text-neutral-900">{offer.name}</p>
                  <span className="shrink-0 rounded-full bg-neutral-100 px-2 py-1 text-caption font-medium text-neutral-600">{offer.source === "idbi" ? "IDBI" : "Partner"}</span>
                </div>
                <p className="mt-1 text-caption text-neutral-600">{offer.reasons[0]}</p>
              </div>
            ))}
          </div>
        )}

        <div className="rounded-sm border border-neutral-200 bg-neutral-0 px-3 py-2">
          <p className="text-caption text-neutral-500">Next best action</p>
          <p className="text-body-sm font-medium text-neutral-800">{card.next_best_action}</p>
        </div>

        <p className="text-caption text-neutral-500">
          This needs a licensed human — regulated products are never auto-executed by WealthMitra.
        </p>
      </CardContent>
    </Card>
  );
}
