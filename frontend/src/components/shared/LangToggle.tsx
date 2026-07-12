import { cn } from "@/lib/utils";

export type LanguageCode = "en" | "hi" | "gu";

interface LanguageOption {
  code: LanguageCode;
  label: string;
}

const LANGUAGES: LanguageOption[] = [
  { code: "en", label: "EN" },
  { code: "hi", label: "हिंदी" },
  { code: "gu", label: "ગુજરાતી" },
];

export interface LangToggleProps {
  value: LanguageCode;
  onChange: (code: LanguageCode) => void;
  className?: string;
}

/** EN / हिंदी / ગુજરાતી segmented toggle — linguistic democratization (CLAUDE.md §5) starts here. */
export function LangToggle({ value, onChange, className }: LangToggleProps) {
  return (
    <div
      role="radiogroup"
      aria-label="Language"
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-neutral-200 bg-neutral-50 p-1",
        className
      )}
    >
      {LANGUAGES.map((lang) => {
        const isActive = lang.code === value;
        return (
          <button
            key={lang.code}
            type="button"
            role="radio"
            aria-checked={isActive}
            onClick={() => onChange(lang.code)}
            className={cn(
              "min-h-11 min-w-11 rounded-full px-3 text-caption font-medium transition-colors duration-[var(--motion-micro)] ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
              isActive ? "bg-brand-500 text-neutral-950" : "text-neutral-600 hover:text-neutral-900"
            )}
          >
            {lang.label}
          </button>
        );
      })}
    </div>
  );
}
