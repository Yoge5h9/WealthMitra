import { cn } from "@/lib/utils";
import type { ChannelDelivery, ChannelKey } from "./types";

export function ChannelFitNote({ delivery, channel }: { delivery: ChannelDelivery; channel: ChannelKey }) {
  const fit = delivery.channelFits[channel];
  return (
    <div className="border-t border-neutral-200 bg-neutral-0 px-3 py-2">
      <p className={cn("text-caption font-semibold", fit.emphasis === "primary" ? "text-structural-700" : "text-neutral-600")}>
        {fit.label} · why this channel
      </p>
      <p className="mt-0.5 text-caption text-neutral-500">{fit.reason}</p>
    </div>
  );
}
