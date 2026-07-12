/** Small label helpers scoped to the Dashboard surface — snake_case ids
 * (holding types, segment ids, risk bands) to short, human-readable labels.
 * Kept local rather than pulled from `components/rm/text.ts` since that
 * helper belongs to the RM surface, not shared. */

const KNOWN_LABELS: Record<string, string> = {
  FD: "Fixed deposit",
  NPS: "NPS",
  mutual_fund: "Mutual fund",
  equity: "Equity",
  insurance: "Insurance",
  gold: "Gold",
  personal_loan: "Personal loan",
  home_loan: "Home loan",
  auto_loan: "Auto loan",
  mass_retail_salaried: "Mass retail · salaried",
  mass_retail_gig: "Mass retail · gig",
  affluent: "Affluent",
  hni: "HNI",
  nri: "NRI",
  senior: "Senior",
};

export function humanize(id: string): string {
  const known = KNOWN_LABELS[id];
  if (known) return known;
  return id
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
