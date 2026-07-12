import { motion } from "framer-motion";
import { ChevronLeft } from "lucide-react";
import { PhoneFrame } from "@/components/shared/PhoneFrame";
import { SampleTag } from "@/components/showcase/channels/SampleTag";
import { ChannelFitNote } from "@/components/showcase/channels/ChannelFitNote";
import type { ChannelDelivery } from "@/components/showcase/channels/types";

const EASE_OUT: [number, number, number, number] = [0.22, 1, 0.36, 1];

// SMS carriers hard-wrap around this length — the mock reflects that
// instead of showing an unrealistically long single message.
const SMS_CHAR_LIMIT = 160;

function toSmsBody(delivery: ChannelDelivery): string {
  const raw = `WM-IDBIBK: ${delivery.body}`;
  return raw.length > SMS_CHAR_LIMIT ? `${raw.slice(0, SMS_CHAR_LIMIT - 1)}…` : raw;
}

/** SMS app thread view — a single incoming short-code message bubble. */
export function SmsThreadCard({ delivery }: { delivery: ChannelDelivery }) {
  return (
    <PhoneFrame headerTitle="Messages">
      <div className="flex h-full flex-col">
        <div className="flex items-center gap-2 border-b border-neutral-200 bg-neutral-0 px-3 py-2.5">
          <ChevronLeft size={18} strokeWidth={1.75} className="text-neutral-500" aria-hidden="true" />
          <div>
            <p className="text-body-sm font-semibold text-neutral-900">WM-IDBIBK</p>
            <p className="text-caption text-neutral-500">SMS · IDBI Bank</p>
          </div>
          {delivery.sample && <span className="ml-auto"><SampleTag /></span>}
        </div>

        <div className="flex-1 space-y-2 bg-neutral-50 p-3">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: EASE_OUT }}
            className="max-w-[85%] rounded-lg rounded-tl-xs border border-neutral-200 bg-neutral-0 px-3 py-2 text-body-sm text-neutral-800"
          >
            {toSmsBody(delivery)}
          </motion.div>
          <p className="pl-1 text-caption text-neutral-400">Delivered · now</p>
        </div>

        <ChannelFitNote delivery={delivery} channel="sms" />
        <p className="bg-neutral-0 px-3 pb-2 text-caption text-neutral-500">Simulated delivery · real AI-generated copy</p>
      </div>
    </PhoneFrame>
  );
}
