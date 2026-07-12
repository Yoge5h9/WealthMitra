from __future__ import annotations

from app.catalogue.recommendations import (
    evaluate_card_eligibility,
    evaluate_eligibility,
    recommendations_for,
    resolve_offer,
)
from app.domain.models import PersonaProfile
from app.routing.engine import decide
from app.routing.intents import classify_intent

UNSECURED_CARD_IDS = [
    "idbi_aspire_platinum",
    "idbi_royale_signature",
    "idbi_euphoria_world",
    "idbi_winnings",
]


def profile(*, dependents: int = 0) -> PersonaProfile:
    return PersonaProfile(
        id="demo",
        name="Demo Customer",
        age=32,
        city="Mumbai",
        segment="mass_retail_salaried",
        language="en",
        risk_tolerance="moderate",
        dependents=dependents,
        occupation="Salaried professional",
        avatar="",
        story="Synthetic demo profile",
    )


def test_card_query_creates_rm_only_first_party_options() -> None:
    intent = classify_intent("I need a credit card with rewards", "en")
    assert intent == "loan_card_query"
    assert decide(intent, [], None).model_dump() == {
        "path": "rm_lead",
        "lead_family": "loans_cards",
        "reasons": ["credit_product_requires_rm_eligibility_review"],
    }

    offers = recommendations_for(profile(), {}, family="loans_cards", message="I need a credit card")
    assert 1 <= len(offers) <= 3
    assert offers[0]["id"] == "idbi_aspire_platinum"
    assert all(offer["source"] == "idbi" and offer["journey"] == "rm_only" for offer in offers)


def test_generic_card_request_routes_to_the_credit_rm_journey() -> None:
    intent = classify_intent("Which card should I get?", "en")
    assert intent == "loan_card_query"
    assert decide(intent, [], None).path == "rm_lead"


def test_named_aspire_question_is_factual_information_not_an_investment_intent() -> None:
    assert classify_intent("tell me about the Aspire card", "en") == "credit_product_info"
    offer = resolve_offer("tell me about the Aspire card")
    assert offer is not None and offer.id == "idbi_aspire_platinum"
    eligibility = evaluate_eligibility(profile(), {}, offer)
    assert eligibility["status"] == "eligible"
    assert offer.features and offer.fees and offer.source_url.startswith("https://www.idbi.bank.in/")


def test_nri_is_not_preeligible_for_aspire_and_never_recommended() -> None:
    nri = profile()
    nri = nri.model_copy(update={"segment": "nri", "city": "Dubai"})
    offer = resolve_offer("I want to apply for Aspire card")
    assert offer is not None
    assert evaluate_eligibility(nri, {}, offer)["status"] == "ineligible"
    assert recommendations_for(nri, {}, family="loans_cards", message="I want to apply for Aspire card") == []


def test_insurance_offer_is_partner_labeled_and_rm_only() -> None:
    offers = recommendations_for(profile(dependents=2), {}, family="investment_insurance", message="I need insurance")
    assert len(offers) == 1
    assert offers[0]["source"] == "partner"
    assert offers[0]["journey"] == "rm_only"
    assert offers[0]["eligibility"]["status"] == "eligible"


def test_distress_still_overrides_credit_intent() -> None:
    assert decide("loan_card_query", ["emi_stressed"], None).path == "distress_suppress"


def test_resident_salaried_is_eligible_for_aspire_and_royale() -> None:
    resident = profile().model_copy(update={"age": 28})

    results = {r["card_id"]: r for r in evaluate_card_eligibility(resident)}

    assert results["idbi_aspire_platinum"]["status"] == "eligible"
    assert results["idbi_royale_signature"]["status"] == "eligible"
    assert results["idbi_aspire_platinum"]["reason"]
    assert results["idbi_royale_signature"]["reason"]


def test_nri_without_idbi_fd_is_ineligible_for_unsecured_cards_with_imperium_alternative() -> None:
    nri = profile().model_copy(update={"segment": "nri", "city": "Dubai", "age": 35})
    # A non-IDBI external NRE FD only — the pre-AA-connect shape before a
    # customer's own IDBI deposit (see data/synthetic/arjun.json) is surfaced.
    metrics = {
        "external_holdings": [
            {"id": "hold-arjun-1", "type": "FD", "institution": "ICICI NRE", "amount": 700000, "rate": 7.0}
        ]
    }

    results = {r["card_id"]: r for r in evaluate_card_eligibility(nri, metrics)}

    for card_id in UNSECURED_CARD_IDS:
        assert results[card_id]["status"] == "ineligible"
        assert "NRI" in results[card_id]["reason"]
        assert results[card_id]["alternative"] is not None
        assert results[card_id]["alternative"]["card_id"] == "idbi_imperium_platinum"

    assert results["idbi_imperium_platinum"]["status"] == "needs_more_data"
    assert results["idbi_imperium_platinum"]["reason"]
    assert results["idbi_imperium_platinum"]["alternative"] is None


def test_nri_with_idbi_fcnr_fd_is_eligible_for_imperium() -> None:
    nri = profile().model_copy(update={"segment": "nri", "city": "Dubai", "age": 35})
    metrics = {
        "external_holdings": [
            {"id": "hold-nri-fcnr", "type": "FCNR", "institution": "IDBI Bank FCNR", "amount": 25000, "rate": 5.0}
        ]
    }

    results = {r["card_id"]: r for r in evaluate_card_eligibility(nri, metrics)}

    assert results["idbi_imperium_platinum"]["status"] == "eligible"
    assert results["idbi_imperium_platinum"]["reason"]


def test_minor_is_ineligible_for_every_card_on_age() -> None:
    minor = profile().model_copy(update={"age": 17})

    results = evaluate_card_eligibility(minor)

    assert results
    assert all(r["status"] == "ineligible" for r in results)
    assert all("age" in r["reason"].lower() for r in results)
