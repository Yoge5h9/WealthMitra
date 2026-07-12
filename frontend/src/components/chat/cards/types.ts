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
