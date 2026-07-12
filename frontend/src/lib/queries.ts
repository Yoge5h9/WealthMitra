/**
 * TanStack Query hooks typed against the backend API surface (see
 * `lib/types.ts`). Every data-bearing view should consume its data
 * through one of these rather than calling `apiGet`/`apiPost` directly, so
 * cache keys and invalidation stay consistent across surfaces.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api";
import type {
  AaConsentRequest,
  AaState,
  AuditEntry,
  ChatRequest,
  CreateSessionRequest,
  CreateSessionResponse,
  CreateSpaceResponse,
  CustomerSummary,
  ExecuteRequest,
  LeadPacket,
  LeadStatus,
  Nudge,
  Persona,
  Receipt,
} from "@/lib/types";

export const queryKeys = {
  personas: ["personas"] as const,
  customerSummary: (sessionId: string) => ["customer", sessionId, "summary"] as const,
  rmCustomerSummary: (spaceId: string, personaId: string) =>
    ["spaces", spaceId, "customers", personaId, "summary"] as const,
  nudges: (sessionId: string) => ["customer", sessionId, "nudges"] as const,
  leads: (spaceId: string) => ["spaces", spaceId, "leads"] as const,
  audit: (sessionId: string) => ["audit", sessionId] as const,
};

export function usePersonas(): UseQueryResult<Persona[]> {
  return useQuery({
    queryKey: queryKeys.personas,
    queryFn: () => apiGet<Persona[]>("/personas"),
  });
}

export function useCustomerSummary(sessionId: string | null | undefined): UseQueryResult<CustomerSummary> {
  return useQuery({
    queryKey: queryKeys.customerSummary(sessionId ?? ""),
    queryFn: () => apiGet<CustomerSummary>(`/customer/${sessionId}/summary`),
    enabled: Boolean(sessionId),
  });
}

export function useRmCustomerSummary(
  spaceId: string | null | undefined,
  personaId: string | null | undefined,
): UseQueryResult<CustomerSummary> {
  return useQuery({
    queryKey: queryKeys.rmCustomerSummary(spaceId ?? "", personaId ?? ""),
    queryFn: () => apiGet<CustomerSummary>(`/spaces/${spaceId}/customers/${personaId}/summary`),
    enabled: Boolean(spaceId && personaId),
  });
}

export function useNudges(sessionId: string | null | undefined): UseQueryResult<Nudge[]> {
  return useQuery({
    queryKey: queryKeys.nudges(sessionId ?? ""),
    queryFn: () => apiGet<Nudge[]>(`/customer/${sessionId}/nudges`),
    enabled: Boolean(sessionId),
  });
}

export function useLeads(spaceId: string | null | undefined): UseQueryResult<LeadPacket[]> {
  return useQuery({
    queryKey: queryKeys.leads(spaceId ?? ""),
    queryFn: () => apiGet<LeadPacket[]>(`/spaces/${spaceId}/leads`),
    enabled: Boolean(spaceId),
  });
}

export function useAudit(sessionId: string | null | undefined): UseQueryResult<AuditEntry[]> {
  return useQuery({
    queryKey: queryKeys.audit(sessionId ?? ""),
    queryFn: () => apiGet<AuditEntry[]>(`/audit/${sessionId}`),
    enabled: Boolean(sessionId),
  });
}

export function useCreateSpace(): UseMutationResult<CreateSpaceResponse, Error, void> {
  return useMutation({
    mutationFn: () => apiPost<CreateSpaceResponse>("/spaces"),
  });
}

export function useResetSpace(): UseMutationResult<void, Error, string> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (spaceId: string) => apiPost<void>(`/spaces/${spaceId}/reset`),
    onSuccess: (_data, spaceId) => {
      void queryClient.invalidateQueries({ queryKey: ["spaces", spaceId] });
    },
  });
}

export function useCreateSession(): UseMutationResult<
  CreateSessionResponse,
  Error,
  { spaceId: string; body: CreateSessionRequest }
> {
  return useMutation({
    mutationFn: ({ spaceId, body }) =>
      apiPost<CreateSessionResponse>(`/spaces/${spaceId}/sessions`, body),
  });
}

/**
 * Sends a chat turn. The response is an SSE stream (token/card/avatar/done
 * frames), so this posts the request and hands back the
 * raw `Response` for the caller to read as a stream — TanStack Query's
 * cache model isn't a fit for a streaming body.
 */
export async function sendChatMessage(body: ChatRequest): Promise<Response> {
  return fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
  });
}

export function useUpdateLeadStatus(): UseMutationResult<
  void,
  Error,
  { leadId: string; status: LeadStatus; spaceId: string }
> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ leadId, status, spaceId }) =>
      apiPost<void>(`/leads/${leadId}/status?space_id=${encodeURIComponent(spaceId)}`, { status }),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.leads(variables.spaceId) });
    },
  });
}

export function useExecute(): UseMutationResult<Receipt, Error, ExecuteRequest> {
  return useMutation({
    mutationFn: (body) => apiPost<Receipt>("/execute", body),
  });
}

export function useAaConsent(): UseMutationResult<AaState, Error, AaConsentRequest> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body) => apiPost<AaState>("/aa/consent", body),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.customerSummary(variables.session_id),
      });
    },
  });
}
