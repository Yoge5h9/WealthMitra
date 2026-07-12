/**
 * Live lead-queue state for the RM console: wraps `useLeads` with the
 * `/ws/{space}` `lead.created`/`lead.updated` stream so new leads slide in
 * instantly and status changes reconcile without a manual refetch.
 *
 * Status updates go straight through `apiPost` rather than the shared
 * `useUpdateLeadStatus` mutation — that hook's `mutationFn` never appends
 * `space_id`, but `POST /api/leads/{id}/status` requires it as a REQUIRED
 * query param (backend: `app/api/leads.py`, a 422 without it). Fixing the
 * shared hook is out of scope here (frontend/src/lib is a shared tree this
 * task doesn't own), so this hook calls the endpoint directly with the
 * query param attached.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiPost } from "@/lib/api";
import { queryKeys, useLeads } from "@/lib/queries";
import { useSpaceSocket } from "@/hooks/useSpaceSocket";
import type { LeadPacket, LeadStatus } from "@/lib/types";
import { FAMILY_SHORT_LABEL } from "./text";

export interface LeadToast {
  id: string;
  title: string;
  description: string;
}

export interface UseLeadFeedResult {
  leads: LeadPacket[];
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
  newLeadIds: ReadonlySet<string>;
  pendingLeadIds: ReadonlySet<string>;
  toasts: LeadToast[];
  dismissToast: (id: string) => void;
  updateStatus: (leadId: string, status: LeadStatus) => void;
}

const NEW_LEAD_HIGHLIGHT_MS = 4000;
const TOAST_LIFETIME_MS = 5000;

function sortByPriorityDesc(leads: LeadPacket[]): LeadPacket[] {
  return [...leads].sort((a, b) => b.priority_score - a.priority_score);
}

export function useLeadFeed(spaceId: string): UseLeadFeedResult {
  const queryClient = useQueryClient();
  const query = useLeads(spaceId);
  const { subscribe } = useSpaceSocket(spaceId);

  const [newLeadIds, setNewLeadIds] = useState<Set<string>>(new Set());
  const [pendingLeadIds, setPendingLeadIds] = useState<Set<string>>(new Set());
  const [toasts, setToasts] = useState<LeadToast[]>([]);
  const timersRef = useRef<Set<number>>(new Set());
  // Toast/highlight dedupe: the same `lead.created` event can arrive more
  // than once (two sockets briefly alive across a StrictMode remount, or a
  // server-side redeliver). The cache update below is already idempotent;
  // this keeps the one-shot side effects one-shot too.
  const announcedLeadIdsRef = useRef<Set<string>>(new Set());

  const setTimer = useCallback((fn: () => void, ms: number) => {
    const handle = window.setTimeout(() => {
      timersRef.current.delete(handle);
      fn();
    }, ms);
    timersRef.current.add(handle);
  }, []);

  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      timers.forEach((handle) => window.clearTimeout(handle));
      timers.clear();
    };
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  useEffect(() => {
    const key = queryKeys.leads(spaceId);

    const unsubCreated = subscribe("lead.created", (lead) => {
      queryClient.setQueryData<LeadPacket[]>(key, (old) => {
        const withoutDup = (old ?? []).filter((existing) => existing.lead_id !== lead.lead_id);
        return sortByPriorityDesc([...withoutDup, lead]);
      });

      if (announcedLeadIdsRef.current.has(lead.lead_id)) return;
      announcedLeadIdsRef.current.add(lead.lead_id);

      setNewLeadIds((prev) => new Set(prev).add(lead.lead_id));
      setTimer(() => {
        setNewLeadIds((prev) => {
          if (!prev.has(lead.lead_id)) return prev;
          const next = new Set(prev);
          next.delete(lead.lead_id);
          return next;
        });
      }, NEW_LEAD_HIGHLIGHT_MS);

      const toastId = `${lead.lead_id}-${Date.now()}`;
      setToasts((prev) => [
        ...prev,
        {
          id: toastId,
          title: `New lead: ${lead.customer.name}`,
          description: FAMILY_SHORT_LABEL[lead.family],
        },
      ]);
      setTimer(() => dismissToast(toastId), TOAST_LIFETIME_MS);
    });

    const unsubUpdated = subscribe("lead.updated", (lead) => {
      queryClient.setQueryData<LeadPacket[]>(key, (old) =>
        sortByPriorityDesc((old ?? []).map((existing) => (existing.lead_id === lead.lead_id ? lead : existing)))
      );
      setPendingLeadIds((prev) => {
        if (!prev.has(lead.lead_id)) return prev;
        const next = new Set(prev);
        next.delete(lead.lead_id);
        return next;
      });
    });

    return () => {
      unsubCreated();
      unsubUpdated();
    };
  }, [spaceId, subscribe, queryClient, dismissToast, setTimer]);

  const updateStatus = useCallback(
    (leadId: string, status: LeadStatus) => {
      const key = queryKeys.leads(spaceId);
      const previous = queryClient.getQueryData<LeadPacket[]>(key);

      setPendingLeadIds((prev) => new Set(prev).add(leadId));
      queryClient.setQueryData<LeadPacket[]>(key, (old) =>
        (old ?? []).map((lead) => (lead.lead_id === leadId ? { ...lead, status } : lead))
      );

      apiPost<void>(`/leads/${leadId}/status?space_id=${encodeURIComponent(spaceId)}`, { status }).catch(() => {
        queryClient.setQueryData(key, previous);
        setPendingLeadIds((prev) => {
          const next = new Set(prev);
          next.delete(leadId);
          return next;
        });
      });
    },
    [spaceId, queryClient]
  );

  const leads = useMemo(() => sortByPriorityDesc(query.data ?? []), [query.data]);

  return {
    leads,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: () => void query.refetch(),
    newLeadIds,
    pendingLeadIds,
    toasts,
    dismissToast,
    updateStatus,
  };
}
