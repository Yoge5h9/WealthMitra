import { motion } from "framer-motion";
import { AlertTriangle, PiggyBank } from "lucide-react";
import { MoneyText } from "@/components/shared/MoneyText";
import { humanize } from "./format";
import type { DashboardHolding, DashboardLiability } from "./types";

export interface HoldingsListProps {
  holdings: DashboardHolding[];
  liabilities: DashboardLiability[];
  /** Staggers each row in on first reveal (the AA "discovery" moment). Off for a plain re-render. */
  animateIn?: boolean;
}

/**
 * Renders real per-holding fields only (`type`, `institution`, `amount`,
 * `rate`) — no per-holding history exists anywhere in the backend (see
 * `app/domain/models.py::ExternalHolding`), so rather than fabricate a time
 * series for a "trend sparkline" (a hard compliance invariant: never invent
 * a figure client-side), each row instead gets a real, derived-not-invented
 * allocation bar: this holding's share of the total connected external
 * value. That's the honest substitute for a sparkline here.
 */
export function HoldingsList({ holdings, liabilities, animateIn = false }: HoldingsListProps) {
  const totalHoldings = holdings.reduce((sum, h) => sum + h.amount, 0);

  if (holdings.length === 0 && liabilities.length === 0) {
    return <p className="text-body-sm text-neutral-600">No external holdings or liabilities on record.</p>;
  }

  return (
    <ul className="space-y-2">
      {holdings.map((holding, index) => {
        const share = totalHoldings > 0 ? holding.amount / totalHoldings : 0;
        return (
          <motion.li
            key={holding.id}
            initial={animateIn ? { opacity: 0, y: 8 } : false}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22, delay: animateIn ? index * 0.08 : 0, ease: [0.22, 1, 0.36, 1] }}
            className="rounded-lg border border-neutral-200 p-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-structural-50 text-structural-600">
                  <PiggyBank size={16} strokeWidth={1.75} aria-hidden="true" />
                </span>
                <div>
                  <p className="text-body-sm font-medium text-neutral-900">{humanize(holding.type)}</p>
                  <p className="text-caption text-neutral-500">{holding.institution}</p>
                </div>
              </div>
              <div className="text-right">
                <MoneyText
                  value={holding.amount}
                  size="sm"
                  whyThisNumber={`From ${holding.institution} via Account Aggregator, only visible while linked`}
                />
                {holding.rate !== null && (
                  <p className="mt-0.5 text-caption tabular-nums text-neutral-500">{holding.rate}% p.a.</p>
                )}
              </div>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-neutral-100" aria-hidden="true">
              <div
                className="h-full rounded-full bg-structural-400"
                style={{ width: `${Math.round(share * 100)}%` }}
              />
            </div>
            <p className="mt-1 text-caption tabular-nums text-neutral-500">{Math.round(share * 100)}% of connected holdings</p>
          </motion.li>
        );
      })}

      {liabilities.map((liability, index) => (
        <motion.li
          key={liability.id}
          initial={animateIn ? { opacity: 0, y: 8 } : false}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 0.22,
            delay: animateIn ? (holdings.length + index) * 0.08 : 0,
            ease: [0.22, 1, 0.36, 1],
          }}
          className="rounded-lg border border-danger-200 bg-danger-50/40 p-3"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-danger-50 text-danger-600">
                <AlertTriangle size={16} strokeWidth={1.75} aria-hidden="true" />
              </span>
              <div>
                <p className="text-body-sm font-medium text-neutral-900">{humanize(liability.type)}</p>
                <p className="text-caption text-neutral-500">{liability.lender}</p>
              </div>
            </div>
            <div className="text-right">
              <MoneyText
                value={liability.principal}
                size="sm"
                whyThisNumber={`From ${liability.lender} via Account Aggregator, only visible while linked`}
              />
              <p className="mt-0.5 text-caption tabular-nums text-danger-600">{liability.rate}% p.a.</p>
            </div>
          </div>
        </motion.li>
      ))}
    </ul>
  );
}
