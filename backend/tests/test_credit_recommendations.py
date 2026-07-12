from __future__ import annotations

from app.catalogue.recommendations import evaluate_eligibility, recommendations_for, resolve_offer
from app.domain.models import PersonaProfile
from app.routing.engine import decide
from app.routing.intents import classify_intent


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
