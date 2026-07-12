"""Nudge engine policy tests (Task 13): quota invariant across every persona,
distress zeroing all selling nudges, AA-gated external triggers, and the
guardrail regeneration-free fallback (a nudge either uses valid LLM copy or
the deterministic template — never a hallucinated figure).
"""

from datetime import datetime, timezone

import pytest
from agent_fakes import FakeGateway, resp

from app.analytics import AnalyticsEngine
from app.core.spaces import get_space_store
from app.nudges import FUNCTIONAL_CAP, generate_nudges
from app.nudges.engine import _collect_functional

_NOW = datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)  # no tax window, no festival window
_FEB = datetime(2026, 2, 10, 10, 0, tzinfo=timezone.utc)

_ALL_PERSONAS = ("vikram", "ravi", "priya", "devika", "meera", "arjun", "shanta")


@pytest.fixture
def space():
    store = get_space_store()
    return store.get(store.create_space())


def _by_kind(nudges):
    functional = [n for n in nudges if n.kind == "functional"]
    relational = [n for n in nudges if n.kind == "relational"]
    return functional, relational


# --- per-persona scenarios named in the brief -----------------------------------


def test_vikram_gets_zero_selling_nudges(space):
    nudges = generate_nudges(space, "vikram", now=_NOW, use_llm=False)
    functional, relational = _by_kind(nudges)
    assert functional, "the protective nudge must still survive distress"
    assert all(n.intent == "protective" for n in functional)
    assert not any(n.intent in ("opportunity", "contextual", "motivational") for n in functional)
    assert relational
    assert len(relational) >= len(functional)


def test_ravi_gets_opportunity_and_relational_at_least_1to1(space):
    nudges = generate_nudges(space, "ravi", now=_NOW, use_llm=False)
    functional, relational = _by_kind(nudges)
    assert any(n.intent == "opportunity" for n in functional)
    assert any("sip_due" in n.id or "idle_balance_high" in n.id for n in functional)
    assert len(relational) >= len(functional)


def test_priya_no_aa_gets_valid_feed_without_external_triggers(space):
    nudges = generate_nudges(space, "priya", now=_NOW, use_llm=False)
    assert nudges
    assert not any("external_refinance" in n.id or "fd_maturity" in n.id for n in nudges)
    for n in nudges:
        assert n.persona_id == "priya"
        assert n.title and n.body


def test_devika_external_refinance_only_once_aa_connected(space):
    before = generate_nudges(space, "devika", now=_NOW, use_llm=False)
    assert not any("external_refinance" in n.id for n in before)

    space.personas["devika"].external.connected = True
    after = generate_nudges(space, "devika", now=_NOW, use_llm=False)
    assert any("external_refinance" in n.id for n in after)


@pytest.mark.parametrize("persona_id", _ALL_PERSONAS)
def test_quota_invariant_holds_for_every_persona(space, persona_id):
    nudges = generate_nudges(space, persona_id, now=_NOW, use_llm=False)
    functional, relational = _by_kind(nudges)
    assert len(functional) <= FUNCTIONAL_CAP
    assert len(relational) >= len(functional)
    assert all(n.persona_id == persona_id for n in nudges)
    assert all(n.language == space.personas[persona_id].profile.language for n in nudges)


def test_tax_window_only_fires_when_clock_says_feb(space):
    persona = space.personas["ravi"]
    metrics = {m.id: m for m in AnalyticsEngine().compute(space, "ravi", now=_NOW)}

    assert not any(c.template_id == "tax_window" for c in _collect_functional(metrics, persona, _NOW))
    assert any(c.template_id == "tax_window" for c in _collect_functional(metrics, persona, _FEB))


# --- guardrail: LLM copy accepted when grounded, falls back when not -----------


def test_llm_hallucination_falls_back_to_deterministic_template(space):
    bad = resp(text="TITLE: You have ₹99,99,999 saved!\nBODY: Incredible progress, invest ₹99,99,999 today!")
    fake = FakeGateway([bad] * 10)
    nudges = generate_nudges(space, "ravi", now=_NOW, use_llm=True, gateway=fake)
    assert nudges
    for n in nudges:
        assert "99,99,999" not in n.title
        assert "99,99,999" not in n.body


def test_llm_grounded_copy_is_accepted(space):
    # ravi's real idle_balance (see test_agent_orchestrator.py) — passes the guardrail.
    good = resp(text="TITLE: Nice cushion building up\nBODY: You have ₹1,25,173 parked and could put some to work.")
    fake = FakeGateway([good] * 10)
    nudges = generate_nudges(space, "ravi", now=_NOW, use_llm=True, gateway=fake)
    assert any(n.title == "Nice cushion building up" for n in nudges)


def test_malformed_llm_response_falls_back(space):
    malformed = resp(text="Sure, here's a notification for you!")  # no TITLE:/BODY: markers
    fake = FakeGateway([malformed] * 10)
    nudges = generate_nudges(space, "ravi", now=_NOW, use_llm=True, gateway=fake)
    assert nudges
    for n in nudges:
        assert n.title and n.body
        assert n.title != "Sure, here's a notification for you!"


# --- determinism / ids -----------------------------------------------------------


def test_ids_are_stable_across_repeated_calls_same_day(space):
    first = generate_nudges(space, "ravi", now=_NOW, use_llm=False)
    second = generate_nudges(space, "ravi", now=_NOW, use_llm=False)
    assert [n.id for n in first] == [n.id for n in second]


def test_ids_change_on_a_different_day(space):
    day1 = generate_nudges(space, "ravi", now=_NOW, use_llm=False)
    day2 = generate_nudges(space, "ravi", now=_NOW.replace(day=13), use_llm=False)
    assert {n.id for n in day1}.isdisjoint({n.id for n in day2})
