/**
 * Priority-score band + breakdown for the RM queue's "why this number"
 * affordance — every figure must be traceable.
 *
 * The breakdown terms below mirror the deterministic formula in
 * `backend/app/routing/engine.py::priority_score` verbatim (same weights,
 * same divisors, same cap) so the sum always reconciles with the lead's own
 * `priority_score` — this is a display of how that number was built, not a
 * second guess at it.
 */
import type { LeadPacket } from "@/lib/types";

export type PriorityBand = "hot" | "warm" | "standard";

export function priorityBand(score: number): PriorityBand {
  if (score >= 70) return "hot";
  if (score >= 40) return "warm";
  return "standard";
}

export const PRIORITY_BAND_LABEL: Record<PriorityBand, string> = {
  hot: "Hot",
  warm: "Warm",
  standard: "Standard",
};

const SURPLUS_WEIGHT = 0.4;
const SURPLUS_DIVISOR = 1000;
const SURPLUS_CAP = 50;
const IDLE_WEIGHT = 0.3;
const IDLE_DIVISOR = 10000;
const TOLERANCE_DIVISOR = 5;
const GOAL_BONUS = 20;

export interface PriorityTerm {
  label: string;
  detail: string;
  contribution: number;
}

export function priorityBreakdown(lead: LeadPacket): PriorityTerm[] {
  const surplus = lead.financial_snapshot.monthly_surplus;
  const idle = lead.financial_snapshot.idle_balance;
  const tolerance = lead.risk.tolerance_score;
  const hasGoals = lead.goals.length > 0;

  const surplusTerm = SURPLUS_WEIGHT * Math.min(surplus / SURPLUS_DIVISOR, SURPLUS_CAP);
  const idleTerm = IDLE_WEIGHT * (idle / IDLE_DIVISOR);
  const toleranceTerm = tolerance / TOLERANCE_DIVISOR;
  const goalTerm = hasGoals ? GOAL_BONUS : 0;

  return [
    { label: "Monthly surplus", detail: "0.4 × min(surplus ÷ 1,000, 50)", contribution: surplusTerm },
    { label: "Idle balance", detail: "0.3 × (idle balance ÷ 10,000)", contribution: idleTerm },
    { label: "Risk tolerance", detail: "tolerance score ÷ 5", contribution: toleranceTerm },
    { label: "Active goals", detail: hasGoals ? "goal bonus applied" : "no goals set", contribution: goalTerm },
  ];
}
