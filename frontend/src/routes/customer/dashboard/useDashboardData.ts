/**
 * Data access for the Dashboard tab. Reuses the shared `queryKeys.customerSummary`
 * cache key (so `useAaConsent`'s existing invalidation — and this file's own
 * consent call — both refresh the same cached summary) but calls `apiGet`
 * directly with the *real* `CustomerDashboardSummary` shape (see `./types.ts`)
 * instead of `lib/queries.ts`'s `useCustomerSummary`, which is typed against
 * the shared `CustomerSummary` contract that does not match what the backend
 * actually returns.
 */
import { useCallback, useState } from "react";
import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api";
import { queryKeys } from "@/lib/queries";
import type { AaConsentStateReal, AaConsentStepReal, CustomerDashboardSummary } from "./types";

export function useDashboardSummary(
  sessionId: string | null | undefined
): UseQueryResult<CustomerDashboardSummary> {
  return useQuery({
    queryKey: queryKeys.customerSummary(sessionId ?? ""),
    queryFn: () => apiGet<CustomerDashboardSummary>(`/customer/${sessionId}/summary`),
    enabled: Boolean(sessionId),
  });
}

export interface UseAaConsentActionResult {
  /** Null when no request is in flight, else the step currently being granted/revoked. */
  pendingStep: AaConsentStepReal | null;
  setConsent: (step: AaConsentStepReal, granted: boolean) => Promise<AaConsentStateReal>;
}

/** Grants or revokes one of the two independent AA consents and refreshes
 * the cached summary so net worth / holdings recompute visibly. */
export function useAaConsentAction(sessionId: string | null | undefined): UseAaConsentActionResult {
  const queryClient = useQueryClient();
  const [pendingStep, setPendingStep] = useState<AaConsentStepReal | null>(null);

  const setConsent = useCallback(
    async (step: AaConsentStepReal, granted: boolean): Promise<AaConsentStateReal> => {
      if (!sessionId) throw new Error("No active session");
      setPendingStep(step);
      try {
        const result = await apiPost<AaConsentStateReal>("/aa/consent", {
          session_id: sessionId,
          step,
          granted,
        });
        await queryClient.invalidateQueries({ queryKey: queryKeys.customerSummary(sessionId) });
        return result;
      } finally {
        setPendingStep(null);
      }
    },
    [sessionId, queryClient]
  );

  return { pendingStep, setConsent };
}
