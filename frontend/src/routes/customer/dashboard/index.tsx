/**
 * The customer Dashboard tab (`/app` — Task 16): net-worth hero, spend &
 * cash-flow breakdown, holdings + AA connect, goals, and a live nudge feed.
 * Every rupee figure on this screen comes straight off
 * `GET /customer/{session_id}/summary` — nothing here is computed or
 * invented client-side.
 */
import { DataState } from "@/components/shared/DataState";
import { MoneyText } from "@/components/shared/MoneyText";
import { TrustFooter } from "@/components/shared/TrustFooter";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { NetWorthHero } from "./NetWorthHero";
import { SpendBreakdown } from "./SpendBreakdown";
import { AaConnectFlow } from "./AaConnectFlow";
import { GoalsList } from "./GoalsList";
import { NudgeFeed } from "./NudgeFeed";
import { personaAaAvailabilityHint } from "./personaAaAvailability";
import { useDashboardSummary } from "./useDashboardData";

export interface CustomerDashboardProps {
  sessionId: string;
  spaceId: string | null;
  personaId: string;
}

export function CustomerDashboard({ sessionId, spaceId, personaId }: CustomerDashboardProps) {
  const summary = useDashboardSummary(sessionId);

  return (
    <div className="space-y-5 px-4 py-4">
      <DataState
        status={summary.isLoading ? "loading" : summary.isError ? "error" : summary.data ? "success" : "empty"}
        onRetry={() => summary.refetch()}
        errorDescription="Couldn't load your dashboard right now. Your data is safe — try again."
        skeleton={
          <div className="animate-pulse space-y-4" aria-hidden="true">
            <div className="h-40 rounded-xl bg-neutral-200" />
            <div className="h-56 rounded-lg bg-neutral-100" />
            <div className="h-40 rounded-lg bg-neutral-100" />
          </div>
        }
      >
        {summary.data && (
          <>
            <NetWorthHero value={summary.data.metrics.net_worth} />

            <SpendBreakdown
              spendByCategory={summary.data.metrics.spend_by_category}
              monthlyIncome={summary.data.metrics.monthly_income}
              monthlySurplus={summary.data.metrics.monthly_surplus}
            />

            <section className="rounded-lg border border-neutral-200 bg-neutral-0 p-4">
              <SectionHeader
                eyebrow="Holdings"
                title="Your accounts"
                description="Bank balance plus anything you've linked from outside IDBI."
              />
              <div className="mt-3 flex items-center justify-between rounded-lg border border-neutral-200 p-3">
                <span className="text-body-sm text-neutral-700">Bank balance (IDBI)</span>
                <MoneyText
                  value={summary.data.holdings.internal_bank_balance}
                  size="sm"
                  whyThisNumber="idle_balance_v1 · net of credits minus debits across your bank transaction ledger"
                />
              </div>
              <div className="mt-3">
                <AaConnectFlow
                  sessionId={sessionId}
                  aaAvailableHint={personaAaAvailabilityHint(personaId)}
                  connected={summary.data.holdings.aa_connected}
                  holdings={summary.data.holdings.external}
                  liabilities={summary.data.holdings.external_liabilities}
                />
              </div>
            </section>

            <section className="rounded-lg border border-neutral-200 bg-neutral-0 p-4">
              <SectionHeader eyebrow="Goals" title="What you're saving for" />
              <div className="mt-3">
                <GoalsList goals={summary.data.goals} />
              </div>
            </section>

            <section className="rounded-lg border border-neutral-200 bg-neutral-0 p-4">
              <SectionHeader eyebrow="For you" title="Nudges" />
              <div className="mt-3">
                <NudgeFeed sessionId={sessionId} spaceId={spaceId} personaId={personaId} />
              </div>
            </section>

            <TrustFooter className="rounded-lg border-t-0" />
          </>
        )}
      </DataState>
    </div>
  );
}
