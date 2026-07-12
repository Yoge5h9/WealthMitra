/**
 * Frontend-wide type definitions, mirrored from the backend's Pydantic
 * contracts (see `backend/app/domain/models.py`). This file is the single
 * source of truth for frontend types — every component/hook/query imports
 * from here rather than redeclaring shapes locally.
 *
 * Keep in sync with the backend contract whenever it changes.
 */

// ---------------------------------------------------------------------------
// C.1 — Metric (audit-grade universal output)
// ---------------------------------------------------------------------------

export type MetricUnit = "inr" | "ratio" | "score" | "label" | "json";

export interface Metric {
  id: string;
  value: number | string | Record<string, unknown>;
  unit: MetricUnit;
  as_of: string; // ISO date
  source_refs: string[];
  method: string;
  input_hash: string;
  computed_at: string; // ISO datetime
}

// ---------------------------------------------------------------------------
// C.2 — LeadPacket
// ---------------------------------------------------------------------------

export type LeadFamily = "investment_insurance" | "loans_cards";
export type LeadStatus = "new" | "contacted" | "converted";

export interface LeadCustomer {
  persona_id: string;
  name: string;
  segment: string;
  age_band: string;
  city_tier: string;
  language: string;
}

export interface LeadTrigger {
  type: string;
  utterance: string;
  ts: string;
}

export interface LeadFinancialSnapshot {
  monthly_income: number;
  monthly_surplus: number;
  idle_balance: number;
  external_holdings: PersonaHolding[];
  liabilities: PersonaLiability[];
}

export interface LeadRisk {
  capacity_score: number;
  tolerance_score: number;
  band: string;
}

export interface LeadGoal {
  name: string;
  horizon_years: number;
  target: number;
}

export interface LeadSuitability {
  recommended_shelf: string[];
  excluded: string[];
  reasons: string[];
  offer_recommendations?: Array<{
    id: string;
    name: string;
    provider_name: string;
    source: "idbi" | "partner";
    reasons: string[];
    display_disclaimer: string;
  }>;
}

export interface LeadConsent {
  aa_consent_id: string | null;
  advice_consent: boolean;
}

export interface LeadPacket {
  lead_id: string;
  family: LeadFamily;
  status: LeadStatus;
  customer: LeadCustomer;
  trigger: LeadTrigger;
  financial_snapshot: LeadFinancialSnapshot;
  risk: LeadRisk;
  goals: LeadGoal[];
  suitability: LeadSuitability;
  next_best_action: string;
  consent: LeadConsent;
  priority_score: number; // 5..99
  created_at: string;
}

// ---------------------------------------------------------------------------
// C.3 — Supporting domain models
// ---------------------------------------------------------------------------

export type ProductTag = "vanilla" | "regulated";
export type ProductCategory =
  | "deposit"
  | "mutual_fund"
  | "bond"
  | "govt_scheme"
  | "pms"
  | "aif"
  | "structured"
  | "insurance"
  | "portfolio";

export interface Product {
  id: string;
  name: string;
  tag: ProductTag;
  category: ProductCategory;
  min_amount: number;
  expected_return: string;
  description: string;
}

export interface Receipt {
  receipt_id: string;
  session_id: string;
  product_id: string;
  product_name: string;
  amount: number;
  executed_at: string;
  audit_ref: string;
}

export type NudgeKind = "functional" | "relational";
export type NudgeIntent =
  | "motivational"
  | "protective"
  | "opportunity"
  | "contextual"
  | "literacy"
  | "celebration";

export interface Nudge {
  id: string;
  persona_id: string;
  kind: NudgeKind;
  intent: NudgeIntent;
  title: string;
  body: string;
  language: string;
  source_metric_ids: string[];
  created_at: string;
}

export type AuditEntryKind =
  | "tool_call"
  | "llm_call"
  | "routing"
  | "guardrail"
  | "execution"
  | "consent";

export interface AuditEntry {
  id: string;
  session_id: string;
  ts: string;
  kind: AuditEntryKind;
  name: string;
  inputs: Record<string, unknown>;
  outputs_summary: Record<string, unknown>;
  refs: string[];
}

export interface FeatureMatrixRow {
  feature: string;
  values: Record<string, string>;
}

export interface FeatureMatrix {
  product_ids: string[];
  rows: FeatureMatrixRow[];
}

// ---------------------------------------------------------------------------
// C.4 — Persona
// ---------------------------------------------------------------------------

export interface PersonaProfile {
  id: string;
  name: string;
  age: number;
  city: string;
  segment: string;
  language: string;
  risk_tolerance: string;
  dependents: number;
  occupation: string;
  avatar: string;
  story: string;
}

export interface PersonaTransaction {
  id: string;
  date: string;
  amount: number;
  type: "credit" | "debit";
  category: string;
  description: string;
  account: "sa" | "ca" | "cc";
}

export interface PersonaGoal {
  name: string;
  horizon_years: number;
  target: number;
  saved_so_far: number;
}

export interface PersonaHolding {
  id: string;
  type: string;
  institution: string;
  amount: number;
  rate: number;
}

export interface PersonaLiability {
  id: string;
  type: string;
  lender: string;
  principal: number;
  rate: number;
  emi: number;
}

export interface PersonaExternal {
  aa_available: boolean;
  connected: boolean;
  holdings: PersonaHolding[];
  liabilities: PersonaLiability[];
}

export interface Persona {
  profile: PersonaProfile;
  transactions: PersonaTransaction[];
  goals: PersonaGoal[];
  external: PersonaExternal;
}

// ---------------------------------------------------------------------------
// C.6 — SSE chat frames + WS events
// ---------------------------------------------------------------------------

export type CardType =
  | "spend_summary"
  | "recommendation"
  | "routed_to_rm"
  | "execution_confirm"
  | "execution_receipt"
  | "aa_connect"
  | "goal"
  | "literacy"
  | "nudge"
  | "distress_support"
  | "profile_question"
  | "profile_summary";

export interface ChatCard {
  card_type: CardType;
  [key: string]: unknown;
}

export type AvatarState =
  | "idle"
  | "listening"
  | "thinking"
  | "speaking"
  | "celebrating"
  | "concerned";

export type SseFrame =
  | { type: "token"; text: string }
  | { type: "card"; card: ChatCard }
  | { type: "avatar"; state: Exclude<AvatarState, "idle" | "listening"> }
  | { type: "done"; audit_ref: string };

export interface SpaceSocketEventMap {
  "lead.created": LeadPacket;
  "lead.updated": LeadPacket;
  "nudge.created": Nudge;
  "execution.completed": Receipt;
  "aa.connected": { session_id: string };
  "space.reset": { space_id: string };
  "chat.activity": { session_id: string; state: AvatarState };
}

export type SpaceSocketEventType = keyof SpaceSocketEventMap;

export type SpaceSocketEvent = {
  [K in SpaceSocketEventType]: { type: K; payload: SpaceSocketEventMap[K] };
}[SpaceSocketEventType];

// ---------------------------------------------------------------------------
// C.8 — API surface DTOs
// ---------------------------------------------------------------------------

export interface CreateSpaceResponse {
  space_id: string;
}

export interface CreateSessionRequest {
  persona_id: string;
  language: string;
}

export interface CreateSessionResponse {
  session_id: string;
  greeting: string;
}

export interface ChatRequest {
  session_id: string;
  message: string;
  language?: string;
}

export interface ExecuteRequest {
  session_id: string;
  product_id: string;
  amount: number;
  confirm_token: string;
}

export type AaConsentStep = "transfer" | "processing";

export interface AaConsentRequest {
  session_id: string;
  step: AaConsentStep;
  granted: boolean;
}

export interface AaState {
  session_id: string;
  transfer_granted: boolean;
  processing_granted: boolean;
  connected: boolean;
}

/** Wire shape of GET /api/customer/{session_id}/summary and its RM
 * persona-keyed twin. The backend unwraps every Metric to its bare value
 * before responding — no provenance envelope survives this endpoint. */
export interface CustomerSummary {
  profile: {
    persona_id: string;
    name: string;
    age: number;
    city: string;
    segment: string;
    language: string;
    avatar: string;
  };
  metrics: {
    net_worth: { internal: number; external: number; total: number; external_connected: boolean };
    monthly_income: number;
    monthly_surplus: number;
    idle_balance: number;
    spend_by_category: Record<string, number>;
    risk_band: string;
    segment: string;
    goal_progress: Record<string, unknown>;
  };
  holdings: {
    aa_connected: boolean;
    internal_bank_balance: number;
    external: { id: string; type: string; institution: string; amount: number; rate: number | null }[];
    external_liabilities: { id: string; type: string; lender: string; principal: number; rate: number }[];
  };
  goals: Record<string, unknown>[];
}

export type LeadStatusUpdate = { status: LeadStatus };
