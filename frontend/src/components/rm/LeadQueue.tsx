import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Inbox } from "lucide-react";
import { DataState } from "@/components/shared/DataState";
import type { LeadPacket, LeadStatus } from "@/lib/types";
import { FamilyTabs, type FamilyFilter } from "./FamilyTabs";
import { FunnelTiles } from "./FunnelTiles";
import { LeadListItem } from "./LeadListItem";

export interface LeadQueueProps {
  leads: LeadPacket[];
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  newLeadIds: ReadonlySet<string>;
  selectedLeadId: string | null;
  onSelect: (leadId: string) => void;
}

const EMPTY_STATUS_COUNTS: Record<LeadStatus, number> = { new: 0, contacted: 0, converted: 0 };

function countByStatus(leads: LeadPacket[]): Record<LeadStatus, number> {
  const counts = { ...EMPTY_STATUS_COUNTS };
  for (const lead of leads) counts[lead.status] += 1;
  return counts;
}

function skeletonRow(key: number) {
  return (
    <div key={key} className="animate-pulse space-y-2 border-b border-neutral-100 px-4 py-3">
      <div className="flex items-center gap-2">
        <div className="size-8 rounded-full bg-neutral-100" />
        <div className="h-3.5 w-28 rounded-sm bg-neutral-100" />
        <div className="ml-auto h-5 w-16 rounded-full bg-neutral-100" />
      </div>
      <div className="h-3 w-full rounded-sm bg-neutral-100" />
      <div className="h-3 w-1/3 rounded-sm bg-neutral-100" />
    </div>
  );
}

/** Left pane: live, priority-sorted lead queue with family filters and a status funnel. */
export function LeadQueue({ leads, isLoading, isError, onRetry, newLeadIds, selectedLeadId, onSelect }: LeadQueueProps) {
  const [familyFilter, setFamilyFilter] = useState<FamilyFilter>("all");

  const counts = useMemo(
    () => ({
      all: leads.length,
      investment_insurance: leads.filter((l) => l.family === "investment_insurance").length,
      loans_cards: leads.filter((l) => l.family === "loans_cards").length,
    }),
    [leads]
  );

  const filteredLeads = useMemo(
    () => (familyFilter === "all" ? leads : leads.filter((lead) => lead.family === familyFilter)),
    [leads, familyFilter]
  );

  const funnelCounts = useMemo(() => countByStatus(filteredLeads), [filteredLeads]);

  const status = isLoading ? "loading" : isError ? "error" : filteredLeads.length === 0 ? "empty" : "success";

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 space-y-4 border-b border-neutral-200 px-4 py-4">
        <FamilyTabs value={familyFilter} onChange={setFamilyFilter} counts={counts} />
        <FunnelTiles counts={funnelCounts} />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <DataState
          status={status}
          onRetry={onRetry}
          errorTitle="Couldn't load the lead queue"
          errorDescription="The lead list didn't come through. Your leads are safe — try again."
          emptyIcon={Inbox}
          emptyTitle={leads.length === 0 ? "No leads yet" : "No leads in this category yet"}
          emptyDescription={
            leads.length === 0
              ? "Leads from customer conversations appear here instantly."
              : "Switch tabs or check back once a matching conversation routes here."
          }
          skeleton={<div className="pt-2">{[0, 1, 2, 3].map(skeletonRow)}</div>}
          className="h-full justify-center rounded-none border-0"
        >
          <motion.ul layout className="divide-y divide-neutral-100">
            {filteredLeads.map((lead) => (
              <LeadListItem
                key={lead.lead_id}
                lead={lead}
                isSelected={lead.lead_id === selectedLeadId}
                isNew={newLeadIds.has(lead.lead_id)}
                onSelect={() => onSelect(lead.lead_id)}
              />
            ))}
          </motion.ul>
        </DataState>
      </div>
    </div>
  );
}
