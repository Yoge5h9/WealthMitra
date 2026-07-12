import { motion } from "framer-motion";
import { CheckCheck, MessageCircle } from "lucide-react";
import { PhoneFrame } from "@/components/shared/PhoneFrame";
import { SampleTag } from "@/components/showcase/channels/SampleTag";
import type { ChannelDelivery } from "@/components/showcase/channels/types";

const EASE_OUT: [number, number, number, number] = [0.22, 1, 0.36, 1];

/**
 * A generic messaging-app chat mock — green header and bubble styling read
 * as "WhatsApp-like" without using the WhatsApp name, logo, or exact bubble
 * shade, per the brand-imitation guardrail (CLAUDE.md §7 IP).
 */
export function WMessageChatCard({ delivery }: { delivery: ChannelDelivery }) {
  return (
    <PhoneFrame headerTitle="WMessage">
      <div className="flex h-full flex-col">
        <div className="flex items-center gap-2 bg-success-600 px-3 py-2.5 text-neutral-0">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-success-700">
            <MessageCircle size={16} strokeWidth={1.75} aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-body-sm font-semibold">WealthMitra</p>
            <p className="text-caption text-success-100">online</p>
          </div>
          {delivery.sample && <SampleTag />}
        </div>

        <div
          className="flex-1 space-y-3 p-3"
          style={{ backgroundColor: "color-mix(in oklab, var(--color-success-50) 55%, var(--color-neutral-50))" }}
        >
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.35, ease: EASE_OUT }}
            className="max-w-[85%] rounded-lg rounded-tl-xs bg-neutral-0 px-3 py-2 shadow-float-sm"
          >
            <p className="text-body-sm font-semibold text-neutral-900">{delivery.title}</p>
            <p className="mt-0.5 text-body-sm text-neutral-700">{delivery.body}</p>
            <p className="mt-1 flex items-center justify-end gap-1 text-caption text-neutral-400">
              now
              <CheckCheck size={13} strokeWidth={2} aria-hidden="true" />
            </p>
          </motion.div>
        </div>

        <p className="border-t border-neutral-200 bg-neutral-0 px-3 py-2 text-caption text-neutral-500">
          Simulated delivery · real AI-generated copy
        </p>
      </div>
    </PhoneFrame>
  );
}
