import { Check, ChevronDown, Globe } from "lucide-react";
import { DropdownMenu } from "radix-ui";
import { cn } from "@/lib/utils";
import { t, type LanguageCode } from "@/lib/i18n";

export interface LanguageDropdownProps {
  value: LanguageCode;
  onChange: (code: LanguageCode) => void;
  className?: string;
}

const LANGUAGES: { code: LanguageCode; nativeLabel: string }[] = [
  { code: "en", nativeLabel: "English" },
  { code: "hi", nativeLabel: "हिंदी" },
  { code: "gu", nativeLabel: "ગુજરાતી" },
];

/**
 * Compact globe-icon language switcher — replaces the EN/हिंदी/ગુજરાતી
 * segmented toggle in the chat header (product-owner feedback: the toggle
 * alone ate a full row). Picking a language flips every static UI string on
 * the surface instantly via `src/lib/i18n.ts` — no network round-trip.
 */
export function LanguageDropdown({ value, onChange, className }: LanguageDropdownProps) {
  const current = LANGUAGES.find((l) => l.code === value) ?? LANGUAGES[0];

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          aria-label={t(value, "header.tooltip.language")}
          className={cn(
            "flex h-9 min-w-11 shrink-0 items-center gap-1 rounded-full border border-neutral-200 bg-neutral-0 px-2.5 text-caption font-medium text-neutral-700 transition-colors duration-[var(--motion-micro)] ease-out hover:border-structural-300 hover:text-structural-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
            className
          )}
        >
          <Globe size={15} strokeWidth={1.75} aria-hidden="true" />
          <span>{current.nativeLabel}</span>
          <ChevronDown size={12} strokeWidth={2} aria-hidden="true" className="text-neutral-400" />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={6}
          className="z-50 min-w-40 overflow-hidden rounded-lg border border-neutral-200 bg-neutral-0 p-1 shadow-float-md"
        >
          {LANGUAGES.map((lang) => {
            const active = lang.code === value;
            return (
              <DropdownMenu.Item
                key={lang.code}
                onSelect={() => onChange(lang.code)}
                className={cn(
                  "flex min-h-11 cursor-pointer items-center justify-between gap-2 rounded-sm px-3 text-body-sm outline-none transition-colors duration-[var(--motion-micro)] ease-out",
                  active ? "bg-structural-50 text-structural-700 font-medium" : "text-neutral-700 hover:bg-neutral-50"
                )}
              >
                <span className="flex flex-col leading-tight">
                  <span>{lang.nativeLabel}</span>
                  <span className="text-caption text-neutral-500">
                    {t(value, `language.${lang.code}` as "language.en" | "language.hi" | "language.gu")}
                  </span>
                </span>
                {active && <Check size={16} strokeWidth={2} aria-hidden="true" />}
              </DropdownMenu.Item>
            );
          })}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
