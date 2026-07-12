import { cn } from "@/lib/utils";

export interface ChipRowProps {
  chips: string[];
  onPick: (text: string) => void;
  disabled?: boolean;
  className?: string;
}

/** Persona-aware, localized suggested prompts shown above the input bar. */
export function ChipRow({ chips, onPick, disabled, className }: ChipRowProps) {
  if (chips.length === 0) return null;
  return (
    <div className={cn("flex gap-2 overflow-x-auto px-4 pt-3", className)}>
      {chips.map((chip) => (
        <button
          key={chip}
          type="button"
          disabled={disabled}
          onClick={() => onPick(chip)}
          className="min-h-11 shrink-0 whitespace-nowrap rounded-sm border border-structural-200 bg-structural-50 px-3 text-body-sm font-medium text-structural-700 transition-colors duration-[var(--motion-micro)] ease-out hover:bg-structural-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {chip}
        </button>
      ))}
    </div>
  );
}
