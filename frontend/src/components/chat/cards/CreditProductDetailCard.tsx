import { BadgeCheck, CreditCard, ExternalLink, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CreditProductDetailCard as CreditProductDetailCardData } from "./types";

const STATUS_COPY = {
  eligible: "Ready for RM review",
  ineligible: "Not eligible from known profile",
  needs_more_data: "More information needed",
} as const;

export function CreditProductDetailCard({ card, onApply, disabled }: { card: CreditProductDetailCardData; onApply: (name: string) => void; disabled?: boolean }) {
  const { product } = card;
  const isEligible = product.eligibility.status === "eligible";
  return (
    <Card className="border border-structural-200 bg-structural-50">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 text-structural-700"><CreditCard size={20} strokeWidth={1.75} aria-hidden="true" /><CardTitle><span className="font-display text-h4 text-neutral-900">{product.name}</span></CardTitle></div>
          <span className="rounded-full bg-neutral-100 px-2 py-1 text-caption font-medium text-neutral-600">{product.source === "idbi" ? "IDBI" : "Partner"}</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="rounded-sm border border-neutral-200 bg-neutral-0 px-3 py-2">
          <div className="flex items-center gap-2"><BadgeCheck size={16} strokeWidth={1.75} className="text-structural-600" aria-hidden="true" /><p className="text-body-sm font-medium text-neutral-900">{STATUS_COPY[product.eligibility.status]}</p></div>
          <p className="mt-1 text-caption text-neutral-600">{product.eligibility.reasons[0]}</p>
        </div>
        <div><p className="text-caption font-medium text-neutral-600">Key features</p><ul className="mt-1 space-y-1 text-body-sm text-neutral-700">{product.features.map((feature) => <li key={feature}>• {feature}</li>)}</ul></div>
        {product.fees.length > 0 && <div><p className="text-caption font-medium text-neutral-600">Fees and charges</p><ul className="mt-1 space-y-1 text-body-sm text-neutral-700">{product.fees.map((fee) => <li key={fee}>• {fee}</li>)}</ul></div>}
        <div className="flex items-start gap-2 text-caption text-neutral-600"><ShieldCheck size={15} strokeWidth={1.75} className="mt-0.5 shrink-0 text-structural-600" aria-hidden="true" />{product.display_disclaimer}</div>
        <a href={product.source_url} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center gap-2 text-body-sm font-medium text-structural-700 underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"><ExternalLink size={16} strokeWidth={1.75} aria-hidden="true" />Official IDBI product page</a>
        {isEligible && <Button size="touch" className="w-full" disabled={disabled} onClick={() => onApply(product.name)}>Ask an RM to review this card</Button>}
      </CardContent>
    </Card>
  );
}
