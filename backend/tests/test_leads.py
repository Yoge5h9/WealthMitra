from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domain.models import PersonaProfile, Product
from app.routing.leads import age_band, build_lead_packet, city_tier, tag_for_card_verdict

RAVI = PersonaProfile(
    id="ravi", name="Ravi Kumar", age=28, city="Mumbai", segment="mass_retail_salaried",
    language="en", risk_tolerance="moderate", dependents=0, occupation="salaried",
    avatar="ravi.png", story="Salaried professional building his first SIP habit.",
)
PRIYA = PersonaProfile(
    id="priya", name="Priya Sharma", age=26, city="Jaipur", segment="mass_retail_gig",
    language="hi", risk_tolerance="conservative", dependents=1, occupation="gig_worker",
    avatar="priya.png", story="Gig worker with irregular income.",
)

VANILLA = Product(
    id="fd_1yr", name="1-Year Fixed Deposit", tag="vanilla", category="deposit",
    min_amount=1000, expected_return="7.1% p.a.", description="Retail FD.",
)
REGULATED = Product(
    id="flexicap_mf", name="Flexicap Growth Fund", tag="regulated", category="mutual_fund",
    min_amount=500, expected_return="market-linked", description="Actively-managed equity MF.",
)

FULL_METRICS: dict[str, object] = {
    "monthly_income": 85000,
    "monthly_surplus": 22000,
    "idle_balance": 60000,
    "capacity_score": 72,
    "tolerance_score": 65,
    "risk_band": "moderate",
    "external_holdings": ["mutual_fund@HDFC AMC"],
    "liabilities": ["personal_loan@ICICI"],
    "goals": [{"name": "child_education", "horizon_years": 10, "target": 2_500_000}],
}


# --- age_band ----------------------------------------------------------------

@pytest.mark.parametrize(
    "age,expected",
    [
        (18, "18-24"), (24, "18-24"),
        (25, "25-34"), (34, "25-34"),
        (35, "35-44"), (44, "35-44"),
        (45, "45-54"), (54, "45-54"),
        (55, "55-64"), (64, "55-64"),
        (65, "65+"), (80, "65+"),
    ],
)
def test_age_band_buckets(age, expected):
    assert age_band(age) == expected


# --- city_tier -----------------------------------------------------------------

@pytest.mark.parametrize("city", ["Mumbai", "mumbai", " MUMBAI ", "Bengaluru", "Bangalore", "Pune"])
def test_city_tier_metro_is_urban_t1(city):
    assert city_tier(city) == "urban_t1"


@pytest.mark.parametrize("city", ["Jaipur", "Nagpur", "Indore"])
def test_city_tier_non_metro_is_urban_t2(city):
    assert city_tier(city) == "urban_t2"


# --- build_lead_packet ---------------------------------------------------------

FIXED_NOW = datetime(2026, 7, 13, 10, 30, 0, tzinfo=timezone.utc)


def test_build_lead_packet_fills_every_field():
    packet = build_lead_packet(
        profile=RAVI,
        metrics=FULL_METRICS,
        shelf=[REGULATED, VANILLA],
        trigger_utterance="should I invest in equity mutual funds?",
        family="investment_insurance",
        seq=1,
        now=FIXED_NOW,
    )
    assert packet.lead_id == "LP-2026-000001"
    assert packet.family == "investment_insurance"
    assert packet.status == "new"
    assert packet.customer == {
        "persona_id": "ravi",
        "name": "Ravi Kumar",
        "segment": "mass_retail_salaried",
        "age_band": "25-34",
        "city_tier": "urban_t1",
        "language": "en",
    }
    assert packet.trigger == {
        "type": "chat_message",
        "utterance": "should I invest in equity mutual funds?",
        "ts": FIXED_NOW.isoformat(),
    }
    assert packet.financial_snapshot == {
        "monthly_income": 85000,
        "monthly_surplus": 22000,
        "idle_balance": 60000,
        "external_holdings": ["mutual_fund@HDFC AMC"],
        "liabilities": ["personal_loan@ICICI"],
    }
    assert packet.risk == {"capacity_score": 72, "tolerance_score": 65, "band": "moderate"}
    assert packet.goals == [{"name": "child_education", "horizon_years": 10, "target": 2_500_000}]
    assert packet.suitability["recommended_shelf"] == ["1-Year Fixed Deposit", "Flexicap Growth Fund"]
    assert packet.suitability["excluded"] == []
    assert packet.suitability["reasons"]
    assert packet.next_best_action
    assert "Flexicap Growth Fund" in packet.next_best_action
    assert packet.consent == {"aa_consent_id": None, "advice_consent": False}
    assert 5 <= packet.priority_score <= 99
    assert packet.created_at == FIXED_NOW


def test_lead_id_zero_padded_sequence():
    packet = build_lead_packet(
        profile=RAVI, metrics=FULL_METRICS, shelf=[], trigger_utterance="x",
        family="loans_cards", seq=42, now=FIXED_NOW,
    )
    assert packet.lead_id == "LP-2026-000042"


def test_build_lead_packet_is_deterministic_given_same_inputs():
    kwargs = dict(
        profile=RAVI, metrics=FULL_METRICS, shelf=[VANILLA], trigger_utterance="invest my surplus",
        family="investment_insurance", seq=7, now=FIXED_NOW,
    )
    a = build_lead_packet(**kwargs)
    b = build_lead_packet(**kwargs)
    assert a == b


def test_build_lead_packet_requires_now_argument():
    # Binding amendment: no datetime.now defaults — the caller must always
    # supply the clock reading explicitly.
    with pytest.raises(TypeError):
        build_lead_packet(
            profile=RAVI, metrics=FULL_METRICS, shelf=[], trigger_utterance="x",
            family="investment_insurance", seq=1,
        )


def test_recommended_shelf_orders_vanilla_before_regulated_regardless_of_input_order():
    packet = build_lead_packet(
        profile=RAVI, metrics=FULL_METRICS, shelf=[REGULATED, VANILLA], trigger_utterance="x",
        family="investment_insurance", seq=1, now=FIXED_NOW,
    )
    assert packet.suitability["recommended_shelf"] == [VANILLA.name, REGULATED.name]


def test_next_best_action_loans_cards_family():
    packet = build_lead_packet(
        profile=PRIYA, metrics=FULL_METRICS, shelf=[VANILLA], trigger_utterance="need a loan",
        family="loans_cards", seq=1, now=FIXED_NOW,
    )
    assert "loan" in packet.next_best_action.lower() or "credit" in packet.next_best_action.lower() or VANILLA.name in packet.next_best_action


def test_next_best_action_falls_back_gracefully_with_empty_shelf():
    packet = build_lead_packet(
        profile=PRIYA, metrics=FULL_METRICS, shelf=[], trigger_utterance="need a loan",
        family="loans_cards", seq=1, now=FIXED_NOW,
    )
    assert packet.next_best_action
    assert "Priya Sharma" in packet.next_best_action


def test_build_lead_packet_defaults_missing_optional_metrics_to_empty():
    minimal_metrics: dict[str, object] = {}
    packet = build_lead_packet(
        profile=RAVI, metrics=minimal_metrics, shelf=[], trigger_utterance="hello",
        family="investment_insurance", seq=1, now=FIXED_NOW,
    )
    assert packet.financial_snapshot["monthly_income"] == 0
    assert packet.financial_snapshot["external_holdings"] == []
    assert packet.financial_snapshot["liabilities"] == []
    assert packet.goals == []
    assert packet.priority_score == 5


# --- card-lead exploratory tagging -------------------------------------------


def test_tag_for_card_verdict_eligible_is_standard():
    assert tag_for_card_verdict("eligible") == "standard"


@pytest.mark.parametrize("status", ["ineligible", "needs_more_data"])
def test_tag_for_card_verdict_not_eligible_is_exploratory(status):
    assert tag_for_card_verdict(status) == "exploratory_not_yet_eligible"


def test_build_lead_packet_defaults_to_standard_tag_with_no_context():
    packet = build_lead_packet(
        profile=RAVI, metrics=FULL_METRICS, shelf=[], trigger_utterance="apply for Aspire",
        family="loans_cards", seq=1, now=FIXED_NOW,
    )
    assert packet.tag == "standard"
    assert packet.eligibility_context is None


def test_build_lead_packet_carries_exploratory_tag_and_eligibility_context():
    context = {"card_id": "idbi_imperium_platinum", "status": "needs_more_data", "reason": "Please confirm an eligible IDBI Fixed Deposit."}
    packet = build_lead_packet(
        profile=RAVI, metrics=FULL_METRICS, shelf=[], trigger_utterance="which card should I get",
        family="loans_cards", seq=1, now=FIXED_NOW,
        tag="exploratory_not_yet_eligible", eligibility_context=context,
    )
    assert packet.tag == "exploratory_not_yet_eligible"
    assert packet.eligibility_context == context


def test_build_lead_packet_goals_absent_means_has_goals_false_in_priority():
    metrics_no_goals = dict(FULL_METRICS)
    metrics_no_goals["goals"] = []
    with_goals_score = build_lead_packet(
        profile=RAVI, metrics=FULL_METRICS, shelf=[], trigger_utterance="x",
        family="investment_insurance", seq=1, now=FIXED_NOW,
    ).priority_score
    without_goals_score = build_lead_packet(
        profile=RAVI, metrics=metrics_no_goals, shelf=[], trigger_utterance="x",
        family="investment_insurance", seq=1, now=FIXED_NOW,
    ).priority_score
    assert with_goals_score > without_goals_score
