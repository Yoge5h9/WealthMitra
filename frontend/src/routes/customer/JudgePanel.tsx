/**
 * Standalone-only right side panel — the judge/evaluator control surface,
 * deliberately kept outside the phone. Owns the two demo affordances the
 * product owner moved out of the customer app: the audit trail (the
 * compliance spine — "why this number") and the jump to the RM Desk (the
 * chat -> regulated-lead handoff a judge follows). A real bank customer
 * never sees this panel; it never renders inside `/present`, which pins one
 * persona per iframe and shows the phone alone (see routes/customer/index.tsx).
 */
import { ArrowUpRight, ScrollText, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { t } from "@/lib/i18n";
import type { LanguageCode } from "@/components/shared/LangToggle";
import type { PersonaExperience } from "@/lib/personaExperience";
import { ResetDemoButton } from "@/components/showcase/ResetDemoButton";

export interface JudgePanelProps {
  spaceId: string | null;
  sessionId: string | null;
  hasLeads: boolean;
  leadCount: number;
  language: LanguageCode;
  experience: PersonaExperience;
  onOpenAudit: () => void;
  onReset: () => void;
}

export function JudgePanel({ spaceId, sessionId, hasLeads, leadCount, language, experience, onOpenAudit, onReset }: JudgePanelProps) {
  const auditReady = Boolean(sessionId);
  const rmHref = spaceId ? `/rm?space=${encodeURIComponent(spaceId)}` : "/rm";

  return (
    <div className="w-full shrink-0 rounded-2xl border border-brand-200 bg-neutral-0 p-4 shadow-float-md lg:w-72">
      <div className="mb-3 px-1">
        <p className="text-caption font-semibold uppercase tracking-wide text-brand-600">
          {t(language, "judgePanel.eyebrow")}
        </p>
        <h2 className="font-display text-h4 font-semibold text-neutral-900">{t(language, "judgePanel.heading")}</h2>
      </div>

      <div className="space-y-3">
        <section className="rounded-lg border border-structural-200 bg-structural-50 p-3" aria-label="Persona adaptation shown to judges">
          <div className="flex items-center gap-2 text-structural-700">
            <Sparkles size={16} strokeWidth={1.75} aria-hidden="true" />
            <p className="text-caption font-semibold uppercase tracking-wide">Persona adaptation</p>
          </div>
          <dl className="mt-2 space-y-2 text-caption">
            <div><dt className="font-semibold text-neutral-700">Chat</dt><dd className="text-neutral-600">{experience.chat.label}</dd></div>
            <div><dt className="font-semibold text-neutral-700">Dashboard</dt><dd className="text-neutral-600">{experience.dashboard.title}</dd></div>
            <div><dt className="font-semibold text-neutral-700">Channels</dt><dd className="text-neutral-600">{experience.channels.preference} · {experience.channels.cadence}</dd></div>
          </dl>
          <p className="mt-2 text-caption text-neutral-500">Judge view only — the phone shows the adapted experience, not an explanation of it.</p>
        </section>

        {/* Audit trail — same drawer the old in-phone icon opened; the
            entry point moves, the compliance content doesn't. */}
        <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
          <button
            type="button"
            onClick={onOpenAudit}
            disabled={!auditReady}
            aria-label={t(language, "judgePanel.auditButton")}
            className={cn(
              "flex min-h-11 w-full items-center gap-2 rounded-md px-2.5 text-left text-body-sm font-semibold transition-colors duration-[var(--motion-micro)] ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
              auditReady
                ? "bg-structural-600 text-neutral-0 hover:bg-structural-700"
                : "cursor-not-allowed bg-neutral-200 text-neutral-400"
            )}
          >
            <ScrollText size={17} strokeWidth={1.75} aria-hidden="true" />
            {t(language, "judgePanel.auditButton")}
          </button>
          <p className="mt-2 text-caption text-neutral-600">
            {auditReady ? t(language, "judgePanel.auditDesc") : t(language, "judgePanel.auditWaiting")}
          </p>
        </div>

        {/* RM desk jump — opens a new tab so the judge can watch the Lead
            Packet land while the chat session in this tab stays alive. */}
        <div
          className={cn(
            "rounded-lg border p-3",
            hasLeads ? "border-brand-300 bg-brand-50" : "border-neutral-200 bg-neutral-50"
          )}
        >
          <a
            href={rmHref}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={
              hasLeads
                ? `${t(language, "judgePanel.rmButton")} — ${t(language, "judgePanel.leadCount", { count: leadCount })}`
                : t(language, "judgePanel.rmButton")
            }
            className={cn(
              "flex min-h-11 w-full items-center justify-between gap-2 rounded-md px-2.5 text-body-sm font-semibold transition-colors duration-[var(--motion-micro)] ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
              hasLeads
                ? "bg-brand-600 text-neutral-0 hover:bg-brand-700"
                : "bg-structural-50 text-structural-700 hover:bg-structural-100"
            )}
          >
            <span className="flex items-center gap-2">
              {hasLeads && (
                <span className="relative flex size-2.5 shrink-0" aria-hidden="true">
                  <span className="absolute inline-flex size-full animate-ping rounded-full bg-neutral-0 opacity-75" />
                  <span className="relative inline-flex size-2.5 rounded-full bg-neutral-0" />
                </span>
              )}
              {t(language, "judgePanel.rmButton")}
            </span>
            <span className="flex items-center gap-1.5">
              {hasLeads && (
                <span
                  aria-hidden="true"
                  className="rounded-full bg-neutral-0/25 px-2 py-0.5 text-caption font-bold tabular-nums"
                >
                  {leadCount}
                </span>
              )}
              <ArrowUpRight size={16} strokeWidth={2} aria-hidden="true" />
            </span>
          </a>
          <p className="mt-2 text-caption text-neutral-600">
            {hasLeads ? t(language, "judgePanel.rmDescActive") : t(language, "judgePanel.rmDescCalm")}
          </p>
        </div>

        <div className="border-t border-neutral-100 pt-3">
          <p className="mb-2 text-caption text-neutral-600">Reset every demo conversation and start this phone from a fresh seeded session.</p>
          <ResetDemoButton spaceId={spaceId} onReset={onReset} />
        </div>
      </div>

      <p className="mt-3 border-t border-neutral-100 px-1 pt-3 text-caption text-neutral-400">
        {t(language, "judgePanel.note")}
      </p>
    </div>
  );
}
