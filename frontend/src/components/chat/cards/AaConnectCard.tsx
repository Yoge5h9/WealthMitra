import { useState } from "react";
import { Link2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { AaConnectCard as AaConnectCardData } from "./types";

/** Teaser only — the real consent-first Account Aggregator flow (transfer +
 * processing consent, discovery animation) is owned by the Dashboard
 * surface. This card never collects consent itself; it only points there. */
export function AaConnectCard({ card }: { card: AaConnectCardData }) {
  const [acknowledged, setAcknowledged] = useState(false);

  return (
    <Card className="border border-neutral-200">
      <CardHeader>
        <div className="flex items-center gap-2 text-structural-600">
          <Link2 size={18} strokeWidth={1.75} />
          <CardTitle>
            <span className="font-display text-h4 text-neutral-900">{card.headline}</span>
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-body-sm text-neutral-700">{card.body}</p>
        {acknowledged ? (
          <p className="text-caption text-structural-700">
            Head to your Dashboard tab any time — nothing is linked without your explicit consent, twice: once to
            share the data, once to let WealthMitra use it.
          </p>
        ) : (
          <Button size="touch" variant="outline" onClick={() => setAcknowledged(true)}>
            How does linking work?
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
