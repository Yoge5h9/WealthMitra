import { Languages, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";
import { languageLabel, PERSONA_HINTS, type PersonaRosterEntry } from "@/components/showcase/personas";

const BADGE_TONE_CLASSES: Record<string, string> = {
  brand: "border-brand-300 bg-brand-50 text-brand-700",
  structural: "border-structural-300 bg-structural-50 text-structural-700",
  warning: "border-warning-300 bg-warning-50 text-warning-700",
};

/** Deterministic initial-letter avatar chip — no per-persona photography, no emoji. */
function InitialsBadge({ name }: { name: string }) {
  const initials = name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-structural-500 font-display text-body font-semibold text-neutral-0">
      {initials}
    </span>
  );
}

export interface PersonaCardProps {
  persona: PersonaRosterEntry;
  selected?: boolean;
  onSelect: (personaId: string) => void;
  className?: string;
}

/** One persona in the switcher grid — identity, story, "what to try", and a golden-path hint. */
export function PersonaCard({ persona, selected, onSelect, className }: PersonaCardProps) {
  const hint = PERSONA_HINTS[persona.id];

  return (
    <button
      type="button"
      onClick={() => onSelect(persona.id)}
      aria-pressed={selected}
      className={cn(
        "group flex min-h-44 flex-col gap-3 rounded-lg border bg-neutral-0 p-4 text-left transition-colors duration-[var(--motion-micro)] ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
        selected
          ? "border-brand-400 ring-1 ring-brand-200"
          : "border-neutral-200 hover:border-structural-300",
        className
      )}
    >
      {hint?.badge && (
        <span
          className={cn(
            "inline-flex w-fit items-center rounded-xs border px-2 py-0.5 text-caption font-medium",
            BADGE_TONE_CLASSES[hint.badge.tone]
          )}
        >
          {hint.badge.label}
        </span>
      )}

      <div className="flex items-start gap-3">
        <InitialsBadge name={persona.name} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-body font-semibold text-neutral-900">{persona.name}</p>
          <p className="flex items-center gap-1 text-caption text-neutral-600">
            <span className="tabular-nums">{persona.age}</span>
            <span aria-hidden="true">&middot;</span>
            <MapPin size={12} strokeWidth={1.75} aria-hidden="true" />
            {persona.city}
          </p>
        </div>
        <span className="inline-flex shrink-0 items-center gap-1 rounded-xs border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-caption font-medium text-neutral-600">
          <Languages size={12} strokeWidth={1.75} aria-hidden="true" />
          {languageLabel(persona.language)}
        </span>
      </div>

      <p className="line-clamp-2 text-body-sm text-neutral-600">{persona.story}</p>

      {hint && (
        <p className="mt-auto border-t border-neutral-100 pt-2 text-caption text-structural-700">
          <span className="font-semibold">Try:</span> {hint.whatToTry}
        </p>
      )}
    </button>
  );
}
