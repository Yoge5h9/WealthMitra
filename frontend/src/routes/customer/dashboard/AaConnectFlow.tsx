import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Switch } from "radix-ui";
import { Fingerprint, Inbox, Link2, Loader2, ScanSearch, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { t, type LanguageCode } from "@/lib/i18n";
import { HoldingsList } from "./HoldingsList";
import { useAaConsentAction } from "./useDashboardData";
import type { DashboardHolding, DashboardLiability } from "./types";

export interface AaConnectFlowProps {
  sessionId: string;
  /** Best-effort hint (see `./personaAaAvailability.ts`) — the first real
   * `POST /aa/consent` response always overrides this if they disagree. */
  aaAvailableHint: boolean;
  connected: boolean;
  holdings: DashboardHolding[];
  liabilities: DashboardLiability[];
  language: LanguageCode;
}

type Phase = "idle" | "requesting_transfer" | "requesting_processing" | "discovering" | "done";

function ConsentSwitch({
  id,
  label,
  description,
  checked,
  disabled,
  onChange,
}: {
  id: string;
  label: string;
  description: string;
  checked: boolean;
  disabled: boolean;
  onChange: (granted: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-lg border border-neutral-200 p-3">
      <div className="min-w-0">
        <label htmlFor={id} className="text-body-sm font-medium text-neutral-900">
          {label}
        </label>
        <p className="mt-0.5 text-caption text-neutral-600">{description}</p>
      </div>
      {/* Root is the full 44x44 hit area; the visible track is
          a smaller inner span so the switch doesn't look oversized. */}
      <Switch.Root
        id={id}
        checked={checked}
        disabled={disabled}
        onCheckedChange={onChange}
        className="flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-full outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] disabled:cursor-not-allowed disabled:opacity-50"
      >
        <span
          aria-hidden="true"
          data-state={checked ? "checked" : "unchecked"}
          className="relative inline-flex h-6 w-11 items-center rounded-full bg-neutral-300 transition-colors duration-[var(--motion-micro)] ease-out data-[state=checked]:bg-structural-600"
        >
          <Switch.Thumb className="block size-5 translate-x-0.5 rounded-full bg-neutral-0 shadow-float-sm transition-transform duration-[var(--motion-micro)] ease-out data-[state=checked]:translate-x-[22px]" />
        </span>
      </Switch.Root>
    </div>
  );
}

/**
 * Consent-first AA connect flow: two independent, explicitly labeled
 * consents (never one combined "connect" toggle) — granting both flips
 * `persona.external.connected` server-side, which is what unlocks external
 * holdings/liabilities in net worth everywhere else in the app. Each grant
 * is individually revocable at any time; revoking either one immediately
 * re-hides external data (the summary refetch this triggers is what makes
 * net worth visibly recompute).
 */
export function AaConnectFlow({ sessionId, aaAvailableHint, connected, holdings, liabilities, language }: AaConnectFlowProps) {
  const { setConsent, pendingStep } = useAaConsentAction(sessionId);

  const [aaAvailable, setAaAvailable] = useState(aaAvailableHint);

  // The backend has no GET for partial consent state, so on mount we can
  // only infer both grants from `connected` (which requires both to be
  // true) — a real limitation, not a UI guess dressed up as data.
  const [transferGranted, setTransferGranted] = useState(connected);
  const [processingGranted, setProcessingGranted] = useState(connected);
  const [phase, setPhase] = useState<Phase>(connected ? "done" : "idle");
  const wasConnected = useRef(connected);

  useEffect(() => {
    if (connected && !wasConnected.current) {
      setPhase("discovering");
      const timer = window.setTimeout(() => setPhase("done"), 900);
      wasConnected.current = true;
      return () => window.clearTimeout(timer);
    }
    if (!connected && wasConnected.current) {
      wasConnected.current = false;
      setPhase("idle");
    }
    return undefined;
  }, [connected]);

  async function handleLinkAccounts() {
    setPhase("requesting_transfer");
    const transferResult = await setConsent("transfer", true);
    if (!transferResult.aa_available) {
      // Nothing was actually granted server-side for an aa_available=false
      // persona (`app/api/aa.py` returns before any state/audit write in
      // that case) — just correct the UI to the real empty state.
      setAaAvailable(false);
      setPhase("idle");
      return;
    }
    setTransferGranted(true);
    setPhase("requesting_processing");
    await setConsent("processing", true);
    setProcessingGranted(true);
    // `connected` flips true once the summary refetches; the effect above
    // picks up the discovering/done transition from there.
  }

  if (!aaAvailable) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-neutral-200 px-6 py-8 text-center">
        <span className="flex size-11 items-center justify-center rounded-full bg-neutral-100 text-neutral-500">
          <Inbox size={20} strokeWidth={1.75} />
        </span>
        <div className="space-y-1">
          <p className="text-body-sm font-medium text-neutral-700">{t(language, "dashboard.aa.noneTitle")}</p>
          <p className="max-w-xs text-caption text-neutral-600">{t(language, "dashboard.aa.noneDescription")}</p>
        </div>
      </div>
    );
  }

  const linking = phase === "requesting_transfer" || phase === "requesting_processing";

  return (
    <div className="space-y-3">
      {!connected && (
        <div className="rounded-lg border border-structural-200 bg-structural-50 p-4">
          <div className="flex items-center gap-2 text-structural-700">
            <Link2 size={18} strokeWidth={1.75} aria-hidden="true" />
            <p className="font-display text-h4 font-semibold">{t(language, "dashboard.aa.linkTitle")}</p>
          </div>
          <p className="mt-2 text-body-sm text-neutral-700">{t(language, "dashboard.aa.linkDescription")}</p>
          <Button size="touch" className="mt-3 gap-2" onClick={() => void handleLinkAccounts()} disabled={linking}>
            {linking ? (
              <>
                <Loader2 size={18} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />
                {t(language, phase === "requesting_transfer" ? "dashboard.aa.requestingTransfer" : "dashboard.aa.requestingProcessing")}
              </>
            ) : (
              <>
                <ShieldCheck size={18} strokeWidth={1.75} aria-hidden="true" />
                {t(language, "dashboard.aa.linkButton")}
              </>
            )}
          </Button>
        </div>
      )}

      <ConsentSwitch
        id={`aa-transfer-${sessionId}`}
        label={t(language, "dashboard.aa.transferLabel")}
        description={t(language, "dashboard.aa.transferDescription")}
        checked={transferGranted}
        disabled={pendingStep !== null}
        onChange={(granted) => {
          setTransferGranted(granted);
          void setConsent("transfer", granted);
        }}
      />
      <ConsentSwitch
        id={`aa-processing-${sessionId}`}
        label={t(language, "dashboard.aa.processingLabel")}
        description={t(language, "dashboard.aa.processingDescription")}
        checked={processingGranted}
        disabled={pendingStep !== null}
        onChange={(granted) => {
          setProcessingGranted(granted);
          void setConsent("processing", granted);
        }}
      />

      <AnimatePresence mode="wait">
        {phase === "discovering" && (
          <motion.div
            key="discovering"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="flex items-center gap-2 rounded-lg border border-structural-200 bg-structural-50 p-3 text-structural-700"
          >
            <ScanSearch size={18} strokeWidth={1.75} className="animate-pulse" aria-hidden="true" />
            <p className="text-body-sm font-medium">{t(language, "dashboard.aa.discovering")}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {connected && phase === "done" && (
        <div className="pt-1">
          <p className="mb-2 flex items-center gap-1.5 text-caption font-medium text-neutral-600">
            <Fingerprint size={14} strokeWidth={1.75} aria-hidden="true" />
            {t(language, "dashboard.aa.linkedVia")}
          </p>
          <HoldingsList holdings={holdings} liabilities={liabilities} animateIn language={language} />
        </div>
      )}
    </div>
  );
}
