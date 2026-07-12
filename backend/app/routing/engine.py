"""Deterministic routing engine — the compliance moat.

This is rules, not the LLM: regulated financial products and distress signals
must never resolve to auto-execution, and that guarantee has to be provable by
a decision tree a human can read, not by trusting a model's judgement.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.models import Product
from app.routing.intents import Intent

RoutePath = Literal["auto_execute", "rm_lead", "distress_suppress", "info_only"]
LeadFamily = Literal["investment_insurance", "loans_cards"]

_DISTRESS_FLAGS = frozenset({"emi_stressed", "overdraft"})
_WANTS_TO_BUY: frozenset[Intent] = frozenset({"invest_surplus", "goal_set", "regulated_query", "fd_query", "loan_card_query"})

# The documented priority-score formula, deliberately not an undocumented
# `*2` on the surplus term. Weights are named constants so retuning is a
# config-visible diff, not a buried literal.
_SURPLUS_WEIGHT = 0.4
_SURPLUS_DIVISOR = 1000.0
_SURPLUS_CAP = 50.0
_IDLE_WEIGHT = 0.3
_IDLE_DIVISOR = 10000.0
_TOLERANCE_DIVISOR = 5.0
_GOAL_BONUS = 20
_SCORE_MIN = 5
_SCORE_MAX = 99


class Route(BaseModel):
    path: RoutePath
    lead_family: LeadFamily | None = None
    reasons: list[str] = Field(default_factory=list)


def wants_to_buy(intent: Intent) -> bool:
    return intent in _WANTS_TO_BUY


def decide(intent: Intent, behaviour_flags: list[str], product: Product | None) -> Route:
    """The compliance decision tree. Order matters and is exhaustive:

    1. An explicit distress utterance suppresses selling outright — always,
       regardless of flags or any attached product.
    2. A distress flag plus either buy-intent or an attached product (a product
       in the turn is itself a sales opportunity) also suppresses. A distressed
       customer asking a non-buy question with no product attached still gets
       served (info_only) — suppression targets selling, not conversation.
    3. A regulated intent or a regulated-tagged product is never auto-executed
       — it always becomes an RM lead.
    4. A vanilla-tagged product with none of the above auto-executes.
    5. Anything else is informational only.
    """
    if intent == "distress_signal":
        return Route(path="distress_suppress", reasons=["distress_signal_intent"])

    if _DISTRESS_FLAGS.intersection(behaviour_flags) and (wants_to_buy(intent) or product is not None):
        reasons = ["distress_flag_present"]
        if wants_to_buy(intent):
            reasons.append(f"buy_intent:{intent}")
        if product is not None:
            reasons.append(f"product_attached:{product.id}")
        return Route(path="distress_suppress", reasons=reasons)

    if intent == "loan_card_query":
        return Route(
            path="rm_lead",
            lead_family="loans_cards",
            reasons=["credit_product_requires_rm_eligibility_review"],
        )

    if intent == "credit_product_info":
        return Route(path="info_only", reasons=["factual_credit_product_information"])

    product_tag = product.tag if product is not None else None
    if intent == "regulated_query" or product_tag == "regulated":
        reasons = [f"regulated_intent:{intent}"]
        if product_tag == "regulated":
            reasons.append(f"regulated_product:{product.id}")  # type: ignore[union-attr]
        return Route(path="rm_lead", lead_family="investment_insurance", reasons=reasons)

    if product_tag == "vanilla":
        return Route(path="auto_execute", reasons=[f"vanilla_product:{product.id}"])  # type: ignore[union-attr]

    return Route(path="info_only", reasons=[f"no_actionable_route:intent={intent}"])


def priority_score(monthly_surplus: float, idle_balance: float, tolerance_score: float, has_goals: bool) -> int:
    """Priority formula: 0.4*min(surplus/1000, 50) + 0.3*(idle/10000) + tolerance/5
    + (20 if has_goals else 0), clamped to [5, 99].
    """
    surplus_term = _SURPLUS_WEIGHT * min(monthly_surplus / _SURPLUS_DIVISOR, _SURPLUS_CAP)
    idle_term = _IDLE_WEIGHT * (idle_balance / _IDLE_DIVISOR)
    tolerance_term = tolerance_score / _TOLERANCE_DIVISOR
    goal_term = _GOAL_BONUS if has_goals else 0
    raw = surplus_term + idle_term + tolerance_term + goal_term
    return max(_SCORE_MIN, min(_SCORE_MAX, int(raw)))
