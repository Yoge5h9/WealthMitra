from __future__ import annotations

import pytest

from app.domain.models import Product
from app.routing.engine import Route, decide, priority_score, wants_to_buy
from app.routing.intents import classify_intent

VANILLA = Product(
    id="fd_1yr", name="1-Year Fixed Deposit", tag="vanilla", category="deposit",
    min_amount=1000, expected_return="7.1% p.a.", description="Retail FD.",
)
REGULATED = Product(
    id="flexicap_mf", name="Flexicap Growth Fund", tag="regulated", category="mutual_fund",
    min_amount=500, expected_return="market-linked", description="Actively-managed equity MF.",
)


# --- wants_to_buy -----------------------------------------------------------

def test_wants_to_buy_true_for_buy_intents():
    for intent in ("invest_surplus", "goal_set", "regulated_query", "fd_query"):
        assert wants_to_buy(intent) is True


def test_wants_to_buy_false_for_non_buy_intents():
    for intent in ("spend_query", "distress_signal", "literacy", "aa_connect", "greeting", "other"):
        assert wants_to_buy(intent) is False


# --- decide: distress_suppress branch ---------------------------------------

def test_distress_flag_with_buy_intent_suppresses():
    route = decide("invest_surplus", ["emi_stressed"], None)
    assert route.path == "distress_suppress"
    assert route.lead_family is None
    assert "distress_flag_present" in route.reasons


def test_overdraft_flag_with_buy_intent_suppresses():
    route = decide("fd_query", ["overdraft"], VANILLA)
    assert route.path == "distress_suppress"


def test_distress_overrides_regulated_product_and_intent():
    # Distress must win even when the product/intent would otherwise route to
    # an RM lead — a distressed customer never gets a sales prompt.
    route = decide("regulated_query", ["emi_stressed", "overdraft"], REGULATED)
    assert route.path == "distress_suppress"


def test_distress_flag_non_buy_intent_no_product_stays_info_only():
    # A distressed customer asking a non-buy question with nothing to sell in
    # the turn still gets served — suppression targets selling, not talking.
    route = decide("spend_query", ["emi_stressed"], None)
    assert route.path == "info_only"


def test_distress_flag_non_buy_intent_with_vanilla_product_suppresses():
    # Reviewer-found gap: an attached product is itself a sales opportunity, so
    # distress flags must suppress it even when the intent is not a buy intent.
    route = decide("spend_query", ["emi_stressed"], VANILLA)
    assert route.path == "distress_suppress"
    assert any("product_attached" in r for r in route.reasons)


def test_distress_flag_non_buy_intent_with_regulated_product_suppresses():
    route = decide("literacy", ["overdraft"], REGULATED)
    assert route.path == "distress_suppress"


def test_distress_signal_intent_always_suppresses_without_flags():
    # Reviewer-found gap: an explicit distress utterance suppresses on its own,
    # even with no behaviour flags and no product.
    route = decide("distress_signal", [], None)
    assert route.path == "distress_suppress"
    assert "distress_signal_intent" in route.reasons


def test_distress_signal_intent_with_vanilla_product_suppresses():
    route = decide("distress_signal", [], VANILLA)
    assert route.path == "distress_suppress"


def test_distress_signal_intent_with_regulated_product_suppresses():
    route = decide("distress_signal", [], REGULATED)
    assert route.path == "distress_suppress"


def test_distress_signal_intent_with_flags_suppresses():
    route = decide("distress_signal", ["emi_stressed"], None)
    assert route.path == "distress_suppress"


def test_buy_intent_without_distress_flag_does_not_suppress():
    route = decide("invest_surplus", [], VANILLA)
    assert route.path != "distress_suppress"


def test_unrelated_behaviour_flag_does_not_suppress():
    route = decide("invest_surplus", ["cash_surplus_heavy"], VANILLA)
    assert route.path != "distress_suppress"
    assert route.path == "auto_execute"


# --- decide: rm_lead branch --------------------------------------------------

def test_regulated_intent_with_no_product_routes_to_rm_lead():
    route = decide("regulated_query", [], None)
    assert route.path == "rm_lead"
    assert route.lead_family == "investment_insurance"
    assert not any("regulated_product" in r for r in route.reasons)


def test_regulated_product_with_non_regulated_intent_routes_to_rm_lead():
    route = decide("spend_query", [], REGULATED)
    assert route.path == "rm_lead"
    assert route.lead_family == "investment_insurance"
    assert any("regulated_product" in r for r in route.reasons)


def test_regulated_intent_and_regulated_product_routes_to_rm_lead():
    route = decide("regulated_query", [], REGULATED)
    assert route.path == "rm_lead"


# --- decide: rm_handoff branch (explicit RM-connect request) -----------------

def test_rm_handoff_wants_to_buy():
    assert wants_to_buy("rm_handoff") is True


def test_rm_handoff_defaults_to_investment_insurance_family():
    route = decide("rm_handoff", [], None)
    assert route.path == "rm_lead"
    assert route.lead_family == "investment_insurance"
    assert "explicit_rm_handoff_request" in route.reasons


def test_rm_handoff_uses_loans_cards_family_when_card_conversation_open():
    route = decide("rm_handoff", [], None, card_conversation_open=True)
    assert route.path == "rm_lead"
    assert route.lead_family == "loans_cards"


def test_distress_flag_suppresses_rm_handoff():
    route = decide("rm_handoff", ["emi_stressed"], None)
    assert route.path == "distress_suppress"


def test_distress_signal_beats_rm_handoff_even_with_card_conversation_open():
    route = decide("distress_signal", [], None, card_conversation_open=True)
    assert route.path == "distress_suppress"


# --- decide: auto_execute branch --------------------------------------------

def test_vanilla_product_with_vanilla_intent_auto_executes():
    route = decide("invest_surplus", [], VANILLA)
    assert route.path == "auto_execute"
    assert route.lead_family is None
    assert any("vanilla_product" in r for r in route.reasons)


def test_vanilla_product_with_info_intent_auto_executes():
    route = decide("fd_query", [], VANILLA)
    assert route.path == "auto_execute"


# --- decide: info_only branch ------------------------------------------------

def test_no_product_non_regulated_intent_is_info_only():
    assert decide("literacy", [], None).path == "info_only"


def test_no_product_greeting_is_info_only():
    assert decide("greeting", [], None).path == "info_only"


def test_route_is_a_pydantic_model_with_expected_fields():
    route = Route(path="info_only")
    assert route.lead_family is None
    assert route.reasons == []


# --- hard invariant: regulated phrasings NEVER auto-execute -----------------
# Same 21-phrase x 7-category regression matrix as test_intents_routing.py,
# but exercised end-to-end through classify_intent -> decide with a vanilla
# product attached (the failure mode this guards: a vanilla product silently
# riding along on a regulated query must not slip through to auto_execute).
_REGULATED_MATRIX = [
    ("en", "should I invest in equity mutual funds?"),
    ("hi", "क्या इक्विटी फंड में निवेश करूँ?"),
    ("gu", "શું ઇક્વિટી ફંડમાં રોકાણ કરું?"),
    ("en", "should I take a ulip policy"),
    ("hi", "यूलिप पॉलिसी के बारे में बताओ"),
    ("gu", "યુલિપ પોલિસી વિશે જણાવો"),
    ("en", "I want to buy some PMS structured products"),
    ("hi", "पीएमएस के बारे में बताओ"),
    ("gu", "પીએમએસ વિશે જણાવો"),
    ("en", "tell me about alternative investment funds"),
    ("hi", "एआईएफ में निवेश कैसे करें"),
    ("gu", "એઆઈએફમાં રોકાણ કેવી રીતે કરવું"),
    ("en", "explain structured products to me"),
    ("hi", "स्ट्रक्चर्ड प्रोडक्ट क्या है"),
    ("gu", "સ્ટ્રક્ચર્ડ પ્રોડક્ટ શું છે"),
    ("en", "is this insurance plan a good investment"),
    ("hi", "क्या यह बीमा एक अच्छा निवेश है"),
    ("gu", "શું આ વીમો સારું રોકાણ છે"),
    ("en", "I want a complex investment strategy"),
    ("hi", "मुझे जटिल निवेश विकल्प चाहिए"),
    ("gu", "મારે જટિલ રોકાણ જોઈએ છે"),
]


@pytest.mark.parametrize("lang,phrase", _REGULATED_MATRIX)
def test_regulated_phrasings_never_auto_execute_with_vanilla_product_attached(lang, phrase):
    intent = classify_intent(phrase, lang)
    route = decide(intent, [], VANILLA)
    assert route.path != "auto_execute"


@pytest.mark.parametrize("lang,phrase", _REGULATED_MATRIX)
def test_regulated_phrasings_never_auto_execute_with_no_product(lang, phrase):
    intent = classify_intent(phrase, lang)
    route = decide(intent, [], None)
    assert route.path != "auto_execute"


def test_regulated_matrix_size_is_21():
    assert len(_REGULATED_MATRIX) == 21


# --- priority_score -----------------------------------------------------------

def test_priority_score_deterministic():
    a = priority_score(monthly_surplus=15000, idle_balance=40000, tolerance_score=60, has_goals=True)
    b = priority_score(monthly_surplus=15000, idle_balance=40000, tolerance_score=60, has_goals=True)
    assert a == b


def test_priority_score_floor_clamp():
    score = priority_score(monthly_surplus=0, idle_balance=0, tolerance_score=0, has_goals=False)
    assert score == 5


def test_priority_score_ceiling_clamp():
    score = priority_score(monthly_surplus=10_000_000, idle_balance=10_000_000, tolerance_score=1000, has_goals=True)
    assert score == 99


def test_priority_score_has_goals_increases_score():
    without_goals = priority_score(monthly_surplus=15000, idle_balance=40000, tolerance_score=60, has_goals=False)
    with_goals = priority_score(monthly_surplus=15000, idle_balance=40000, tolerance_score=60, has_goals=True)
    assert with_goals > without_goals


def test_priority_score_matches_documented_formula():
    # 0.4*min(surplus/1000, 50) + 0.3*(idle/10000) + tolerance/5 + (20 if goals else 0)
    surplus, idle, tolerance = 8000, 25000, 55
    expected_raw = 0.4 * min(surplus / 1000.0, 50.0) + 0.3 * (idle / 10000.0) + tolerance / 5.0 + 0
    expected = max(5, min(99, int(expected_raw)))
    assert priority_score(surplus, idle, tolerance, False) == expected


def test_priority_score_ordering_high_value_persona_outranks_low_value_persona():
    # "meera"/"devika"-style affluent, goal-having, cash-surplus profile must
    # outrank a "ravi"-style low-surplus, no-goals profile.
    ravi_like = priority_score(monthly_surplus=5000, idle_balance=2000, tolerance_score=40, has_goals=False)
    meera_like = priority_score(monthly_surplus=60000, idle_balance=150000, tolerance_score=80, has_goals=True)
    devika_like = priority_score(monthly_surplus=45000, idle_balance=90000, tolerance_score=70, has_goals=True)
    assert meera_like > ravi_like
    assert devika_like > ravi_like
