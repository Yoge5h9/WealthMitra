import { CircleAlert } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { CreditEligibilityResultCard as CreditEligibilityResultCardData } from "./types";

export function CreditEligibilityResultCard({ card }: { card: CreditEligibilityResultCardData }) {
  return <Card className="border border-warning-300 bg-warning-50"><CardContent className="flex gap-2 py-3"><CircleAlert size={18} strokeWidth={1.75} className="mt-0.5 shrink-0 text-warning-700" aria-hidden="true" /><p className="text-body-sm text-neutral-800">{card.message}</p></CardContent></Card>;
}
