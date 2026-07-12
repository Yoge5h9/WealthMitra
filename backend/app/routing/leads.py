"""Deterministic LeadPacket construction — no LLM involvement.

Every field the RM console needs is filled here from already-computed inputs;
the caller (the orchestrator) supplies both the sequence number and the clock
reading — this module never touches global state or `datetime.now()`, so lead
ids and timestamps are fully reproducible from inputs alone.
"""

from __future__ import annotations

from datetime import datetime

from app.domain.models import LeadPacket, PersonaProfile, Product
from app.routing.engine import LeadFamily, priority_score

_AGE_BAND_EDGES: tuple[int, ...] = (25, 35, 45, 55, 65)
_AGE_BAND_LABELS: tuple[str, ...] = ("18-24", "25-34", "35-44", "45-54", "55-64")
_AGE_BAND_SENIOR = "65+"

_TIER_1_CITIES = frozenset(
    {
        "mumbai", "delhi", "new delhi", "bengaluru", "bangalore", "hyderabad",
        "chennai", "kolkata", "pune", "ahmedabad",
    }
)

_NEXT_BEST_ACTION_WITH_SHELF: dict[LeadFamily, str] = {
    "investment_insurance": "RM to review {product} suitability with {name} and confirm within regulatory disclosure norms.",
    "loans_cards": "RM to discuss {product} eligibility and repayment terms with {name}.",
}
_NEXT_BEST_ACTION_NO_SHELF: dict[LeadFamily, str] = {
    "investment_insurance": "RM to review {name}'s investment goals and recommend from the eligible shelf.",
    "loans_cards": "RM to review {name}'s credit profile and recommend from the eligible shelf.",
}


def age_band(age: int) -> str:
    for edge, label in zip(_AGE_BAND_EDGES, _AGE_BAND_LABELS):
        if age < edge:
            return label
    return _AGE_BAND_SENIOR


def city_tier(city: str) -> str:
    return "urban_t1" if city.strip().lower() in _TIER_1_CITIES else "urban_t2"


def _shelf_names(shelf: list[Product]) -> list[str]:
    vanilla_names = [p.name for p in shelf if p.tag == "vanilla"]
    regulated_names = [p.name for p in shelf if p.tag == "regulated"]
    return vanilla_names + regulated_names


def _next_best_action(family: LeadFamily, shelf: list[Product], customer_name: str) -> str:
    if shelf:
        return _NEXT_BEST_ACTION_WITH_SHELF[family].format(product=shelf[0].name, name=customer_name)
    return _NEXT_BEST_ACTION_NO_SHELF[family].format(name=customer_name)


def build_lead_packet(
    profile: PersonaProfile,
    metrics: dict[str, object],
    shelf: list[Product],
    trigger_utterance: str,
    family: LeadFamily,
    *,
    seq: int,
    now: datetime,
) -> LeadPacket:
    """Assemble a `LeadPacket` for RM handoff.

    Both `seq` (an orchestrator-owned counter) and `now` (the clock reading)
    are caller-supplied — this function never reaches for global state or the
    real clock, so identical inputs always produce identical packets.
    """
    created_at = now
    goals = list(metrics.get("goals", []))  # type: ignore[arg-type]

    return LeadPacket(
        lead_id=f"LP-2026-{seq:06d}",
        family=family,
        status="new",
        customer={
            "persona_id": profile.id,
            "name": profile.name,
            "segment": profile.segment,
            "age_band": age_band(profile.age),
            "city_tier": city_tier(profile.city),
            "language": profile.language,
        },
        trigger={
            "type": "chat_message",
            "utterance": trigger_utterance,
            "ts": created_at.isoformat(),
        },
        financial_snapshot={
            "monthly_income": metrics.get("monthly_income", 0),
            "monthly_surplus": metrics.get("monthly_surplus", 0),
            "idle_balance": metrics.get("idle_balance", 0),
            "external_holdings": list(metrics.get("external_holdings", [])),  # type: ignore[arg-type]
            "liabilities": list(metrics.get("liabilities", [])),  # type: ignore[arg-type]
        },
        risk={
            "capacity_score": metrics.get("capacity_score"),
            "tolerance_score": metrics.get("tolerance_score"),
            "band": metrics.get("risk_band"),
        },
        goals=goals,
        suitability={
            "recommended_shelf": _shelf_names(shelf),
            "excluded": [],
            "reasons": [
                f"family={family}",
                f"shelf_size={len(shelf)}",
                "consent_capture_is_a_separate_dedicated_flow",
            ],
        },
        next_best_action=_next_best_action(family, shelf, profile.name),
        consent={"aa_consent_id": None, "advice_consent": False},
        priority_score=priority_score(
            monthly_surplus=float(metrics.get("monthly_surplus", 0)),  # type: ignore[arg-type]
            idle_balance=float(metrics.get("idle_balance", 0)),  # type: ignore[arg-type]
            tolerance_score=float(metrics.get("tolerance_score", 0)),  # type: ignore[arg-type]
            has_goals=bool(goals),
        ),
        created_at=created_at,
    )
