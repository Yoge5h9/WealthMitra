import { Dialog } from "radix-ui";
import { X } from "lucide-react";
import { formatDate } from "@/lib/format";
import { DataState } from "@/components/shared/DataState";
import { useAudit } from "@/lib/queries";
import type { AuditEntry, AuditEntryKind } from "@/lib/types";

export interface AuditDrawerProps {
  sessionId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const KIND_LABEL: Record<AuditEntryKind, string> = {
  tool_call: "Data lookup",
  llm_call: "Companion reply",
  routing: "Routing decision",
  guardrail: "Guardrail check",
  execution: "Execution",
  consent: "Consent",
};

function summarize(entry: AuditEntry): string {
  const parts = Object.entries(entry.outputs_summary)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .slice(0, 4)
    .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`);
  return parts.join(" · ");
}

function EntryRow({ entry }: { entry: AuditEntry }) {
  return (
    <li className="rounded-lg border border-neutral-200 bg-neutral-0 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="rounded-xs bg-structural-50 px-2 py-1 text-caption font-semibold uppercase tracking-wide text-structural-700">
          {KIND_LABEL[entry.kind]}
        </span>
        <span className="text-caption tabular-nums text-neutral-500">{formatDate(entry.ts, { withTime: true })}</span>
      </div>
      <p className="mt-2 text-body-sm font-medium text-neutral-800">{entry.name}</p>
      {summarize(entry) && <p className="mt-1 text-caption text-neutral-600">{summarize(entry)}</p>}
      {entry.refs.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {entry.refs.map((ref) => (
            <span key={ref} className="rounded-xs bg-neutral-100 px-2 py-1 text-caption text-neutral-600">
              {ref}
            </span>
          ))}
        </div>
      )}
    </li>
  );
}

/** "Why this number" drawer — every tool call, LLM call, routing decision
 * and guardrail verdict for this session, in append order. */
export function AuditDrawer({ sessionId, open, onOpenChange }: AuditDrawerProps) {
  const audit = useAudit(open ? sessionId : null);

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-neutral-950/40" />
        <Dialog.Content
          className="fixed inset-y-0 right-0 z-50 flex w-full max-w-sm flex-col rounded-l-xl border-l border-neutral-200 bg-neutral-50 shadow-float-xl"
          aria-describedby={undefined}
        >
          <div className="flex items-center justify-between border-b border-neutral-200 bg-neutral-0 px-4 py-3">
            <div>
              <Dialog.Title className="font-display text-h4 font-semibold text-neutral-900">
                Why this number
              </Dialog.Title>
              <p className="text-caption text-neutral-500">Every tool call, reply, and check for this conversation</p>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                aria-label="Close audit trail"
                className="flex size-11 shrink-0 items-center justify-center rounded-full text-neutral-500 hover:text-neutral-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
              >
                <X size={20} strokeWidth={1.75} />
              </button>
            </Dialog.Close>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            <DataState
              status={audit.isLoading ? "loading" : audit.isError ? "error" : (audit.data?.length ?? 0) === 0 ? "empty" : "success"}
              emptyTitle="No audit entries yet"
              emptyDescription="Ask WealthMitra something — every data lookup and decision will show up here."
              errorDescription="Couldn't load the audit trail. Your data is unaffected — try again."
              onRetry={() => void audit.refetch()}
            >
              <ul className="space-y-2">{audit.data?.map((entry) => <EntryRow key={entry.id} entry={entry} />)}</ul>
            </DataState>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
