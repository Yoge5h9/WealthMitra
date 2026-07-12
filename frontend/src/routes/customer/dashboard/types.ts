/**
 * Local, verified types for the Dashboard surface's two backend contracts —
 * `GET /customer/{session_id}/summary` (`app/api/customer.py::_summary`) and
 * `POST /aa/consent` (`app/api/aa.py::aa_consent`).
 *
 * `lib/types.ts` declares a `CustomerSummary` (flat `net_worth`/`monthly_surplus`/
 * etc. as top-level `Metric` objects, each with `value`/`unit`/`as_of`/`method`)
 * and an `AaState` (`session_id` + two grant flags + `connected`, no
 * `aa_available`/`holdings`) that do NOT match what these two endpoints
 * actually return. Confirmed two ways: reading the FastAPI handlers directly,
 * and then hitting the real running endpoint (`curl .../summary`) — the
 * live response caught a second discrepancy the source reading alone missed.
 * `_summary()` builds its `metrics` dict via `{m.id: m.value for m in
 * AnalyticsEngine().compute(...)}` — it unwraps every `Metric` down to its
 * bare `.value` before putting it in the response, so `metrics.net_worth` is
 * the raw `{internal, external, total, external_connected}` object directly
 * (no `.value`/`.as_of`/`.method` envelope), `metrics.monthly_income` is a
 * bare number, etc. `holdings.internal_bank_balance` is likewise a bare
 * number, not a `Metric`. No provenance field (`as_of`, `method`) survives
 * this endpoint at all — nothing here should claim one. Following the
 * precedent already set in `routes/customer/types.ts` (chat surface), the
 * corrected shapes live here, scoped to the surface that consumes them,
 * rather than editing the shared contract file.
 */

export interface DashboardProfile {
  persona_id: string;
  name: string;
  age: number;
  city: string;
  segment: string;
  language: string;
  avatar: string;
}

export interface NetWorthValue {
  internal: number;
  external: number;
  total: number;
  external_connected: boolean;
}

export interface GoalEntry {
  name: string;
  target: number;
  saved_so_far: number;
  horizon_years: number;
  progress_ratio: number;
  monthly_required_inr: number;
}

/** `ExternalHolding` (`app/domain/models.py`) as it actually serializes —
 * `rate` is nullable (e.g. equity/NPS holdings carry no fixed rate). */
export interface DashboardHolding {
  id: string;
  type: string;
  institution: string;
  amount: number;
  rate: number | null;
}

/** `ExternalLiability` as it actually serializes. Note: the persona JSON
 * fixtures carry an `emi` field, and `lib/types.ts`'s `PersonaLiability`
 * declares one too, but `ExternalLiability`'s pydantic model
 * (`_PersonaFileModel`, `extra="ignore"`) does not list `emi` among its
 * fields, so it is silently dropped before this ever reaches the wire —
 * never rely on `emi` from this endpoint. */
export interface DashboardLiability {
  id: string;
  type: string;
  lender: string;
  principal: number;
  rate: number;
}

export interface DashboardMetrics {
  net_worth: NetWorthValue;
  monthly_income: number;
  monthly_surplus: number;
  idle_balance: number;
  spend_by_category: Record<string, number>;
  risk_band: string;
  segment: string;
  goal_progress: { goals: GoalEntry[] };
}

export interface DashboardHoldingsBlock {
  aa_connected: boolean;
  internal_bank_balance: number;
  external: DashboardHolding[];
  external_liabilities: DashboardLiability[];
}

export interface CustomerDashboardSummary {
  profile: DashboardProfile;
  metrics: DashboardMetrics;
  holdings: DashboardHoldingsBlock;
  goals: GoalEntry[];
}

export type AaConsentStepReal = "transfer" | "processing";

export interface AaConsentStateReal {
  aa_available: boolean;
  transfer_granted: boolean;
  processing_granted: boolean;
  connected: boolean;
  holdings: DashboardHolding[] | null;
}
