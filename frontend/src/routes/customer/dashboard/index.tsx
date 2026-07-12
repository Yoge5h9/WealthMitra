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
import { personaExperienceFor, type PersonaExperience } from "@/lib/personaExperience";

export interface CustomerDashboardProps {
  sessionId: string;
  spaceId: string | null;
  personaId: string;
  language: LanguageCode;
  experience?: PersonaExperience;
}

export function CustomerDashboard({ sessionId, spaceId, personaId, language, experience: suppliedExperience }: CustomerDashboardProps) {
  const isNewCustomer = personaId === "new_to_idbi";
  const summary = useDashboardSummary(isNewCustomer ? null : sessionId);
  const experience = suppliedExperience ?? personaExperienceFor(personaId);

  if (isNewCustomer) {
    return (
      <div className="space-y-5 px-4 py-4">
        <section className="rounded-lg border border-structural-200 bg-structural-50 p-5">
          <SectionHeader eyebrow="Your WealthMitra" title="Your dashboard grows with you" description="Finish the four quick questions in Chat, then choose whether to connect external accounts through Account Aggregator. We never invent a balance, holding or recommendation before you share data." />
        </section>
        <TrustFooter className="rounded-lg border-t-0" language={language} />
      </div>
    );
  }

  function cashflowSection() {
    return (
      <SpendBreakdown
        spendByCategory={summary.data!.metrics.spend_by_category}
        monthlyIncome={summary.data!.metrics.monthly_income}
        monthlySurplus={summary.data!.metrics.monthly_surplus}
        language={language}
      />
    );
  }

  function holdingsSection() {
    return (
      <section className="rounded-lg border border-neutral-200 bg-neutral-0 p-4">
        <SectionHeader eyebrow={t(language, "dashboard.holdings.eyebrow")} title={t(language, "dashboard.holdings.title")} description={t(language, "dashboard.holdings.description")} />
        <div className="mt-3 flex items-center justify-between rounded-lg border border-neutral-200 p-3">
          <span className="text-body-sm text-neutral-700">{t(language, "dashboard.holdings.bankBalance")}</span>
          <MoneyText value={summary.data!.holdings.internal_bank_balance} size="sm" whyThisNumber={t(language, "header.tooltip.audit")} />
        </div>
        <div className="mt-3"><AaConnectFlow sessionId={sessionId} aaAvailableHint={personaAaAvailabilityHint(personaId)} connected={summary.data!.holdings.aa_connected} holdings={summary.data!.holdings.external} liabilities={summary.data!.holdings.external_liabilities} language={language} /></div>
      </section>
    );
  }

  function goalsSection() {
    return (
      <section className="rounded-lg border border-neutral-200 bg-neutral-0 p-4">
        <SectionHeader eyebrow={t(language, "dashboard.goals.eyebrow")} title={t(language, "dashboard.goals.title")} />
        <div className="mt-3"><GoalsList goals={summary.data!.goals} language={language} /></div>
      </section>
    );
  }

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
            <section className={`rounded-lg border p-4 ${experience.dashboard.accentClass}`}>
              <p className="text-caption font-semibold uppercase tracking-wide">Your dashboard focus</p>
              <h2 className="mt-1 font-display text-h4 font-semibold">{experience.dashboard.title}</h2>
              <p className="mt-1 text-body-sm">{experience.dashboard.description}</p>
            </section>
            <NetWorthHero value={summary.data.metrics.net_worth} language={language} />

            {experience.dashboard.primary === "cashflow" && cashflowSection()}
            {experience.dashboard.primary === "holdings" && holdingsSection()}
            {experience.dashboard.primary === "goals" && goalsSection()}
            {experience.dashboard.primary !== "cashflow" && cashflowSection()}
            {experience.dashboard.primary !== "holdings" && holdingsSection()}
            {experience.dashboard.primary !== "goals" && goalsSection()}

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
