import { CheckCircle2, Link2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProfileSummaryCard as ProfileSummaryCardData } from "./types";

const LABELS: Record<string, string> = { priority: "Priority", income: "Income", surplus: "Monthly set-aside", preference: "Approach" };

export function ProfileSummaryCard({ card }: { card: ProfileSummaryCardData }) {
  return (
    <Card className="border border-success-200 bg-success-50">
      <CardHeader>
        <div className="flex items-center gap-2 text-success-700">
          <CheckCircle2 size={20} strokeWidth={1.75} aria-hidden="true" />
          <CardTitle><span className="font-display text-h4 text-neutral-900">Your starting profile</span></CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <dl className="space-y-2">
          {Object.entries(card.answers).map(([key, value]) => <div key={key} className="flex items-center justify-between gap-3 text-body-sm"><dt className="text-neutral-600">{LABELS[key] ?? key}</dt><dd className="font-medium text-neutral-900">{value}</dd></div>)}
        </dl>
        <div className="rounded-sm border border-neutral-200 bg-neutral-0 px-3 py-2">
          <p className="text-caption font-medium text-neutral-600">Still needed for personalised insights</p>
          <p className="mt-1 text-body-sm text-neutral-700">{card.missing_data.join(" · ")}</p>
        </div>
        <div className="flex items-start gap-2 text-body-sm text-neutral-700"><Link2 size={16} strokeWidth={1.75} className="mt-0.5 shrink-0 text-structural-600" aria-hidden="true" />{card.next_step}</div>
      </CardContent>
    </Card>
  );
}
