import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { Nudge, NudgeKind } from "@/lib/types";

export type BadgeTone = "brand" | "structural" | "warning";

/**
 * The actual shape `GET /api/personas` returns (`app/api/spaces.py
 * list_personas`) — a flat roster card, not the nested `Persona` type in
 * `lib/types.ts`/`lib/queries.ts` (which wraps identity fields under
 * `.profile` for the full persona detail endpoint). Fetched separately
 * here, under its own query key, so this route never collides with
 * whatever cache shape other surfaces build on top of `usePersonas()`.
 */
export interface PersonaRosterEntry {
  id: string;
  name: string;
  age: number;
  city: string;
  segment: string;
  language: string;
  avatar: string;
  story: string;
}

export function usePersonaRoster(): UseQueryResult<PersonaRosterEntry[]> {
  return useQuery({
    queryKey: ["showcase", "persona-roster"],
    queryFn: () => apiGet<PersonaRosterEntry[]>("/personas"),
  });
}

export interface PersonaHint {
  /** The 2-liner shown on the persona card telling a judge what to try. */
  whatToTry: string;
  /** Optional small callout tag surfacing which golden path this persona demonstrates. */
  badge?: { label: string; tone: BadgeTone };
}

/**
 * Demo-curation copy layered on top of the API persona roster
 * (`GET /api/personas`). Not served by the backend — this is what a judge
 * should try with each persona, written once here so every surface that
 * lists personas (Command Center, Omni-channel) shares the same hints.
 */
export const PERSONA_HINTS: Record<string, PersonaHint> = {
  ravi: {
    whatToTry:
      "Ask about growing your salary surplus — watch a Nifty index SIP get recommended and auto-executed live.",
    badge: { label: "Start here · SIP auto-execute", tone: "brand" },
  },
  vikram: {
    whatToTry:
      "Tell the companion your EMIs feel heavy — see the distress-aware response that suppresses selling and offers refinance.",
    badge: { label: "Protective path · no selling", tone: "warning" },
  },
  meera: {
    whatToTry:
      "Ask about parking a business surplus in equity — watch it get triaged straight to your RM as a Lead Packet.",
    badge: { label: "Routes to your RM", tone: "structural" },
  },
  devika: {
    whatToTry:
      "Ask about PMS or structured products for a crore-plus portfolio — see the RM hand-off with full customer-360.",
    badge: { label: "Routes to your RM", tone: "structural" },
  },
  arjun: {
    whatToTry:
      "Ask how to grow an India-based corpus while living abroad — see NRI-aware guidance and remittance-linked context.",
  },
  shanta: {
    whatToTry:
      "Ask her companion, in Hindi, how to make a pension and FD last — see conservative, literacy-first guidance.",
  },
  priya: {
    whatToTry:
      "Ask about building a small emergency cushion from irregular gig income — see guidance with no linked investments yet.",
  },
};

export const LANGUAGE_LABELS: Record<string, string> = {
  en: "English",
  hi: "हिंदी",
  gu: "ગુજરાતી",
};

export function languageLabel(code: string): string {
  return LANGUAGE_LABELS[code] ?? code.toUpperCase();
}

/**
 * Fallback copy used on the Omni-channel showcase when
 * `GET /api/customer/{session_id}/nudges` hasn't landed yet or 404s —
 * always visibly labeled "Sample" (never mistaken for live AI copy).
 */
export function sampleNudges(personaName: string): Record<NudgeKind, Nudge> {
  const now = new Date().toISOString();
  return {
    functional: {
      id: "sample_functional",
      persona_id: "sample",
      kind: "functional",
      intent: "opportunity",
      title: "Idle balance, meet a better home",
      body: `${personaName}, ₹18,400 has sat idle in your savings account for 22 days. Moving it into a liquid fund could earn meaningfully more without locking it away.`,
      language: "en",
      source_metric_ids: [],
      created_at: now,
    },
    relational: {
      id: "sample_relational",
      persona_id: "sample",
      kind: "relational",
      intent: "celebration",
      title: "Three months of steady saving",
      body: `Nice run, ${personaName} — you've kept your monthly surplus positive for three months straight. That's the habit that compounds.`,
      language: "en",
      source_metric_ids: [],
      created_at: now,
    },
  };
}
