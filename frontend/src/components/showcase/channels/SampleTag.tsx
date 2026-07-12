import { FlaskConical } from "lucide-react";

/** Marks fallback copy so it's never mistaken for live AI-generated nudge text. */
export function SampleTag() {
  return (
    <span className="inline-flex items-center gap-1 rounded-xs border border-warning-300 bg-warning-50 px-1.5 py-0.5 text-caption font-medium text-warning-700">
      <FlaskConical size={11} strokeWidth={2} aria-hidden="true" />
      Sample
    </span>
  );
}
