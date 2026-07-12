/**
 * Per-card-type shapes, narrowed from the generic `ChatCard` (`card_type` +
 * index signature) in `lib/types.ts`. Matched against the actual payloads
 * built in `backend/app/agent/orchestrator.py::_cards`/`_recommendation_card`/
 * `_spend_card` and `backend/app/agent/tools.py::request_execution` — not the
 * aspirational shape, the real one.
 */
import type { ChatCard, ProductCategory, ProductTag } from "@/lib/types";

export interface SpendSummaryCard extends ChatCard {
  card_type: "spend_summary";
  monthly_income: number;
  spend_by_category: Record<string, number>;
  savings_rate: number;
}

export interface RecommendationProduct {
  id: string;
  name: string;
  tag: ProductTag;
  category: ProductCategory;
  min_amount: number;
  expected_return: string;
}

export interface RecommendationCard extends ChatCard {
  card_type: "recommendation";
  product: RecommendationProduct;
  why: string[];
}

export interface RoutedToRmCard extends ChatCard {
  card_type: "routed_to_rm";
  lead_id: string;
  family: "investment_insurance" | "loans_cards";
  priority_score: number;
  next_best_action: string;
  what_happens_next: string;
  recommendations?: Array<{
    id: string;
    name: string;
    provider_name: string;
    source: "idbi" | "partner";
    reasons: string[];
    display_disclaimer: string;
  }>;
}

export interface ExecutionConfirmCard extends ChatCard {
  card_type: "execution_confirm";
  product_id: string;
  product_name: string;
  amount: number;
  expected_return: string;
  confirm_token: string;
  note: string;
}

/** Never arrives over SSE — synthesized client-side from the `Receipt` a
 * successful `POST /api/execute` returns, so `ExecutionConfirmCard` can swap
 * itself for this in place once the customer confirms. */
export interface ExecutionReceiptCard extends ChatCard {
  card_type: "execution_receipt";
  receipt_id: string;
  product_name: string;
  amount: number;
  executed_at: string;
  audit_ref: string;
}

export interface DistressSupportCard extends ChatCard {
  card_type: "distress_support";
  message: string;
  options: string[];
}

export interface LiteracyCard extends ChatCard {
  card_type: "literacy";
  term: string;
  definition: string;
  language?: string;
}

export interface GoalCard extends ChatCard {
  card_type: "goal";
  name: string;
  target: number;
  saved_so_far: number;
  horizon_years: number;
}

export interface NudgeCard extends ChatCard {
  card_type: "nudge";
  title: string;
  body: string;
  kind: "functional" | "relational";
  intent: string;
}

export interface AaConnectCard extends ChatCard {
  card_type: "aa_connect";
  headline: string;
  body: string;
}

export interface ProfileQuestionCard extends ChatCard {
  card_type: "profile_question";
  step: number;
  total_steps: number;
  key: string;
  question: string;
  options: string[];
}

export interface ProfileSummaryCard extends ChatCard {
  card_type: "profile_summary";
  answers: Record<string, string>;
  missing_data: string[];
  next_step: string;
}

export interface CreditProductDetailCard extends ChatCard {
  card_type: "credit_product_detail";
  product: {
    id: string;
    name: string;
    provider_name: string;
    source: "idbi" | "partner";
    features: string[];
    fees: string[];
    eligibility: { status: "eligible" | "ineligible" | "needs_more_data"; reasons: string[]; checked_criteria: string[] };
    display_disclaimer: string;
    source_url: string;
    source_checked_at: string;
  };
}

export interface CreditEligibilityResultCard extends ChatCard {
  card_type: "credit_eligibility_result";
  status: "ineligible" | "needs_more_data";
  message: string;
}
