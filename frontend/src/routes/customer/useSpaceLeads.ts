/**
 * Judge-cockpit affordance: does the current space have any routed leads
 * yet? Seeds from `GET /spaces/{spaceId}/leads` on mount/space-change, then
 * stays live via `lead.created` on the same space's WebSocket — this is
 * what lets the JudgePanel go from "calm" to "a lead just landed, come look"
 * without a manual refresh.
 */
import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { useSpaceSocket } from "@/hooks/useSpaceSocket";

export interface UseSpaceLeadsResult {
  count: number;
  hasLeads: boolean;
}

export function useSpaceLeads(spaceId: string | null): UseSpaceLeadsResult {
  const [count, setCount] = useState(0);
  const { subscribe } = useSpaceSocket(spaceId);

  useEffect(() => {
    if (!spaceId) {
      setCount(0);
      return;
    }
    let cancelled = false;
    apiGet<unknown[]>(`/spaces/${spaceId}/leads`)
      .then((leads) => {
        if (!cancelled) setCount(Array.isArray(leads) ? leads.length : 0);
      })
      .catch(() => {
        // Best-effort seed — a judge-facing convenience panel must never
        // throw or block the real customer surface it sits beside.
      });
    return () => {
      cancelled = true;
    };
  }, [spaceId]);

  useEffect(() => {
    if (!spaceId) return undefined;
    return subscribe("lead.created", () => {
      setCount((prev) => prev + 1);
    });
  }, [subscribe, spaceId]);

  return { count, hasLeads: count > 0 };
}
