import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { UserRoundCog } from "lucide-react";
import { LeadQueue } from "@/components/rm/LeadQueue";
import { LeadDetail } from "@/components/rm/LeadDetail";
import { LeadToasts } from "@/components/rm/LeadToasts";
import { useLeadFeed } from "@/components/rm/useLeadFeed";

const DEFAULT_SPACE_ID = "default";

/**
 * RM desktop console — the money-shot surface where a live `lead.created`
 * WS event lands as a structured Lead Packet the RM can act on immediately.
 * Judge-isolated demo spaces are addressed via `?space=`, same convention as
 * every other surface; falls back to the shared `default` space (backend
 * `app/core/spaces.py::DEFAULT_SPACE_ID`) when none is given.
 */
export default function RmDashboard() {
  const [searchParams] = useSearchParams();
  const spaceId = searchParams.get("space") || DEFAULT_SPACE_ID;

  const { leads, isLoading, isError, refetch, newLeadIds, pendingLeadIds, toasts, dismissToast, updateStatus } =
    useLeadFeed(spaceId);

  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);

  useEffect(() => {
    if (selectedLeadId && leads.some((lead) => lead.lead_id === selectedLeadId)) return;
    setSelectedLeadId(leads[0]?.lead_id ?? null);
    // Only re-run when the lead roster itself changes shape, not on every
    // selection change (that would fight the user's own click).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leads]);

  const selectedLead = useMemo(
    () => leads.find((lead) => lead.lead_id === selectedLeadId) ?? null,
    [leads, selectedLeadId]
  );

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col bg-neutral-50">
      <header className="flex shrink-0 items-center gap-3 border-b border-structural-800 bg-gradient-to-r from-structural-800 to-structural-700 px-6 py-5">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-structural-900/40 text-neutral-0">
          <UserRoundCog size={20} strokeWidth={1.75} aria-hidden="true" />
        </span>
        <div>
          <p className="text-caption font-semibold uppercase tracking-wide text-structural-200">
            Relationship Manager Console
          </p>
          <h1 className="font-display text-h3 font-semibold tracking-tight text-neutral-0">RM Desk</h1>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-[24rem_1fr]">
        <div className="min-h-0 border-r border-neutral-200 bg-neutral-0">
          <LeadQueue
            leads={leads}
            isLoading={isLoading}
            isError={isError}
            onRetry={refetch}
            newLeadIds={newLeadIds}
            selectedLeadId={selectedLeadId}
            onSelect={setSelectedLeadId}
          />
        </div>
        <div className="min-h-0">
          <LeadDetail
            lead={selectedLead}
            spaceId={spaceId}
            pending={selectedLead ? pendingLeadIds.has(selectedLead.lead_id) : false}
            onStatusChange={updateStatus}
          />
        </div>
      </div>

      <LeadToasts toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
