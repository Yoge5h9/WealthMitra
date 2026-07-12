import { Dialog } from "radix-ui";
import { MapPin, Users, X } from "lucide-react";
import { DataState } from "@/components/shared/DataState";
import type { LanguageCode } from "@/components/shared/LangToggle";
import { t } from "@/lib/i18n";
import type { PersonaRosterItem } from "./types";

export interface PersonaPickerProps {
  open: boolean;
  loading: boolean;
  error: boolean;
  roster: PersonaRosterItem[] | undefined;
  onRetry: () => void;
  onPick: (personaId: string, language: LanguageCode) => void;
  /** "initial" (default): the blocking first-run sheet — no escape, no
   * dismiss. "switch": a voluntary, dismissible sheet for changing persona
   * mid-conversation (requirement 7 — never re-forces the blocking screen
   * once a persona is already active). */
  mode?: "initial" | "switch";
  onDismiss?: () => void;
  /** Current language, used only to translate this sheet's own chrome —
   * the roster's persona names/segments stay as seeded data. */
  language?: LanguageCode;
}

const LANGUAGE_LABEL: Record<string, string> = { en: "English", hi: "हिंदी", gu: "ગુજરાતી" };

function asLanguage(value: string): LanguageCode {
  return value === "hi" || value === "gu" ? value : "en";
}

/** Persona-selection sheet: blocking on first run (no `?persona=` yet),
 * voluntarily dismissible when reopened later to switch customers. Every
 * demo persona is a real seeded synthetic profile, never a "Sample User"
 * placeholder. */
export function PersonaPicker({
  open,
  loading,
  error,
  roster,
  onRetry,
  onPick,
  mode = "initial",
  onDismiss,
  language = "en",
}: PersonaPickerProps) {
  const dismissible = mode === "switch";
  return (
    <Dialog.Root open={open} onOpenChange={(next) => !next && dismissible && onDismiss?.()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-neutral-950/40" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-[min(92vw,420px)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-neutral-200 bg-neutral-0 shadow-float-xl"
          onEscapeKeyDown={(e) => !dismissible && e.preventDefault()}
          onPointerDownOutside={(e) => !dismissible && e.preventDefault()}
          aria-describedby={undefined}
        >
          <div className="flex items-start justify-between gap-3 border-b border-neutral-200 px-6 py-5">
            <div>
              <Dialog.Title className="font-display text-h3 font-semibold text-neutral-900">
                {t(language, dismissible ? "persona.switchTitle" : "persona.pickTitle")}
              </Dialog.Title>
              <p className="mt-1 text-body-sm text-neutral-600">
                {t(language, dismissible ? "persona.switchSubtitle" : "persona.pickSubtitle")}
              </p>
            </div>
            {dismissible && (
              <Dialog.Close asChild>
                <button
                  type="button"
                  aria-label={t(language, "persona.close")}
                  className="flex size-11 shrink-0 items-center justify-center rounded-full text-neutral-500 hover:text-neutral-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
                >
                  <X size={20} strokeWidth={1.75} />
                </button>
              </Dialog.Close>
            )}
          </div>

          <div className="p-4">
            <DataState
              status={loading ? "loading" : error ? "error" : (roster?.length ?? 0) === 0 ? "empty" : "success"}
              emptyIcon={Users}
              emptyTitle={t(language, "persona.empty")}
              emptyDescription={t(language, "persona.emptyDesc")}
              errorDescription={t(language, "persona.errorDesc")}
              onRetry={onRetry}
            >
              <ul className="space-y-2">
                {roster?.map((persona) => (
                  <li key={persona.id}>
                    <button
                      type="button"
                      onClick={() => onPick(persona.id, asLanguage(persona.language))}
                      className="flex min-h-11 w-full items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 text-left transition-colors duration-[var(--motion-micro)] ease-out hover:border-structural-300 hover:bg-structural-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
                    >
                      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-structural-100 font-display text-h4 font-semibold text-structural-700">
                        {persona.name.charAt(0)}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-body-sm font-semibold text-neutral-900">{persona.name}</span>
                        <span className="flex items-center gap-1 truncate text-caption text-neutral-500">
                          <MapPin size={12} strokeWidth={1.75} aria-hidden="true" />
                          {persona.city} · {persona.age}y · {LANGUAGE_LABEL[persona.language] ?? persona.language}
                        </span>
                      </span>
                      <span className="shrink-0 rounded-full bg-neutral-100 px-2 py-1 text-caption font-medium capitalize text-neutral-600">
                        {persona.segment.replace(/_/g, " ")}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </DataState>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
