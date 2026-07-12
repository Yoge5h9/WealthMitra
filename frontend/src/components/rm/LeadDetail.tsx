import type { ReactNode } from "react";
import { useState } from "react";
import { CheckCircle2, CircleDashed, Landmark, LayoutGrid, Lightbulb, Scale, Target, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { formatDate, formatINR } from "@/lib/format";
import { MoneyText } from "@/components/shared/MoneyText";
import type { LeadPacket, LeadStatus, PersonaHolding, PersonaLiability } from "@/lib/types";
import { PriorityChip } from "./PriorityChip";
import { RiskMeter } from "./RiskMeter";
import { StatusActions } from "./StatusActions";
import { priorityBreakdown } from "./priority";
import { FAMILY_LABEL, humanize, languageLabel } from "./text";
import { CustomerDrawer } from "./CustomerDrawer";

export interface LeadDetailProps {
  lead: LeadPacket | null;
  spaceId: string;
  pending: boolean;
  onStatusChange: (leadId: string, status: LeadStatus) => void;
  className?: string;
}

function Panel({ title, icon: Icon, action, children }: { title: string; icon: typeof UserRound; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-neutral-200 bg-neutral-0">
      <header className="flex items-center justify-between gap-3 border-b border-neutral-100 px-4 py-3">
        <div className="flex items-center gap-2">
          <Icon size={16} strokeWidth={1.75} className="text-structural-600" aria-hidden="true" />
          <h4 className="text-body-sm font-semibold uppercase tracking-wide text-neutral-500">{title}</h4>
        </div>
        {action}
      </header>
      <div className="px-4 py-4">{children}</div>
    </section>
  );
}

function LabelValue({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <p className="text-caption text-neutral-500">{label}</p>
      <p className="mt-0.5 text-body-sm font-medium text-neutral-900">{value}</p>
    </div>
  );
}

/**
 * `external_holdings`/`liabilities` are typed as `number` in `LeadFinancialSnapshot`
 * (lib/types.ts) but the backend (`app/routing/leads.py`) actually fills them with
 * arrays of holding/liability records. Narrow defensively rather than trust the
 * stale type, and fall back to a plain total if a future backend change makes the
 * type true again.
 */
function asRecordList<T>(value: unknown): T[] | null {
  return Array.isArray(value) ? (value as T[]) : null;
}

/**
 * Suitability reasons arrive as machine strings straight from the routing
 * engine (`family=investment_insurance`, `shelf_size=1`, snake_case notes).
 * Keep the content verbatim-traceable but render it in words.
 */
function humanizeReason(reason: string): string {
  const sentenceCase = (value: string) => {
    const spaced = value.split("_").filter(Boolean).join(" ");
    return spaced.charAt(0).toUpperCase() + spaced.slice(1);
  };
  const eq = reason.indexOf("=");
  if (eq > 0) {
    return `${sentenceCase(reason.slice(0, eq))}: ${humanize(reason.slice(eq + 1))}`;
  }
  return sentenceCase(reason);
}

export function LeadDetail({ lead, spaceId, pending, onStatusChange, className }: LeadDetailProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  if (!lead) {
    return (
      <div className={cn("flex h-full flex-col items-center justify-center gap-3 px-6 text-center", className)}>
        <span className="flex size-11 items-center justify-center rounded-full bg-neutral-100 text-neutral-500">
          <LayoutGrid size={20} strokeWidth={1.75} />
        </span>
        <div className="space-y-1">
          <p className="text-body-sm font-medium text-neutral-700">Select a lead</p>
          <p className="max-w-xs text-caption text-neutral-600">
            Choose a lead from the queue on the left to see its full Lead Packet.
          </p>
        </div>
      </div>
    );
  }

  const holdings = asRecordList<PersonaHolding>(lead.financial_snapshot.external_holdings);
  const liabilities = asRecordList<PersonaLiability>(lead.financial_snapshot.liabilities);
  const holdingsTotal = holdings === null ? Number(lead.financial_snapshot.external_holdings) : null;
  const liabilitiesTotal = liabilities === null ? Number(lead.financial_snapshot.liabilities) : null;

  return (
    <div className={cn("flex h-full flex-col", className)}>
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-6">
        {/* Header: customer + priority + status actions */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-caption font-semibold uppercase tracking-wide text-structural-600">
              {FAMILY_LABEL[lead.family]} · {lead.lead_id}
            </p>
            <h2 className="mt-1 font-display text-h3 font-semibold tracking-tight text-neutral-900">
              {lead.customer.name}
            </h2>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-caption text-neutral-600">
              <span className="rounded-full bg-neutral-100 px-3 py-1 font-medium text-neutral-700">
                {humanize(lead.customer.segment)}
              </span>
              <span className="rounded-full bg-neutral-100 px-3 py-1 font-medium text-neutral-700">
                Age {lead.customer.age_band}
              </span>
              <span className="rounded-full bg-neutral-100 px-3 py-1 font-medium text-neutral-700">
                {humanize(lead.customer.city_tier)}
              </span>
              <span className="rounded-full bg-structural-100 px-3 py-1 font-medium text-structural-700">
                {languageLabel(lead.customer.language)}
              </span>
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            <PriorityChip score={lead.priority_score} className="text-body-sm" />
            <Button size="sm" variant="outline" onClick={() => setDrawerOpen(true)}>
              View full customer analysis
            </Button>
          </div>
        </div>

        <StatusActions status={lead.status} pending={pending} onChange={(status) => onStatusChange(lead.lead_id, status)} />

        {/* Next best action callout — asymmetric hero, not another equal-width card */}
        <div className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-3">
          <p className="text-caption font-semibold uppercase tracking-wide text-brand-700">Next best action</p>
          <p className="mt-1 text-body-sm font-medium text-neutral-900">{lead.next_best_action}</p>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Panel title="Trigger" icon={Lightbulb}>
            <div className="space-y-2">
              <LabelValue label="Type" value={humanize(lead.trigger.type)} />
              <blockquote className="border-l-2 border-neutral-200 pl-3 text-body-sm italic text-neutral-700">
                &ldquo;{lead.trigger.utterance}&rdquo;
              </blockquote>
              <p className="text-caption text-neutral-500">{formatDate(lead.trigger.ts, { withTime: true })}</p>
            </div>
          </Panel>

          <Panel title="Consent" icon={Scale}>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                {lead.consent.aa_consent_id ? (
                  <CheckCircle2 size={18} strokeWidth={1.75} className="shrink-0 text-success-600" aria-hidden="true" />
                ) : (
                  <CircleDashed size={18} strokeWidth={1.75} className="shrink-0 text-neutral-400" aria-hidden="true" />
                )}
                <div>
                  <p className="text-body-sm font-medium text-neutral-900">AA data-transfer consent</p>
                  <p className="text-caption text-neutral-500">
                    {lead.consent.aa_consent_id ? `Linked · ${lead.consent.aa_consent_id}` : "Not linked"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {lead.consent.advice_consent ? (
                  <CheckCircle2 size={18} strokeWidth={1.75} className="shrink-0 text-success-600" aria-hidden="true" />
                ) : (
                  <CircleDashed size={18} strokeWidth={1.75} className="shrink-0 text-neutral-400" aria-hidden="true" />
                )}
                <div>
                  <p className="text-body-sm font-medium text-neutral-900">DPDP advisory-use consent</p>
                  <p className="text-caption text-neutral-500">
                    {lead.consent.advice_consent ? "Granted" : "Not yet granted"}
                  </p>
                </div>
              </div>
            </div>
          </Panel>
        </div>

        <Panel title="Financial snapshot" icon={Landmark}>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <p className="text-caption text-neutral-500">Monthly income</p>
              <MoneyText
                value={lead.financial_snapshot.monthly_income}
                size="md"
                whyThisNumber="Computed by the deterministic analytics engine from salary credits, snapshotted into the Lead Packet at lead creation."
              />
            </div>
            <div>
              <p className="text-caption text-neutral-500">Monthly surplus</p>
              <MoneyText
                value={lead.financial_snapshot.monthly_surplus}
                size="md"
                whyThisNumber="Income minus recurring debits over the analysis window — deterministic engine output, snapshotted at lead creation."
              />
            </div>
            <div>
              <p className="text-caption text-neutral-500">Idle balance</p>
              <MoneyText
                value={lead.financial_snapshot.idle_balance}
                size="md"
                whyThisNumber="Un-deployed savings balance from the customer's accounts — deterministic engine output, snapshotted at lead creation."
              />
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 border-t border-neutral-100 pt-4 sm:grid-cols-2">
            <div>
              <p className="mb-2 text-caption font-medium text-neutral-600">External holdings</p>
              {holdings && holdings.length > 0 ? (
                <ul className="space-y-2">
                  {holdings.map((holding, index) => (
                    <li key={holding.id ?? index} className="flex items-center justify-between text-body-sm">
                      <span className="text-neutral-700">
                        {humanize(holding.type)} · {holding.institution}
                      </span>
                      <span className="tabular-nums font-medium text-neutral-900">{formatINR(holding.amount)}</span>
                    </li>
                  ))}
                </ul>
              ) : holdingsTotal !== null && Number.isFinite(holdingsTotal) ? (
                <MoneyText value={holdingsTotal} size="sm" />
              ) : (
                <p className="text-caption text-neutral-500">None on record.</p>
              )}
            </div>
            <div>
              <p className="mb-2 text-caption font-medium text-neutral-600">Liabilities</p>
              {liabilities && liabilities.length > 0 ? (
                <ul className="space-y-2">
                  {liabilities.map((liability, index) => (
                    <li key={liability.id ?? index} className="flex items-center justify-between text-body-sm">
                      <span className="text-neutral-700">
                        {humanize(liability.type)} · {liability.lender}
                      </span>
                      <span className="tabular-nums font-medium text-neutral-900">{formatINR(liability.principal)}</span>
                    </li>
                  ))}
                </ul>
              ) : liabilitiesTotal !== null && Number.isFinite(liabilitiesTotal) ? (
                <MoneyText value={liabilitiesTotal} size="sm" />
              ) : (
                <p className="text-caption text-neutral-500">None on record.</p>
              )}
            </div>
          </div>
        </Panel>

        <Panel title="Two-axis risk" icon={Scale}>
          <RiskMeter capacityScore={lead.risk.capacity_score} toleranceScore={lead.risk.tolerance_score} band={lead.risk.band} />
        </Panel>

        <Panel title="Goals" icon={Target}>
          {lead.goals.length === 0 ? (
            <p className="text-caption text-neutral-500">No goals set yet.</p>
          ) : (
            <ul className="space-y-3">
              {lead.goals.map((goal) => (
                <li key={goal.name} className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-body-sm font-medium text-neutral-900">{goal.name}</p>
                    <p className="text-caption text-neutral-500">{goal.horizon_years}-year horizon</p>
                  </div>
                  <MoneyText value={goal.target} size="sm" />
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Suitability" icon={LayoutGrid}>
          <div className="space-y-4">
            <div>
              <p className="mb-2 text-caption font-medium text-neutral-600">Recommended shelf</p>
              {lead.suitability.recommended_shelf.length === 0 ? (
                <p className="text-caption text-neutral-500">No products currently eligible for this shelf.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {lead.suitability.recommended_shelf.map((product) => (
                    <span
                      key={product}
                      className="rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-caption font-medium text-neutral-800"
                    >
                      {product}
                    </span>
                  ))}
                </div>
              )}
            </div>
            {lead.suitability.excluded.length > 0 && (
              <div>
                <p className="mb-2 text-caption font-medium text-neutral-600">Excluded</p>
                <div className="flex flex-wrap gap-2">
                  {lead.suitability.excluded.map((product) => (
                    <span
                      key={product}
                      className="rounded-full border border-neutral-200 bg-neutral-100 px-3 py-1 text-caption font-medium text-neutral-500 line-through"
                    >
                      {product}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <div>
              <p className="mb-2 text-caption font-medium text-neutral-600">Reasons</p>
              <ul className="list-inside list-disc space-y-1 text-body-sm text-neutral-700">
                {lead.suitability.reasons.map((reason) => (
                  <li key={reason}>{humanizeReason(reason)}</li>
                ))}
              </ul>
            </div>
          </div>
        </Panel>

        <Panel title="Priority score breakdown" icon={Scale} action={<PriorityChip score={lead.priority_score} />}>
          {(() => {
            const terms = priorityBreakdown(lead);
            const rawTotal = terms.reduce((sum, term) => sum + term.contribution, 0);
            const clamped = Math.trunc(rawTotal) !== lead.priority_score;
            return (
              <>
                <ul className="space-y-2">
                  {terms.map((term) => (
                    <li key={term.label} className="flex items-center justify-between gap-3 text-body-sm">
                      <div>
                        <span className="font-medium text-neutral-800">{term.label}</span>
                        <span className="ml-2 text-caption text-neutral-500">{term.detail}</span>
                      </div>
                      <span className="tabular-nums font-semibold text-neutral-900">+{term.contribution.toFixed(1)}</span>
                    </li>
                  ))}
                </ul>
                <div className="mt-3 flex items-center justify-between gap-3 border-t border-neutral-100 pt-3 text-body-sm">
                  <span className="font-medium text-neutral-800">
                    Raw total
                    {clamped && (
                      <span className="ml-2 text-caption font-normal text-neutral-500">
                        clamped to the 5–99 score band → {lead.priority_score}
                      </span>
                    )}
                  </span>
                  <span className="tabular-nums font-semibold text-neutral-900">{rawTotal.toFixed(1)}</span>
                </div>
              </>
            );
          })()}
        </Panel>
      </div>

      <CustomerDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        spaceId={spaceId}
        personaId={lead.customer.persona_id}
        customerName={lead.customer.name}
      />
    </div>
  );
}
