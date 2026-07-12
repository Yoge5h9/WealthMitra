import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { DataState } from "@/components/shared/DataState";
import { MoneyText } from "@/components/shared/MoneyText";
import { useRmCustomerSummary } from "@/lib/queries";
import { humanize } from "./text";

export interface CustomerDrawerProps {
  open: boolean;
  onClose: () => void;
  spaceId: string;
  personaId: string;
  customerName: string;
}

function SummaryRow({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-neutral-100 py-3 last:border-0">
      <p className="text-body-sm text-neutral-600">{label}</p>
      {typeof value === "number" ? (
        <MoneyText value={value} size="md" />
      ) : (
        <span className="text-body-sm font-semibold capitalize text-neutral-900">{humanize(value)}</span>
      )}
    </div>
  );
}

/**
 * "View full customer analysis" — the same deterministic summary the avatar
 * sees mid-chat, keyed by persona for the RM (GET /api/spaces/{space_id}/
 * customers/{persona_id}/summary) since a LeadPacket carries no session id.
 */
export function CustomerDrawer({ open, onClose, spaceId, personaId, customerName }: CustomerDrawerProps) {
  const summary = useRmCustomerSummary(open ? spaceId : null, open ? personaId : null);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="fixed inset-0 z-40 bg-neutral-950/40"
            onClick={onClose}
            aria-hidden="true"
          />
          <motion.aside
            key="panel"
            role="dialog"
            aria-modal="true"
            aria-label={`${customerName} — full customer analysis`}
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 24 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col overflow-hidden border-l border-neutral-200 bg-neutral-0 shadow-float-xl"
          >
            <div className="flex shrink-0 items-center justify-between border-b border-neutral-200 px-6 py-4">
              <div>
                <p className="text-caption font-semibold uppercase tracking-wide text-structural-600">
                  Customer-360
                </p>
                <h3 className="font-display text-h4 font-semibold text-neutral-900">{customerName}</h3>
              </div>
              <button
                type="button"
                aria-label="Close"
                onClick={onClose}
                className="flex size-9 items-center justify-center rounded-full text-neutral-500 transition-colors duration-[var(--motion-micro)] ease-out hover:bg-neutral-100 hover:text-neutral-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
              >
                <X size={18} strokeWidth={1.75} />
              </button>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
              <DataState
                status={summary.isLoading ? "loading" : summary.isError ? "error" : summary.data ? "success" : "empty"}
                onRetry={() => summary.refetch()}
                emptyTitle="No customer data"
                emptyDescription="The summary for this customer could not be loaded."
              >
                {summary.data && (
                  <div className="space-y-0">
                    <SummaryRow label="Net worth" value={summary.data.metrics.net_worth.total} />
                    <SummaryRow label="Monthly income" value={summary.data.metrics.monthly_income} />
                    <SummaryRow label="Monthly surplus" value={summary.data.metrics.monthly_surplus} />
                    <SummaryRow label="Idle balance" value={summary.data.metrics.idle_balance} />
                    <SummaryRow label="Risk band" value={summary.data.metrics.risk_band} />
                    <SummaryRow label="Suitability segment" value={summary.data.metrics.segment} />
                    <SummaryRow
                      label="Out-of-bank holdings"
                      value={
                        summary.data.holdings.aa_connected
                          ? summary.data.holdings.external.reduce((sum, h) => sum + h.amount, 0)
                          : "not connected"
                      }
                    />
                  </div>
                )}
              </DataState>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
