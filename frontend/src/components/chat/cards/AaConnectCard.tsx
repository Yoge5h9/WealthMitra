import { useState } from "react";
import { CheckCircle2, Link2, Loader2, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { apiPost } from "@/lib/api";
import type { AaConnectCard as AaConnectCardData } from "./types";

interface AaConsentResult {
  transfer_granted: boolean;
  processing_granted: boolean;
  connected: boolean;
}

/** A short, consent-first version of the AA flow for the cold-start chat.
 * The two checkboxes are selected locally first; permissions are only written
 * after the customer presses the explicit connect button. */
export function AaConnectCard({ card, sessionId }: { card: AaConnectCardData; sessionId: string | null }) {
  const [transfer, setTransfer] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function connect() {
    if (!sessionId || !transfer || !processing) return;
    setConnecting(true);
    setError(null);
    try {
      await apiPost<AaConsentResult>("/aa/consent", { session_id: sessionId, step: "transfer", granted: true });
      const result = await apiPost<AaConsentResult>("/aa/consent", { session_id: sessionId, step: "processing", granted: true });
      setTransfer(result.transfer_granted);
      setProcessing(result.processing_granted);
      setConnected(result.connected);
    } catch {
      setError("We couldn’t save your permissions. Please try again.");
    } finally {
      setConnecting(false);
    }
  }

  async function revoke() {
    if (!sessionId) return;
    setConnecting(true);
    setError(null);
    try {
      await apiPost<AaConsentResult>("/aa/consent", { session_id: sessionId, step: "processing", granted: false });
      const result = await apiPost<AaConsentResult>("/aa/consent", { session_id: sessionId, step: "transfer", granted: false });
      setTransfer(result.transfer_granted);
      setProcessing(result.processing_granted);
      setConnected(result.connected);
    } catch {
      setError("We couldn’t revoke your permissions. Please try again.");
    } finally {
      setConnecting(false);
    }
  }

  return (
    <Card className="border border-neutral-200">
      <CardHeader>
        <div className="flex items-center gap-2 text-structural-600">
          <Link2 size={18} strokeWidth={1.75} />
          <CardTitle>
            <span className="font-display text-h4 text-neutral-900">{card.headline}</span>
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-body-sm text-neutral-700">{card.body}</p>
        {connected ? (
          <>
            <div className="flex items-start gap-2 rounded-sm bg-success-50 p-3 text-body-sm text-success-800">
              <CheckCircle2 className="mt-0.5 shrink-0" size={17} strokeWidth={1.75} aria-hidden="true" />
              <p>Permissions saved. When an eligible account is connected, its data can make your WealthMitra view more complete.</p>
            </div>
            {error && <p role="alert" className="text-caption text-danger-700">{error}</p>}
            <Button size="touch" variant="outline" disabled={!sessionId || connecting} onClick={() => void revoke()}>
              Revoke permissions
            </Button>
          </>
        ) : (
          <>
            <label className="flex cursor-pointer items-start gap-3 rounded-sm border border-neutral-200 p-3">
              <input className="mt-1 size-4 accent-[var(--color-structural-600)]" type="checkbox" checked={transfer} onChange={(event) => setTransfer(event.target.checked)} />
              <span><span className="block text-body-sm font-medium text-neutral-900">Share external account data via AA</span><span className="mt-0.5 block text-caption text-neutral-600">This permits Account Aggregator to transfer eligible account data. It does not permit WealthMitra to use it.</span></span>
            </label>
            <label className="flex cursor-pointer items-start gap-3 rounded-sm border border-neutral-200 p-3">
              <input className="mt-1 size-4 accent-[var(--color-structural-600)]" type="checkbox" checked={processing} onChange={(event) => setProcessing(event.target.checked)} />
              <span><span className="block text-body-sm font-medium text-neutral-900">Use connected data for my WealthMitra view</span><span className="mt-0.5 block text-caption text-neutral-600">This separate DPDP permission lets WealthMitra analyse the transferred data for your dashboard.</span></span>
            </label>
            {error && <p role="alert" className="text-caption text-danger-700">{error}</p>}
            <Button size="touch" className="gap-2" disabled={!sessionId || !transfer || !processing || connecting} onClick={() => void connect()}>
              {connecting ? <Loader2 size={18} className="animate-spin" aria-hidden="true" /> : <ShieldCheck size={18} strokeWidth={1.75} aria-hidden="true" />}
              {connecting ? "Saving permissions…" : "Connect with my permission"}
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}
