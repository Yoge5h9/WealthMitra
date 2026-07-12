"""Deterministic, RM-only loan/card/insurance offer ranking for the demo.

This is deliberately separate from the investment suitability matrix: a cash-flow
profile can start an eligibility conversation, but it can never grant credit or
select an insurance policy.  The returned offers are a short, traceable brief
for the RM, not an approval or a customer-facing recommendation to execute.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.domain.models import PersonaProfile

OfferSource = Literal["idbi", "partner"]
OfferFamily = Literal["loans_cards", "investment_insurance"]


@dataclass(frozen=True)
class CreditOffer:
    id: str
    name: str
    family: OfferFamily
    product_type: str
    provider_name: str
    source: OfferSource
    journey: Literal["rm_only"]
    display_disclaimer: str


def _load_offers() -> dict[str, CreditOffer]:
    path = Path(__file__).resolve().parents[2] / "config" / "credit_offers.json"
    return {raw["id"]: CreditOffer(**raw) for raw in json.loads(path.read_text(encoding="utf-8"))}


OFFERS = _load_offers()


def recommendations_for(
    profile: PersonaProfile,
    metrics: dict[str, object],
    *,
    family: OfferFamily,
    message: str,
) -> list[dict]:
    """Return at most three RM-review offers, ordered for the stated need.

    No bureau score, KYC state, property value, or insurance underwriting data
    is available in the demo. The reasons therefore only state observed profile
    facts and explicitly defer every eligibility/coverage decision to the RM.
    """
    del metrics  # Kept in the boundary for future rules; no inferred credit decision in v1.
    query = message.lower()
    candidates = [offer for offer in OFFERS.values() if offer.family == family]

    if family == "loans_cards":
        if any(term in query for term in ("home", "house", "property", "mortgage")):
            preferred = ("idbi_home_loan", "idbi_personal_loan", "idbi_aspire_platinum")
        elif any(term in query for term in ("card", "credit card", "reward")):
            preferred = ("idbi_aspire_platinum", "idbi_personal_loan", "idbi_home_loan")
        else:
            preferred = ("idbi_personal_loan", "idbi_aspire_platinum", "idbi_home_loan")
    else:
        preferred = ("tata_aig_medicare",)

    ordered = [OFFERS[offer_id] for offer_id in preferred if offer_id in {offer.id for offer in candidates}]
    income_context = "A declared income profile gives the RM a starting point for an eligibility conversation."
    dependent_context = (
        "Your profile records dependents, so protection needs are worth reviewing with a licensed RM."
        if profile.dependents > 0
        else "A licensed RM will first confirm your coverage need and eligibility."
    )
    result: list[dict] = []
    for offer in ordered[:3]:
        profile_reason = dependent_context if offer.family == "investment_insurance" else income_context
        result.append(
            {
                "id": offer.id,
                "name": offer.name,
                "provider_name": offer.provider_name,
                "source": offer.source,
                "product_type": offer.product_type,
                "journey": offer.journey,
                "reasons": [profile_reason, "Final eligibility and terms require an IDBI RM review."],
                "display_disclaimer": offer.display_disclaimer,
            }
        )
    return result
