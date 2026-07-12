"""Static, source-backed credit product master and deterministic pre-eligibility.

The July demo deliberately stores a small set of verified product facts rather
than scraping during a customer chat. A card is surfaced to an RM only after
the hard criteria available in the synthetic profile pass; this is a
pre-eligibility check, never an underwriting or issuance decision.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.domain.models import PersonaExternal, PersonaProfile

OfferSource = Literal["idbi", "partner"]
OfferFamily = Literal["loans_cards", "investment_insurance"]
EligibilityStatus = Literal["eligible", "ineligible", "needs_more_data"]


@dataclass(frozen=True)
class CreditOffer:
    id: str
    name: str
    family: OfferFamily
    product_type: str
    provider_name: str
    source: OfferSource
    journey: Literal["rm_only"]
    aliases: list[str]
    features: list[str]
    fees: list[str]
    eligibility: dict
    display_disclaimer: str
    source_url: str
    source_checked_at: str


def _load_offers() -> dict[str, CreditOffer]:
    path = Path(__file__).resolve().parents[2] / "config" / "credit_offers.json"
    return {raw["id"]: CreditOffer(**raw) for raw in json.loads(path.read_text(encoding="utf-8"))}


OFFERS = _load_offers()


def resolve_offer(message: str) -> CreditOffer | None:
    query = message.lower()
    matches = [offer for offer in OFFERS.values() if any(alias in query for alias in offer.aliases)]
    return max(matches, key=lambda offer: max(len(alias) for alias in offer.aliases), default=None)


def evaluate_eligibility(profile: PersonaProfile, metrics: dict[str, object], offer: CreditOffer) -> dict:
    """Evaluate only product-master rules that this demo can actually prove."""
    rules = offer.eligibility
    reasons: list[str] = []
    checked: list[str] = []

    if rules.get("resident_india"):
        checked.append("Indian residency")
        if profile.segment == "nri":
            return _result("ineligible", ["Set up for India-resident profiles; your profile is marked NRI."], checked)

    min_age = rules.get("min_age")
    if min_age is not None:
        checked.append("age")
        if profile.age < int(min_age):
            return _result("ineligible", [f"This card requires a primary-cardholder age of at least {min_age}."], checked)

    max_age = rules.get("max_age_self_employed") if _is_self_employed(profile) else rules.get("max_age_salaried")
    if max_age is not None:
        checked.append("age and employment type")
        if profile.age > int(max_age):
            return _result("ineligible", [f"This card's published age limit is {max_age} for your profile type."], checked)

    fd_threshold = rules.get("requires_idbi_fd_min")
    if fd_threshold:
        checked.append("eligible IDBI Fixed Deposit")
        threshold = int(fd_threshold)
        deposit = _qualifying_idbi_deposit(metrics, threshold, accepts_fcnr=bool(rules.get("accepts_fcnr")))
        if deposit is not None:
            return _result(
                "eligible",
                [f"An eligible IDBI Fixed Deposit of ₹{int(deposit['amount']):,} secures this card."],
                checked,
            )
        return _result(
            "needs_more_data",
            [f"Please confirm an eligible IDBI Fixed Deposit of at least ₹{threshold:,} before we can check this secured-card path."],
            checked,
        )

    if rules.get("requires_existing_relationship") or rules.get("requires_property_and_repayment_review"):
        return _result(
            "needs_more_data",
            ["We need the product-specific banking and underwriting facts before we can take this to an RM."],
            checked,
        )

    reasons.append("Your known profile passes the published demo pre-eligibility checks.")
    return _result("eligible", reasons, checked)


def card_metrics_from_external(external: PersonaExternal) -> dict[str, object]:
    """The only path a holding can reach card eligibility: AA-connected and
    consented. Mirrors `tools.get_holdings`' own `connected` gate so a deposit
    the customer has not yet linked can never silently qualify a secured card.
    """
    if not external.connected:
        return {}
    return {"external_holdings": [h.model_dump(mode="json") for h in external.holdings]}


def evaluate_card_eligibility(profile: PersonaProfile, metrics: dict[str, object] | None = None) -> list[dict]:
    """Deterministic pre-eligibility verdict for every credit card, independent of the RM shelf filter.

    Unlike `recommendations_for`, this returns every card's verdict (including
    `ineligible`/`needs_more_data`) so an empathetic response can explain why a
    card is not offered and, where one exists, name a genuine alternative path.
    """
    metrics = metrics or {}
    cards = [offer for offer in OFFERS.values() if offer.product_type == "credit_card"]
    results = [_card_verdict(profile, metrics, offer) for offer in cards]

    unsecured = [r for r in results if not OFFERS[r["card_id"]].eligibility.get("requires_idbi_fd_min")]
    secured = next((r for r in results if OFFERS[r["card_id"]].eligibility.get("requires_idbi_fd_min")), None)
    if profile.segment == "nri" and secured and unsecured and all(r["status"] == "ineligible" for r in unsecured):
        for r in unsecured:
            r["alternative"] = {
                "card_id": secured["card_id"],
                "name": secured["name"],
                "why": "A card secured against your IDBI NRE/FCNR fixed deposit — the NRI-eligible path.",
            }

    return results


def _card_verdict(profile: PersonaProfile, metrics: dict[str, object], offer: CreditOffer) -> dict:
    eligibility = evaluate_eligibility(profile, metrics, offer)
    return {
        "card_id": offer.id,
        "name": offer.name,
        "status": eligibility["status"],
        "reason": " ".join(eligibility["reasons"]),
        "alternative": None,
    }


def _qualifying_idbi_deposit(metrics: dict[str, object], threshold: int, *, accepts_fcnr: bool) -> dict | None:
    holdings = metrics.get("external_holdings") if isinstance(metrics, dict) else None
    if not holdings:
        return None
    allowed_types = {"FD", "FCNR", "NRE"} if accepts_fcnr else {"FD"}
    for holding in holdings:
        institution = str(holding.get("institution", "")).lower()
        deposit_type = str(holding.get("type", "")).upper()
        amount = holding.get("amount") or 0
        if "idbi" in institution and deposit_type in allowed_types and amount >= threshold:
            return holding
    return None


def recommendations_for(profile: PersonaProfile, metrics: dict[str, object], *, family: OfferFamily, message: str) -> list[dict]:
    """Return only pre-eligible offers; ineligible/unknown products never reach the RM queue."""
    named = resolve_offer(message)
    candidates = [named] if named and named.family == family else [offer for offer in OFFERS.values() if offer.family == family]
    result: list[dict] = []
    for offer in candidates:
        if offer is None:
            continue
        eligibility = evaluate_eligibility(profile, metrics, offer)
        if family == "loans_cards" and eligibility["status"] != "eligible":
            continue
        result.append(offer_payload(offer, eligibility))
    return result[:3]


def offer_payload(offer: CreditOffer, eligibility: dict) -> dict:
    return {
        "id": offer.id,
        "name": offer.name,
        "provider_name": offer.provider_name,
        "source": offer.source,
        "product_type": offer.product_type,
        "journey": offer.journey,
        "features": offer.features,
        "fees": offer.fees,
        "eligibility": eligibility,
        "reasons": eligibility["reasons"],
        "display_disclaimer": offer.display_disclaimer,
        "source_url": offer.source_url,
        "source_checked_at": offer.source_checked_at,
    }


def _is_self_employed(profile: PersonaProfile) -> bool:
    occupation = profile.occupation.lower()
    return any(word in occupation for word in ("business", "self-employed", "trader", "freelance"))


def _result(status: EligibilityStatus, reasons: list[str], checked_criteria: list[str]) -> dict:
    return {"status": status, "reasons": reasons, "checked_criteria": checked_criteria}
