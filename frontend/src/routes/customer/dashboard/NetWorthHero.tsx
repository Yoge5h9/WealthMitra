import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Eye, EyeOff, Landmark, Link2 } from "lucide-react";
import { MoneyText } from "@/components/shared/MoneyText";
import type { NetWorthValue } from "./types";

export interface NetWorthHeroProps {
  value: NetWorthValue;
}

/**
 * The dashboard's dominant element — breaks hero+3-cards
 * symmetry by letting the most important figure visibly dominate. Defaults
 * blurred behind a tap-to-reveal privacy shield, a common banking-app
 * pattern for a figure this sensitive. The internal/external split makes the
 * AA-connected state legible without a second screen.
 */
export function NetWorthHero({ value }: NetWorthHeroProps) {
  const [revealed, setRevealed] = useState(false);
  const reduceMotion = Boolean(useReducedMotion());

  return (
    <div className="rounded-xl border border-neutral-200 bg-gradient-to-br from-structural-700 to-structural-600 p-6 text-neutral-0">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-caption font-semibold uppercase tracking-wide text-structural-100">
            Total net worth
          </p>
        </div>
        <button
          type="button"
          onClick={() => setRevealed((r) => !r)}
          aria-pressed={revealed}
          aria-label={revealed ? "Hide net worth" : "Reveal net worth"}
          className="flex size-11 shrink-0 items-center justify-center rounded-full bg-neutral-0/10 text-neutral-0 transition-colors duration-[var(--motion-micro)] ease-out hover:bg-neutral-0/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
        >
          {revealed ? <EyeOff size={20} strokeWidth={1.75} /> : <Eye size={20} strokeWidth={1.75} />}
        </button>
      </div>

      <div className="relative mt-3 inline-block">
        <MoneyText
          value={value.total}
          size="hero"
          compact
          whyThisNumber={`net_worth_v1 · internal ledger position${
            value.external_connected ? " + connected external holdings/liabilities" : " (connect external accounts to include them)"
          }`}
        />
        <AnimatePresence>
          {!revealed && (
            <motion.div
              initial={reduceMotion ? { opacity: 1 } : { opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: reduceMotion ? 0.01 : 0.22, ease: [0.22, 1, 0.36, 1] }}
              className="absolute inset-0 flex items-center rounded-sm bg-structural-600/70 backdrop-blur-md"
              aria-hidden="true"
            >
              <span className="px-1 text-body-sm font-medium text-neutral-0/80">Tap the eye to reveal</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-neutral-0/15 bg-neutral-0/10 p-3">
          <div className="flex items-center gap-1.5 text-structural-100">
            <Landmark size={14} strokeWidth={1.75} aria-hidden="true" />
            <span className="text-caption font-medium">In the bank</span>
          </div>
          <MoneyText value={value.internal} size="lg" compact className="mt-1" />
        </div>
        <div className="rounded-lg border border-neutral-0/15 bg-neutral-0/10 p-3">
          <div className="flex items-center gap-1.5 text-structural-100">
            <Link2 size={14} strokeWidth={1.75} aria-hidden="true" />
            <span className="text-caption font-medium">Outside accounts</span>
          </div>
          {value.external_connected ? (
            <MoneyText value={value.external} size="lg" compact className="mt-1" />
          ) : (
            <p className="mt-1 text-body-sm text-structural-100">Not linked</p>
          )}
        </div>
      </div>
    </div>
  );
}
