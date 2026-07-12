/**
 * Standalone-only left side panel (Fix 2) for toggling between demo
 * customers from beside the phone, rather than from a blocking in-phone
 * sheet. Never rendered inside `/present` — that stage pins one persona per
 * iframe via `?persona=`.
 */
import { MapPin } from "lucide-react";
import { cn } from "@/lib/utils";
import { t } from "@/lib/i18n";
import type { LanguageCode } from "@/components/shared/LangToggle";
import type { PersonaRosterItem } from "./types";

export interface PersonaSwitcherProps {
  roster: PersonaRosterItem[] | undefined;
  activePersonaId: string | null;
  language: LanguageCode;
  onPick: (personaId: string, language: LanguageCode) => void;
}

const LANGUAGE_LABEL: Record<string, string> = { en: "English", hi: "हिंदी", gu: "ગુજરાતી" };

function asLanguage(value: string): LanguageCode {
  return value === "hi" || value === "gu" ? value : "en";
}

export function PersonaSwitcher({ roster, activePersonaId, language, onPick }: PersonaSwitcherProps) {
  if (!roster || roster.length === 0) return null;

  return (
    <div
      className="w-full shrink-0 rounded-2xl border border-neutral-200 bg-neutral-0 p-4 shadow-float-md lg:w-72"
      aria-label={t(language, "personaSwitcher.heading")}
    >
      <div className="mb-3 px-1">
        <h2 className="font-display text-h4 font-semibold text-neutral-900">{t(language, "personaSwitcher.heading")}</h2>
        <p className="text-caption text-neutral-500">{t(language, "personaSwitcher.subheading")}</p>
      </div>

      <ul className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0">
        {roster.map((persona) => {
          const isActive = persona.id === activePersonaId;
          return (
            <li key={persona.id} className="shrink-0 lg:shrink">
              <button
                type="button"
                onClick={() => onPick(persona.id, asLanguage(persona.language))}
                aria-current={isActive ? "true" : undefined}
                aria-label={isActive ? `${persona.name} — ${t(language, "personaSwitcher.active")}` : persona.name}
                className={cn(
                  "flex min-h-11 w-full min-w-[11.5rem] items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors duration-[var(--motion-micro)] ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] lg:min-w-0",
                  isActive
                    ? "border-structural-500 bg-structural-50"
                    : "border-neutral-200 bg-neutral-0 hover:border-structural-300 hover:bg-structural-50"
                )}
              >
                <span
                  className={cn(
                    "flex size-9 shrink-0 items-center justify-center rounded-full font-display text-body-sm font-semibold",
                    isActive ? "bg-structural-600 text-neutral-0" : "bg-structural-100 text-structural-700"
                  )}
                >
                  {persona.name.charAt(0)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-body-sm font-semibold text-neutral-900">{persona.name}</span>
                  <span className="flex items-center gap-1 truncate text-caption text-neutral-500">
                    <MapPin size={11} strokeWidth={1.75} aria-hidden="true" />
                    {persona.city} · {persona.age}y · {LANGUAGE_LABEL[persona.language] ?? persona.language}
                  </span>
                </span>
                {isActive && <span className="size-2 shrink-0 rounded-full bg-brand-500" aria-hidden="true" />}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
