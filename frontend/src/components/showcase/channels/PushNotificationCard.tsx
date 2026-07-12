import { motion } from "framer-motion";
import { Bot } from "lucide-react";
import { PhoneFrame } from "@/components/shared/PhoneFrame";
import { SampleTag } from "@/components/showcase/channels/SampleTag";
import type { ChannelDelivery } from "@/components/showcase/channels/types";

const EASE_OUT: [number, number, number, number] = [0.22, 1, 0.36, 1];

/** Lockscreen-style push notification banner, staged inside the shared IDBI phone shell. */
export function PushNotificationCard({ delivery }: { delivery: ChannelDelivery }) {
  return (
    <PhoneFrame headerTitle="Lock screen">
      <div className="flex h-full flex-col items-center bg-gradient-to-b from-neutral-900 to-neutral-950 px-4 pt-12 pb-6 text-neutral-0">
        <p className="font-display text-h1 font-bold tabular-nums">9:41</p>
        <p className="mt-1 text-body-sm text-neutral-300">Saturday, 12 July</p>

        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: EASE_OUT }}
          className="mt-12 w-full rounded-lg border border-neutral-700 bg-neutral-800/90 p-3 shadow-float-lg"
        >
          <div className="flex items-center gap-2">
            <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-brand-500 text-neutral-950">
              <Bot size={14} strokeWidth={2} aria-hidden="true" />
            </span>
            <span className="text-caption font-semibold text-neutral-200">WealthMitra</span>
            <span className="text-caption text-neutral-400">now</span>
            {delivery.sample && (
              <span className="ml-auto">
                <SampleTag />
              </span>
            )}
          </div>
          <p className="mt-2 text-body-sm font-semibold text-neutral-0">{delivery.title}</p>
          <p className="mt-0.5 line-clamp-3 text-body-sm text-neutral-300">{delivery.body}</p>
        </motion.div>

        <p className="mt-auto text-caption text-neutral-500">Simulated delivery · real AI-generated copy</p>
      </div>
    </PhoneFrame>
  );
}
