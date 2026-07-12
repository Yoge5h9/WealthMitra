import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Compass, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const TOUR_SEEN_KEY = "wm_tour_seen_v1";

const STEPS = [
  {
    title: "1. Pick a person",
    body: "Choose one of the seven personas below — each carries its own real bank and Account Aggregator data.",
  },
  {
    title: "2. Chat with their companion",
    body: "Ask anything, in their language. Replies are live LLM calls grounded in real tool calls, not a script.",
  },
  {
    title: "3. Watch the RM desk light up",
    body: "Ask about a complex, regulated product — a Lead Packet lands on the RM dashboard in real time.",
  },
  {
    title: "4. See it delivered omni-channel",
    body: "Open the Omni-channel showcase to see the same nudge copy played back as push, SMS, WMessage, and voice.",
  },
];

// Entrance/step timings reference the same token scale as everywhere else
// (motion-screen = 350ms, ease-out) rather than inventing new values.
const SCREEN = 0.35;
const EASE_OUT: [number, number, number, number] = [0.22, 1, 0.36, 1];

export interface GuidedTourProps {
  className?: string;
  /** Bump this (e.g. from a "Replay tour" button) to force the tour open again, ignoring the dismissed flag. */
  reopenSignal?: number;
}

/** Dismissible 4-step walkthrough overlay, remembered per-browser via localStorage. */
export function GuidedTour({ className, reopenSignal }: GuidedTourProps) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const reduceMotion = Boolean(useReducedMotion());
  const isFirstReopen = useRef(true);

  useEffect(() => {
    const seen = window.localStorage.getItem(TOUR_SEEN_KEY);
    if (!seen) {
      const timer = window.setTimeout(() => setOpen(true), 700);
      return () => window.clearTimeout(timer);
    }
  }, []);

  useEffect(() => {
    if (isFirstReopen.current) {
      isFirstReopen.current = false;
      return;
    }
    setStep(0);
    setOpen(true);
  }, [reopenSignal]);

  function dismiss() {
    setOpen(false);
    window.localStorage.setItem(TOUR_SEEN_KEY, "1");
  }

  function next() {
    if (step === STEPS.length - 1) {
      dismiss();
      return;
    }
    setStep((current) => current + 1);
  }

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          role="dialog"
          aria-label="Guided tour"
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 16, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 16, scale: 0.98 }}
          transition={{ duration: SCREEN, ease: EASE_OUT }}
          className={cn(
            "fixed bottom-6 left-1/2 z-40 w-[calc(100%-2rem)] max-w-sm -translate-x-1/2 rounded-xl border border-neutral-200 bg-neutral-0 p-4 shadow-float-xl sm:left-auto sm:right-6 sm:translate-x-0",
            className
          )}
        >
          <div className="flex items-start justify-between gap-3">
            <span className="flex items-center gap-2 text-caption font-semibold uppercase tracking-wide text-structural-600">
              <Compass size={16} strokeWidth={1.75} aria-hidden="true" />
              Guided tour
            </span>
            <button
              type="button"
              onClick={dismiss}
              aria-label="Close guided tour"
              className="-m-2 flex size-8 shrink-0 items-center justify-center rounded-full text-neutral-500 transition-colors duration-[var(--motion-micro)] ease-out hover:text-neutral-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              <X size={16} strokeWidth={1.75} />
            </button>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={reduceMotion ? { opacity: 0 } : { opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={reduceMotion ? { opacity: 0 } : { opacity: 0, x: -12 }}
              transition={{ duration: 0.22, ease: EASE_OUT }}
              className="mt-3"
            >
              <p className="font-display text-h4 font-semibold text-neutral-900">{current.title}</p>
              <p className="mt-1 text-body-sm text-neutral-600">{current.body}</p>
            </motion.div>
          </AnimatePresence>

          <div className="mt-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-1.5" aria-hidden="true">
              {STEPS.map((s, index) => (
                <span
                  key={s.title}
                  className={cn(
                    "h-1.5 rounded-full transition-all duration-[var(--motion-state)] ease-out",
                    index === step ? "w-5 bg-brand-500" : "w-1.5 bg-neutral-200"
                  )}
                />
              ))}
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={dismiss}>
                Skip
              </Button>
              <Button size="sm" className="gap-1.5" onClick={next}>
                {isLast ? "Done" : "Next"}
                {!isLast && <ArrowRight size={14} strokeWidth={2} aria-hidden="true" />}
              </Button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
