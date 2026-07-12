import { BookOpen } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { LiteracyCard as LiteracyCardData } from "./types";

export function LiteracyCard({ card }: { card: LiteracyCardData }) {
  return (
    <Card className="border border-structural-200 bg-structural-50">
      <CardHeader>
        <div className="flex items-center gap-2 text-structural-700">
          <BookOpen size={18} strokeWidth={1.75} />
          <CardTitle>
            <span className="font-display text-h4 capitalize text-neutral-900">{card.term}</span>
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-body-sm text-neutral-700">{card.definition}</p>
      </CardContent>
    </Card>
  );
}
