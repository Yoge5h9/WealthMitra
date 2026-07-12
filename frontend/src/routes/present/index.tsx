import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { AlertTriangle, ArrowRight, MessageSquareText, MonitorDot, Radio, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiGet, apiPost, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useSpaceSocket } from "@/hooks/useSpaceSocket";
import { useDemoSpace } from "@/components/showcase/useDemoSpace";

const PRESENTER_PERSONA_ID = "meera";
// How long the LIVE dot stays hot after a WS event before settling back.
const PULSE_HOLD_MS = 2500;

// Must match `SPACE_STORAGE_KEY` in components/showcase/useDemoSpace.ts — a
// stale id here (left over from a previous backend process, e.g. after a
// dev-server restart wiped the in-memory space store) is exactly what makes
// both panes 404 at once. Clearing it forces useDemoSpace to mint a fresh
// one on the next mount instead of re-offering the dead id forever.
const SPACE_STORAGE_KEY = "wm_demo_space_id";

const SCRIPT_STEPS = [
  { label: "Ask Meera's companion about equity funds", icon: MessageSquareText },
  { label: "Watch the Lead Packet land on the RM desk", icon: MonitorDot },
  { label: "Open Omni-channel to see the nudge delivered", icon: Radio },
];

export default function Present() {
  const { spaceId: candidateSpaceId } = useDemoSpace();
  const [searchParams, setSearchParams] = useSearchParams();

  // useDemoSpace() resolves a candidate id from `?space=` or a prior
  // localStorage entry, but never confirms the backend still recognizes it.
  // Both iframed surfaces (`/app` provisioning a session, `/rm` loading its
  // lead queue) 404 identically against a dead space, which is exactly the
  // "both panes broken" failure — so this stage verifies the candidate
  // before ever handing it to an iframe, and self-heals by minting a fresh
  // space rather than surfacing two redundant error panels.
  const [verifiedSpaceId, setVerifiedSpaceId] = useState<string | null>(null);
  const [checkFailed, setCheckFailed] = useState(false);
  const [retryTick, setRetryTick] = useState(0);
  const checkedRef = useRef<string | null>(null);

  useEffect(() => {
    if (!candidateSpaceId) return;
    if (checkedRef.current === candidateSpaceId && !checkFailed) return;
    checkedRef.current = candidateSpaceId;
    let cancelled = false;
    setCheckFailed(false);

    apiGet(`/spaces/${candidateSpaceId}/leads`)
      .then(() => {
        if (!cancelled) setVerifiedSpaceId(candidateSpaceId);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          window.localStorage.removeItem(SPACE_STORAGE_KEY);
          apiPost<{ space_id: string }>("/spaces")
            .then((res) => {
              if (cancelled) return;
              checkedRef.current = res.space_id;
              window.localStorage.setItem(SPACE_STORAGE_KEY, res.space_id);
              const next = new URLSearchParams(searchParams);
              next.set("space", res.space_id);
              setSearchParams(next, { replace: true });
              setVerifiedSpaceId(res.space_id);
            })
            .catch(() => {
              checkedRef.current = null;
              setCheckFailed(true);
            });
        } else {
          checkedRef.current = null;
          setCheckFailed(true);
        }
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateSpaceId, retryTick]);

  const retry = () => {
    checkedRef.current = null;
    setCheckFailed(false);
    setRetryTick((n) => n + 1);
  };

  const spaceId = verifiedSpaceId;
  const { connected, subscribe } = useSpaceSocket(spaceId);
  const [pulsing, setPulsing] = useState(false);
  const pulseTimerRef = useRef<number | null>(null);
  const reduceMotion = Boolean(useReducedMotion());

  useEffect(() => {
    function pulse() {
      setPulsing(true);
      if (pulseTimerRef.current !== null) window.clearTimeout(pulseTimerRef.current);
      pulseTimerRef.current = window.setTimeout(() => setPulsing(false), PULSE_HOLD_MS);
    }
    const unsubChat = subscribe("chat.activity", pulse);
    const unsubLead = subscribe("lead.created", pulse);
    return () => {
      unsubChat();
      unsubLead();
      if (pulseTimerRef.current !== null) window.clearTimeout(pulseTimerRef.current);
    };
  }, [subscribe]);

  const spaceQuery = spaceId ? encodeURIComponent(spaceId) : "";
  const customerSrc = spaceId
    ? `/app?space=${spaceQuery}&persona=${PRESENTER_PERSONA_ID}&embedded=1`
    : null;
  const rmSrc = spaceId ? `/rm?space=${spaceQuery}&embedded=1` : null;

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col bg-neutral-950">
      {/* Stage header */}
      <div className="flex items-center justify-between gap-4 border-b border-neutral-800 px-6 py-3">
        <div>
          <h1 className="font-display text-h4 font-semibold text-neutral-0">Presenter stage</h1>
          <p className="text-caption text-neutral-400">
            Customer phone and RM desk, one shared space — nothing below is stitched together in post.
          </p>
        </div>
        <div
          className={cn(
            "flex items-center gap-2 rounded-full border px-3 py-1.5 text-caption font-semibold uppercase tracking-wide transition-colors duration-[var(--motion-state)] ease-out",
            pulsing
              ? "border-brand-400 bg-brand-500/15 text-brand-300"
              : connected
                ? "border-success-700 bg-success-900/40 text-success-300"
                : "border-neutral-700 bg-neutral-900 text-neutral-500"
          )}
        >
          <motion.span
            className={cn(
              "size-2 rounded-full",
              pulsing ? "bg-brand-400" : connected ? "bg-success-400" : "bg-neutral-600"
            )}
            animate={
              !reduceMotion && (pulsing || connected)
                ? { scale: [1, 1.5, 1], opacity: [1, 0.6, 1] }
                : { scale: 1, opacity: 1 }
            }
            transition={
              !reduceMotion && (pulsing || connected)
                ? { duration: pulsing ? 0.7 : 2.1, repeat: Infinity, ease: "easeInOut" }
                : { duration: 0.15 }
            }
            aria-hidden="true"
          />
          {connected ? "LIVE · one engine, two surfaces" : "Connecting…"}
        </div>
      </div>

      {/* Split stage */}
      {checkFailed ? (
        <div className="flex flex-1 items-center justify-center p-8">
          <div className="flex max-w-sm flex-col items-center gap-3 rounded-xl border border-danger-800 bg-danger-950/30 px-8 py-10 text-center">
            <span className="flex size-11 items-center justify-center rounded-full bg-danger-900/60 text-danger-300">
              <AlertTriangle size={20} strokeWidth={1.75} aria-hidden="true" />
            </span>
            <p className="text-body-sm font-medium text-neutral-100">Couldn't reach the bank</p>
            <p className="max-w-xs text-caption text-neutral-400">
              The demo space couldn't be provisioned. Nothing was changed — try again.
            </p>
            <Button size="touch" variant="outline" className="gap-2" onClick={retry}>
              <RotateCcw size={16} strokeWidth={1.75} aria-hidden="true" />
              Try again
            </Button>
          </div>
        </div>
      ) : (
        <div className="grid flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-[440px_1fr]">
          <section aria-label="Customer phone" className="flex flex-col gap-2">
            <p className="text-caption font-semibold uppercase tracking-wide text-neutral-400">
              Customer · Meera's phone
            </p>
            <div className="min-h-[600px] flex-1 overflow-hidden rounded-xl border border-neutral-800 bg-neutral-900">
              {customerSrc ? (
                <iframe
                  src={customerSrc}
                  title="Customer app — Meera"
                  className="size-full border-0"
                />
              ) : (
                <div className="flex h-full items-center justify-center text-body-sm text-neutral-500">
                  Preparing demo stage…
                </div>
              )}
            </div>
          </section>

          <section aria-label="RM dashboard" className="flex flex-col gap-2">
            <p className="text-caption font-semibold uppercase tracking-wide text-neutral-400">
              Relationship Manager · lead desk
            </p>
            <div className="min-h-[600px] flex-1 overflow-hidden rounded-xl border border-neutral-800 bg-neutral-900">
              {rmSrc ? (
                <iframe src={rmSrc} title="RM dashboard" className="size-full border-0" />
              ) : (
                <div className="flex h-full items-center justify-center text-body-sm text-neutral-500">
                  Preparing demo stage…
                </div>
              )}
            </div>
          </section>
        </div>
      )}

      {/* Judge walkthrough — centered, numbered step strip */}
      <div className="border-t border-neutral-800 px-6 py-5">
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-3 text-center">
          <p className="text-caption font-semibold uppercase tracking-[0.2em] text-brand-400">
            Judge walkthrough
          </p>
          <ol className="flex flex-wrap items-center justify-center gap-x-2 gap-y-3">
            {SCRIPT_STEPS.map((step, index) => (
              <li key={step.label} className="flex items-center gap-2">
                <div className="flex items-center gap-2.5 rounded-full border border-neutral-700 bg-neutral-900 px-4 py-2">
                  <span
                    className="flex size-6 shrink-0 items-center justify-center rounded-full bg-brand-500 text-caption font-bold text-neutral-950"
                    aria-hidden="true"
                  >
                    {index + 1}
                  </span>
                  <step.icon size={15} strokeWidth={1.75} className="text-structural-400" aria-hidden="true" />
                  <span className="text-body-sm font-medium text-neutral-200">{step.label}</span>
                </div>
                {index < SCRIPT_STEPS.length - 1 && (
                  <ArrowRight size={16} strokeWidth={2} className="shrink-0 text-neutral-600" aria-hidden="true" />
                )}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}
