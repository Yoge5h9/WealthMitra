import { CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MoneyText } from "@/components/shared/MoneyText";
import { formatDate } from "@/lib/format";
import type { Receipt } from "@/lib/types";

export interface ExecutionReceiptCardProps {
  receipt: Receipt;
  onOpenAudit?: () => void;
}

export function ExecutionReceiptCard({ receipt, onOpenAudit }: ExecutionReceiptCardProps) {
  return (
    <Card className="border border-success-200 bg-success-50">
      <CardHeader>
        <div className="flex items-center gap-2 text-success-700">
          <CheckCircle2 size={20} strokeWidth={1.75} />
          <CardTitle>
            <span className="font-display text-h4 text-neutral-900">Done — {receipt.product_name}</span>
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <MoneyText value={receipt.amount} size="lg" />
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-body-sm">
          <dt className="text-neutral-500">Receipt</dt>
          <dd className="text-right text-neutral-800 tabular-nums">{receipt.receipt_id}</dd>
          <dt className="text-neutral-500">When</dt>
          <dd className="text-right text-neutral-800 tabular-nums">{formatDate(receipt.executed_at, { withTime: true })}</dd>
        </dl>
        {onOpenAudit && (
          <button
            type="button"
            onClick={onOpenAudit}
            className="min-h-11 rounded-sm text-body-sm font-medium text-structural-700 underline underline-offset-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
          >
            View in audit trail
          </button>
        )}
      </CardContent>
    </Card>
  );
}
