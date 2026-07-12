/**
 * Small label/formatting helpers local to the RM console — snake_case
 * segment/city-tier strings and language codes arrive straight from the
 * backend (`LeadCustomer`) with no display-label mapping of
 * their own, so this is where they get humanized once for the whole surface.
 */
import type { LeadFamily } from "@/lib/types";

export function humanize(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export const FAMILY_LABEL: Record<LeadFamily, string> = {
  investment_insurance: "Investments & Insurance",
  loans_cards: "Loans & Cards",
};

/** Short form for space-constrained spots (toasts, list rows). */
export const FAMILY_SHORT_LABEL: Record<LeadFamily, string> = {
  investment_insurance: "Investment",
  loans_cards: "Loan",
};

export const LOANS_TAGLINE = "Interest saved is wealth created";

const LANGUAGE_LABEL: Record<string, string> = {
  en: "English",
  hi: "हिंदी",
  gu: "ગુજરાતી",
};

export function languageLabel(code: string): string {
  return LANGUAGE_LABEL[code] ?? humanize(code);
}
