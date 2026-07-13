/**
 * Whether a persona has any Account Aggregator-linkable external accounts at
 * all — as opposed to having accounts but not yet connecting them.
 *
 * There is no customer-facing GET endpoint that exposes this: `GET
 * /customer/{session_id}/summary` only returns `holdings.aa_connected`
 * (connected or not), never `aa_available`, and `GET /personas` doesn't
 * expose the persona's `external` block either (confirmed by reading both
 * handlers). The one place `aa_available` really does come back from the
 * server is `POST /aa/consent`'s response — but firing that as a blind probe
 * for an AA-available persona (e.g. ravi) writes a spurious "declined
 * transfer consent" audit entry for an action the user never took, which is
 * exactly the kind of black-box-looking trace the audit trail exists to
 * prevent. `app/api/aa.py::aa_consent` *does* return early with zero side
 * effects when `aa_available` is false (before any audit/state write), so a
 * probe is only actually safe for the "no accounts" case — the one case
 * this table can't get wrong without also being self-correcting below.
 *
 * So: this is a best-effort seed derived from the real, fixed synthetic
 * persona set (`data/synthetic/*.json`, verified directly) for the initial
 * render, and every consuming call site treats the *first* real
 * `POST /aa/consent` response as authoritative and self-corrects if it ever
 * disagrees. Not a financial figure — a static roster capability flag for a
 * closed, known set of demo personas — so this isn't the "never invent a
 * number" compliance line, just a stopgap for a known API gap.
 */
const KNOWN_AA_AVAILABILITY: Record<string, boolean> = {
  ravi: true,
  priya: false,
  meera: true,
  arjun: true,
  devika: true,
  vikram: true,
  shanta: true,
  new_to_idbi: true,
};

export function personaAaAvailabilityHint(personaId: string): boolean {
  return KNOWN_AA_AVAILABILITY[personaId] ?? true;
}
