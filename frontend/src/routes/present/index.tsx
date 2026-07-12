import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, MessageSquareText, MonitorDot, Radio } from "lucide-react";
import { cn } from "@/lib/utils";
import { useSpaceSocket } from "@/hooks/useSpaceSocket";
import { useDemoSpace } from "@/components/showcase/useDemoSpace";

const PRESENTER_PERSONA_ID = "meera";
// How long the LIVE dot stays hot after a WS event before settling back.
const PULSE_HOLD_MS = 2500;

const SCRIPT_STEPS = [
  { label: "Ask Meera's companion about equity funds", icon: MessageSquareText },
  { label: "Watch the Lead Packet land on the RM desk", icon: MonitorDot },
  { label: "Open Omni-channel to see the nudge delivered", icon: Radio },
];

export default function Present() {
  const { spaceId } = useDemoSpace();
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
                Provisioning demo space…
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
                Provisioning demo space…
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Script strip */}
      <div className="flex flex-wrap items-center gap-2 border-t border-neutral-800 px-6 py-3">
        <span className="text-caption font-semibold uppercase tracking-wide text-brand-400">Try:</span>
        {SCRIPT_STEPS.map((step, index) => (
          <span key={step.label} className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 rounded-full border border-neutral-800 bg-neutral-900 px-3 py-1.5 text-caption text-neutral-300">
              <step.icon size={13} strokeWidth={1.75} className="text-structural-400" aria-hidden="true" />
              {step.label}
            </span>
            {index < SCRIPT_STEPS.length - 1 && (
              <ArrowRight size={14} strokeWidth={1.75} className="text-neutral-600" aria-hidden="true" />
            )}
          </span>
        ))}
      </div>
    </div>
  );
}
