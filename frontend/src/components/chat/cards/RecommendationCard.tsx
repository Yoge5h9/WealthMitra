import { ShieldCheck, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MoneyText } from "@/components/shared/MoneyText";
import type { RecommendationCard as RecommendationCardData } from "./types";

export interface RecommendationCardProps {
  card: RecommendationCardData;
  onRequestProduct: (productName: string) => void;
  disabled?: boolean;
}

const CATEGORY_LABEL: Record<string, string> = {
  deposit: "Fixed deposit",
  mutual_fund: "Mutual fund",
  bond: "Bond",
  govt_scheme: "Government scheme",
  pms: "Portfolio management",
  aif: "Alternative investment fund",
  structured: "Structured product",
  insurance: "Insurance",
  portfolio: "Portfolio",
};

export function RecommendationCard({ card, onRequestProduct, disabled }: RecommendationCardProps) {
  const { product } = card;
  return (
    <Card className="border border-neutral-200">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 text-brand-700">
            <Sparkles size={18} strokeWidth={1.75} />
            <CardTitle>
              <span className="font-display text-h4 text-neutral-900">{product.name}</span>
            </CardTitle>
          </div>
          <span className="rounded-full bg-neutral-100 px-2 py-1 text-caption font-medium text-neutral-600">
            {CATEGORY_LABEL[product.category] ?? product.category}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-6">
          <div>
            <p className="text-caption text-neutral-500">Expected return</p>
            <p className="text-h4 font-semibold tabular-nums text-neutral-900">{product.expected_return}</p>
          </div>
          <div>
            <p className="text-caption text-neutral-500">Minimum</p>
            <MoneyText value={product.min_amount} size="md" compact />
          </div>
        </div>

        <ul className="space-y-1">
          {card.why.map((reason) => (
            <li key={reason} className="flex items-start gap-2 text-body-sm text-neutral-600">
              {/* 2px optical nudge: centers the 14px icon on the 20px body-sm line box */}
              <ShieldCheck size={14} strokeWidth={1.75} className="mt-0.5 shrink-0 text-structural-600" aria-hidden="true" />
              {reason}
            </li>
          ))}
        </ul>

        <Button
          size="touch"
          className="w-full"
          disabled={disabled}
          onClick={() => onRequestProduct(product.name)}
        >
          I'd like to proceed with this
        </Button>
      </CardContent>
    </Card>
  );
}
