/**
 * Fallback nudges shown the instant the dashboard opens, before/absent any
 * fetched or live `nudge.created` event — the panel must never render empty
 * for a judge (product-owner feedback). Amounts come straight from the
 * already-fetched `DashboardMetrics` (idle balance, monthly surplus) — never
 * an invented figure — and the second slot is a qualitative, segment-aware
 * literacy/behavioural cue with no fabricated number.
 */
import { formatINR } from "@/lib/format";
import { t, type LanguageCode } from "@/lib/i18n";
import type { Nudge } from "@/lib/types";
import type { DashboardMetrics } from "./types";

function seedNudge(
  id: string,
  personaId: string,
  intent: Nudge["intent"],
  title: string,
  body: string
): Nudge {
  return {
    id,
    persona_id: personaId,
    kind: "functional",
    intent,
    title,
    body,
    language: "en",
    source_metric_ids: [],
    created_at: new Date().toISOString(),
  };
}

const SEGMENT_SECONDARY: Record<string, "sip" | "tax" | "literacy"> = {
  mass_retail_salaried: "sip",
  mass_retail_gig: "literacy",
  senior: "tax",
  affluent: "tax",
  hni: "tax",
  nri: "tax",
};

/** Builds 1–2 persona-consistent nudges from real dashboard metrics. Never
 * invents a number: idle-balance/surplus amounts are the actual fetched
 * values; everything else is a qualitative, non-numeric cue. */
export function buildDefaultNudges(
  personaId: string,
  metrics: DashboardMetrics,
  language: LanguageCode
): Nudge[] {
  const nudges: Nudge[] = [];

  if (metrics.idle_balance > 1000) {
    const amount = formatINR(metrics.idle_balance, { compact: true });
    nudges.push(
      seedNudge(
        `seed_idle_${personaId}`,
        personaId,
        "opportunity",
        t(language, "nudge.idle.title", { amount }),
        t(language, "nudge.idle.body")
      )
    );
  } else if (metrics.monthly_surplus > 1000) {
    const amount = formatINR(metrics.monthly_surplus, { compact: true });
    nudges.push(
      seedNudge(
        `seed_surplus_${personaId}`,
        personaId,
        "opportunity",
        t(language, "nudge.surplus.title", { amount }),
        t(language, "nudge.surplus.body")
      )
    );
  }

  const secondary = SEGMENT_SECONDARY[metrics.segment] ?? "literacy";
  if (secondary === "sip") {
    nudges.push(
      seedNudge(`seed_sip_${personaId}`, personaId, "motivational", t(language, "nudge.sip.title"), t(language, "nudge.sip.body"))
    );
  } else if (secondary === "tax") {
    nudges.push(
      seedNudge(`seed_tax_${personaId}`, personaId, "opportunity", t(language, "nudge.tax.title"), t(language, "nudge.tax.body"))
    );
  } else {
    nudges.push(
      seedNudge(
        `seed_literacy_${personaId}`,
        personaId,
        "literacy",
        t(language, "nudge.literacy.title"),
        t(language, "nudge.literacy.body")
      )
    );
  }

  return nudges.slice(0, 2);
}
