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
import { t, type LanguageCode } from "@/lib/i18n";
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
  language: LanguageCode;
}

export function CustomerDashboard({ sessionId, spaceId, personaId, language }: CustomerDashboardProps) {
  const summary = useDashboardSummary(sessionId);

  return (
    <div className="space-y-5 px-4 py-4">
      <DataState
        status={summary.isLoading ? "loading" : summary.isError ? "error" : summary.data ? "success" : "empty"}
        onRetry={() => summary.refetch()}
        errorDescription={t(language, "dashboard.errorDesc")}
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
            <NetWorthHero value={summary.data.metrics.net_worth} language={language} />

            <SpendBreakdown
              spendByCategory={summary.data.metrics.spend_by_category}
              monthlyIncome={summary.data.metrics.monthly_income}
              monthlySurplus={summary.data.metrics.monthly_surplus}
              language={language}
            />

            <section className="rounded-lg border border-neutral-200 bg-neutral-0 p-4">
              <SectionHeader
                eyebrow={t(language, "dashboard.holdings.eyebrow")}
                title={t(language, "dashboard.holdings.title")}
                description={t(language, "dashboard.holdings.description")}
              />
              <div className="mt-3 flex items-center justify-between rounded-lg border border-neutral-200 p-3">
                <span className="text-body-sm text-neutral-700">{t(language, "dashboard.holdings.bankBalance")}</span>
                <MoneyText
                  value={summary.data.holdings.internal_bank_balance}
                  size="sm"
                  whyThisNumber={t(language, "header.tooltip.audit")}
                />
              </div>
              <div className="mt-3">
                <AaConnectFlow
                  sessionId={sessionId}
                  aaAvailableHint={personaAaAvailabilityHint(personaId)}
                  connected={summary.data.holdings.aa_connected}
                  holdings={summary.data.holdings.external}
                  liabilities={summary.data.holdings.external_liabilities}
                  language={language}
                />
              </div>
            </section>

            <section className="rounded-lg border border-neutral-200 bg-neutral-0 p-4">
              <SectionHeader eyebrow={t(language, "dashboard.goals.eyebrow")} title={t(language, "dashboard.goals.title")} />
              <div className="mt-3">
                <GoalsList goals={summary.data.goals} language={language} />
              </div>
            </section>

            <section className="rounded-lg border border-neutral-200 bg-neutral-0 p-4">
              <SectionHeader eyebrow={t(language, "dashboard.nudges.eyebrow")} title={t(language, "dashboard.nudges.title")} />
              <div className="mt-3">
                <NudgeFeed
                  sessionId={sessionId}
                  spaceId={spaceId}
                  personaId={personaId}
                  metrics={summary.data.metrics}
                  language={language}
                />
              </div>
            </section>

            <TrustFooter className="rounded-lg border-t-0" language={language} />
          </>
        )}
      </DataState>
    </div>
  );
}
