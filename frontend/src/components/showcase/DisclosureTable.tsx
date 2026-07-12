import { CheckCircle2, Database, Clapperboard, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { SectionHeader } from "@/components/shared/SectionHeader";

type DisclosureTone = "real" | "pre-seeded" | "simulated";

interface DisclosureRow {
  layer: string;
  status: string;
  tone: DisclosureTone;
  note: string;
}

// The honest REAL / PRE-SEEDED / SIMULATED line every judge sees before they
// touch the demo.
const ROWS: DisclosureRow[] = [
  {
    layer: "Chat answers",
    status: "REAL",
    tone: "real",
    note: "Live LLM tool-use calls, grounded in tools — type anything, get a real grounded reply.",
  },
  {
    layer: "All figures — spend, cash-flow, net-worth, risk, suitability segment",
    status: "REAL, deterministic",
    tone: "real",
    note: "The “compute the numbers” compliance spine — never an LLM guess.",
  },
  {
    layer: "Routing — vanilla-auto vs. RM-lead vs. distress-suppress",
    status: "REAL, deterministic",
    tone: "real",
    note: "The money-shot — 100% testable, no LLM in the decision.",
  },
  {
    layer: "Suitability Matrix product filtering",
    status: "REAL, deterministic (config-driven)",
    tone: "real",
    note: "The governance and scalability story — a config table, not hardcoded logic.",
  },
  {
    layer: "3-surface live sync — chat → RM queue → nudge",
    status: "REAL (realtime channel)",
    tone: "real",
    note: "The “wow” — watch the RM desk light up as the customer types.",
  },
  {
    layer: "Nudge copy, RM lead narrative, multilingual replies",
    status: "REAL (LLM)",
    tone: "real",
    note: "Words are AI-generated; the numbers behind them never are.",
  },
  {
    layer: "Data ingestion — bank + Account Aggregator",
    status: "PRE-SEEDED synthetic",
    tone: "pre-seeded",
    note: "Can't wire live bank APIs before the sandbox stage — disclosed, never hidden.",
  },
  {
    layer: "Omni-channel delivery — voice, SMS, WhatsApp-style, push",
    status: "SIMULATED playback",
    tone: "simulated",
    note: "Real AI-generated copy, played back — telephony/messaging infra is out of scope.",
  },
  {
    layer: "Vanilla auto-execute",
    status: "SIMULATED confirmation + receipt",
    tone: "simulated",
    note: "No real money movement.",
  },
];

const TONE_CONFIG: Record<DisclosureTone, { icon: LucideIcon; classes: string }> = {
  real: { icon: CheckCircle2, classes: "border-success-300 bg-success-50 text-success-700" },
  "pre-seeded": { icon: Database, classes: "border-structural-300 bg-structural-50 text-structural-700" },
  simulated: { icon: Clapperboard, classes: "border-warning-300 bg-warning-50 text-warning-700" },
};

export interface DisclosureTableProps {
  className?: string;
}

/**
 * The honest REAL / PRE-SEEDED / SIMULATED line, rendered as a first-class
 * trust artifact rather than a footnote — this is the demo's compliance
 * story, and judges score regulatory maturity as much as the AI itself.
 */
export function DisclosureTable({ className }: DisclosureTableProps) {
  return (
    <section className={cn("space-y-4", className)}>
      <SectionHeader
        eyebrow="Read this before you judge it"
        title="What's real, what's seeded, what's staged"
        description="Every layer of this demo is labeled honestly. Nothing here is dressed up to look more finished than it is."
      />

      <div className="overflow-hidden rounded-lg border border-neutral-200">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-neutral-200 bg-neutral-50">
              <th scope="col" className="px-4 py-3 text-caption font-semibold uppercase tracking-wide text-neutral-600">
                Layer
              </th>
              <th scope="col" className="px-4 py-3 text-caption font-semibold uppercase tracking-wide text-neutral-600">
                Status
              </th>
              <th scope="col" className="hidden px-4 py-3 text-caption font-semibold uppercase tracking-wide text-neutral-600 sm:table-cell">
                Note
              </th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row, index) => {
              const tone = TONE_CONFIG[row.tone];
              const Icon = tone.icon;
              return (
                <tr
                  key={row.layer}
                  className={cn(
                    "align-top",
                    index !== ROWS.length - 1 && "border-b border-neutral-100"
                  )}
                >
                  <td className="px-4 py-3 text-body-sm font-medium text-neutral-900">{row.layer}</td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-xs border px-2 py-0.5 text-caption font-semibold",
                        tone.classes
                      )}
                    >
                      <Icon size={12} strokeWidth={2} aria-hidden="true" />
                      {row.status}
                    </span>
                    <p className="mt-1 text-caption text-neutral-600 sm:hidden">{row.note}</p>
                  </td>
                  <td className="hidden px-4 py-3 text-body-sm text-neutral-600 sm:table-cell">{row.note}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
