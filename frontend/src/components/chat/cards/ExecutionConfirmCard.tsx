import { useState } from "react";
import { AlertTriangle, CircleDollarSign, RotateCcw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MoneyText } from "@/components/shared/MoneyText";
import { useExecute } from "@/lib/queries";
import { ExecutionReceiptCard } from "@/components/chat/cards/ExecutionReceiptCard";
import type { Receipt } from "@/lib/types";
import type { ExecutionConfirmCard as ExecutionConfirmCardData } from "./types";

export interface ExecutionConfirmCardProps {
  card: ExecutionConfirmCardData;
  sessionId: string | null;
  onOpenAudit?: () => void;
}

/** An explicit tap-to-confirm gate before anything executes — the customer
 * must act, the backend never auto-executes on the LLM's say-so alone. On
 * success this swaps itself for the receipt in place. */
export function ExecutionConfirmCard({ card, sessionId, onOpenAudit }: ExecutionConfirmCardProps) {
  const execute = useExecute();
  const [receipt, setReceipt] = useState<Receipt | null>(null);

  if (receipt) {
    return <ExecutionReceiptCard receipt={receipt} onOpenAudit={onOpenAudit} />;
  }

  function handleConfirm() {
    if (!sessionId) return;
    execute.mutate(
      { session_id: sessionId, product_id: card.product_id, amount: card.amount, confirm_token: card.confirm_token },
      { onSuccess: (data) => setReceipt(data) }
    );
  }

  return (
    <Card className="border border-brand-200 bg-brand-50">
      <CardHeader>
        <div className="flex items-center gap-2 text-brand-700">
          <CircleDollarSign size={20} strokeWidth={1.75} />
          <CardTitle>
            <span className="font-display text-h4 text-neutral-900">Confirm: {card.product_name}</span>
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <MoneyText value={card.amount} size="lg" />
        <p className="text-body-sm text-neutral-600">
          Expected return {card.expected_return} · {card.note}
        </p>

        {execute.isError && (
          <div className="flex items-center gap-2 rounded-sm border border-danger-200 bg-danger-50 px-3 py-2 text-body-sm text-danger-700">
            <AlertTriangle size={16} strokeWidth={1.75} className="shrink-0" />
            Couldn't complete this — nothing was charged.
          </div>
        )}

        <div className="flex gap-2">
          <Button size="touch" className="flex-1" onClick={handleConfirm} disabled={execute.isPending || !sessionId}>
            {execute.isPending ? "Confirming…" : "Confirm"}
          </Button>
          {execute.isError && (
            <Button size="icon-touch" variant="outline" aria-label="Retry" onClick={handleConfirm}>
              <RotateCcw size={16} strokeWidth={1.75} />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
