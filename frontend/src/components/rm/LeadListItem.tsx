import { motion } from "framer-motion";
import { Landmark, Wallet } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/format";
import type { LeadPacket } from "@/lib/types";
import { PriorityChip } from "./PriorityChip";
import { FAMILY_SHORT_LABEL, humanize } from "./text";

const STATUS_PILL_CLASSES: Record<LeadPacket["status"], string> = {
  new: "bg-structural-100 text-structural-700",
  contacted: "bg-warning-100 text-warning-700",
  converted: "bg-success-100 text-success-700",
};

const STATUS_LABEL: Record<LeadPacket["status"], string> = {
  new: "New",
  contacted: "Contacted",
  converted: "Converted",
};

export interface LeadListItemProps {
  lead: LeadPacket;
  isSelected: boolean;
  isNew: boolean;
  onSelect: () => void;
}

export function LeadListItem({ lead, isSelected, isNew, onSelect }: LeadListItemProps) {
  const FamilyIcon = lead.family === "investment_insurance" ? Landmark : Wallet;

  return (
    <motion.li
      layout
      initial={isNew ? { opacity: 0, y: -12, scale: 0.98 } : false}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
      className="list-none"
    >
      <button
        type="button"
        onClick={onSelect}
        aria-current={isSelected}
        className={cn(
          "flex w-full flex-col gap-2 border-l-2 border-transparent px-4 py-3 text-left transition-colors duration-[var(--motion-micro)] ease-out focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
          isSelected ? "border-l-structural-600 bg-structural-50" : "hover:bg-neutral-50",
          isNew && !isSelected && "bg-structural-50"
        )}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-neutral-100 text-neutral-600">
              <FamilyIcon size={16} strokeWidth={1.75} aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <p className="truncate text-body-sm font-semibold text-neutral-900">{lead.customer.name}</p>
              <p className="truncate text-caption text-neutral-500">
                {FAMILY_SHORT_LABEL[lead.family]} · {humanize(lead.customer.segment)}
              </p>
            </div>
          </div>
          <PriorityChip score={lead.priority_score} />
        </div>

        <p className="line-clamp-2 text-caption text-neutral-600">&ldquo;{lead.trigger.utterance}&rdquo;</p>

        <div className="flex items-center justify-between gap-2">
          <span className={cn("rounded-full px-2 py-0.5 text-caption font-medium", STATUS_PILL_CLASSES[lead.status])}>
            {STATUS_LABEL[lead.status]}
          </span>
          <span className="text-caption text-neutral-400">{formatDate(lead.created_at, { withTime: true })}</span>
        </div>
      </button>
    </motion.li>
  );
}
