import { AnimatePresence, motion } from "framer-motion";
import { UserRoundPlus, X } from "lucide-react";
import type { LeadToast } from "./useLeadFeed";

export interface LeadToastsProps {
  toasts: LeadToast[];
  onDismiss: (id: string) => void;
}

/** "New lead" toast stack — the entrance affordance for a live `lead.created` WS event. */
export function LeadToasts({ toasts, onDismiss }: LeadToastsProps) {
  return (
    <div className="pointer-events-none fixed bottom-6 right-6 z-50 flex w-80 flex-col gap-2">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            layout
            initial={{ opacity: 0, x: 24, scale: 0.96 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 24, scale: 0.96 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="pointer-events-auto flex items-start gap-3 rounded-lg border border-neutral-200 bg-neutral-0 p-3 shadow-float-lg"
          >
            <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-structural-100 text-structural-700">
              <UserRoundPlus size={16} strokeWidth={1.75} aria-hidden="true" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-body-sm font-semibold text-neutral-900">{toast.title}</p>
              <p className="truncate text-caption text-neutral-600">{toast.description}</p>
            </div>
            <button
              type="button"
              aria-label="Dismiss notification"
              onClick={() => onDismiss(toast.id)}
              className="flex size-6 shrink-0 items-center justify-center rounded-full text-neutral-400 transition-colors duration-[var(--motion-micro)] ease-out hover:bg-neutral-100 hover:text-neutral-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              <X size={14} strokeWidth={1.75} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
