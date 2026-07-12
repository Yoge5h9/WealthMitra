import { Dialog } from "radix-ui";
import { MapPin, Users } from "lucide-react";
import { DataState } from "@/components/shared/DataState";
import type { LanguageCode } from "@/components/shared/LangToggle";
import type { PersonaRosterItem } from "./types";

export interface PersonaPickerProps {
  open: boolean;
  loading: boolean;
  error: boolean;
  roster: PersonaRosterItem[] | undefined;
  onRetry: () => void;
  onPick: (personaId: string, language: LanguageCode) => void;
}

const LANGUAGE_LABEL: Record<string, string> = { en: "English", hi: "हिंदी", gu: "ગુજરાતી" };

function asLanguage(value: string): LanguageCode {
  return value === "hi" || value === "gu" ? value : "en";
}

/** Blocking persona-selection sheet shown when the surface wasn't opened
 * with `?persona=` — every demo persona is a real seeded synthetic profile,
 * never a "Sample User" placeholder. */
export function PersonaPicker({ open, loading, error, roster, onRetry, onPick }: PersonaPickerProps) {
  return (
    <Dialog.Root open={open}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-neutral-950/40" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-[min(92vw,420px)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-neutral-200 bg-neutral-0 shadow-float-xl"
          onEscapeKeyDown={(e) => e.preventDefault()}
          onPointerDownOutside={(e) => e.preventDefault()}
          aria-describedby={undefined}
        >
          <div className="border-b border-neutral-200 px-6 py-5">
            <Dialog.Title className="font-display text-h3 font-semibold text-neutral-900">
              Who's chatting today?
            </Dialog.Title>
            <p className="mt-1 text-body-sm text-neutral-600">
              Pick a demo customer to start a WealthMitra conversation as them.
            </p>
          </div>

          <div className="p-4">
            <DataState
              status={loading ? "loading" : error ? "error" : (roster?.length ?? 0) === 0 ? "empty" : "success"}
              emptyIcon={Users}
              emptyTitle="No demo customers available"
              emptyDescription="The persona roster couldn't be found for this session."
              errorDescription="Couldn't load the customer roster. Try again."
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
