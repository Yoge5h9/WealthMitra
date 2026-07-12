"""Never-dead-end product surfacing + net-worth grounding.

Real customers asking to invest, open an FD, or see "what premium options"
they have must always get a real, catalogue-sourced product — never "no
options available" — and a net-worth ask must always state the computed
figure, never deflect to a glossary definition. See CLAUDE.md §12 (2026-07-12
"Fix the WealthMitra backend so product/investment asks NEVER dead-end").
"""

from datetime import datetime, timezone

import pytest
from agent_fakes import FakeGateway, call, resp

from app.agent import prompts
from app.agent.orchestrator import Orchestrator
from app.catalogue import eligible_shelf
from app.core import audit
from app.core.spaces import get_space_store
from app.domain.models import PersonaProfile

_NOW = datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)


@pytest.fixture
def space():
    store = get_space_store()
    return store.get(store.create_space())

_DEAD_END_PHRASES = (
    "no products", "no options", "nothing available", "not seeing any", "don't have any options",
)


def _no_dead_end(text: str) -> None:
    lowered = text.lower()
    for phrase in _DEAD_END_PHRASES:
        assert phrase not in lowered, f"dead-end phrase leaked into reply: {phrase!r} in {text!r}"


def make_session(space, persona_id, language="en") -> str:
    session_id = f"sess_{persona_id}_surfacing"
    space.sessions[session_id] = {
        "persona_id": persona_id, "language": language, "history": [],
        "created_at": _NOW.isoformat(),
    }
    return session_id


def run(space, session_id, message, script, language=None):
    fake = FakeGateway(script)
    orch = Orchestrator(fake, now=lambda: _NOW)
    frames = list(orch.run_turn(space, session_id, message, language))
    return frames, fake


def reply_text(frames) -> str:
    return "".join(f["text"] for f in frames if f["type"] == "token")


def system_content(fake) -> str:
    return fake.requests[0].messages[0].content


# --- shelf/net-worth grounding is always present in the prompt --------------


def test_shelf_context_block_is_non_empty_for_every_segment_band_except_suppressed():
    from app.catalogue import RISK_BANDS, CATALOGUE

    for segment in CATALOGUE.segments():
        for band in RISK_BANDS:
            shelf = eligible_shelf(segment, band)
            if not shelf:
                continue  # only senior/growth, and that is the documented suppression
            block = prompts.shelf_context_block(shelf)
            assert block, f"({segment}, {band}) produced no shelf context block"
            assert "ELIGIBLE PRODUCTS" in block


_RAVI = PersonaProfile(
    id="ravi", name="Ravi Kumar", age=28, city="Mumbai", segment="mass_retail_salaried",
    language="en", risk_tolerance="moderate", dependents=0, occupation="Software Engineer",
    avatar="", story="x",
)


def test_system_prompt_never_says_no_products_instruction_and_grounds_real_shelf():
    shelf = eligible_shelf("mass_retail_salaried", "moderate")
    text = prompts.system_prompt(_RAVI, "mass_retail_salaried", "en", "info_only", shelf=shelf)

    assert "NEVER tell the customer there are no products" in text
    for product in shelf:
        assert product.name in text


def test_system_prompt_marks_regulated_items_as_specialist_rm_only():
    shelf = eligible_shelf("hni", "growth")  # pms, aif, insurance_ulip — all regulated
    text = prompts.system_prompt(_RAVI, "hni", "en", "rm_lead", shelf=shelf)

    for product in shelf:
        assert product.name in text
    assert "connect an RM" in text


def test_net_worth_context_line_states_figure_and_mentions_aa_when_unconnected():
    line = prompts.net_worth_context_line(
        {"internal": 125173.0, "external": 0.0, "total": 125173.0, "external_connected": False},
        aa_available=True,
    )
    assert "1,25,173" in line
    assert "Account Aggregator" in line


def test_net_worth_context_line_omits_aa_pitch_when_not_available():
    line = prompts.net_worth_context_line(
        {"internal": 68658.0, "external": 0.0, "total": 68658.0, "external_connected": False},
        aa_available=False,
    )
    assert "68,658" in line
    assert "Account Aggregator" not in line


# --- end-to-end: real turns never dead-end -----------------------------------


def test_open_an_fd_auto_executes_with_a_real_fd_even_off_the_deposit_band(space):
    # ravi's own risk band is "moderate", whose matrix cell holds no deposit
    # product — before the fix this fell through to info_only with nothing to
    # execute. An FD must always be offerable regardless of growth appetite.
    sid = make_session(space, "ravi")
    frames, fake = run(space, sid, "I want to open an FD", [
        resp(tool_calls=[call("request_execution", {"product_id": "fd_regular", "amount": 10000})]),
        resp(text="I can set up the IDBI Regular Fixed Deposit for ₹10,000. Confirm below."),
    ])

    assert fake.requests[0].task_class == "conversational"
    assert "IDBI Regular Fixed Deposit" in system_content(fake)
    text = reply_text(frames)
    _no_dead_end(text)
    assert "IDBI Regular Fixed Deposit" in text
    confirm = next(f["card"] for f in frames if f["type"] == "card" and f["card"]["card_type"] == "execution_confirm")
    assert confirm["product_id"] == "fd_regular"


def test_what_can_i_invest_in_surfaces_a_real_product_info_only(space):
    sid = make_session(space, "ravi")
    frames, fake = run(space, sid, "what can I invest in?", [
        resp(text=(
            "You could start an Index Fund SIP (Direct Plan) with as little as ₹500 a month, "
            "or an ELSS Tax-Saver Fund if you want the Section 80C benefit too."
        )),
    ])

    shelf_names = {p.name for p in eligible_shelf("mass_retail_salaried", "moderate")}
    assert any(name in system_content(fake) for name in shelf_names)
    text = reply_text(frames)
    _no_dead_end(text)
    assert any(name in text for name in shelf_names)


def test_hni_premium_options_ask_routes_to_rm_and_names_a_specialist_product(space):
    # devika's real shelf at her computed (hni, moderate) cell is entirely
    # regulated (wealth_advisory, mf_active_equity, insurance_health,
    # insurance_general) — before the fix, `_representative_product` returned
    # None for an all-regulated shelf and this silently fell through to
    # info_only instead of the RM hand-off.
    sid = make_session(space, "devika")
    frames, fake = run(space, sid, "what premium investment options do I have?", [
        resp(text=(
            "Given your profile, our IDBI Capital Wealth Management desk would be the right fit for a "
            "concentrated, professionally managed approach. A Relationship Manager will review this with you — "
            "nothing here is executed automatically."
        )),
    ])

    routing = [e for e in audit.for_session(space, sid) if e.kind == "routing" and "path" in e.outputs_summary]
    assert routing[0].outputs_summary["path"] == "rm_lead"
    assert space.leads and space.leads[0].family == "investment_insurance"
    assert "IDBI Capital Wealth Management" in system_content(fake)
    text = reply_text(frames)
    _no_dead_end(text)
    assert "wealth management" in text.lower()


def test_invest_my_idle_cash_never_dead_ends(space):
    sid = make_session(space, "meera")  # affluent, growth band
    frames, fake = run(space, sid, "invest my idle cash", [
        resp(text=(
            "Our Actively Managed Equity Fund fits your growth appetite well — a Relationship Manager will walk "
            "you through it before anything is set up."
        )),
    ])
    text = reply_text(frames)
    _no_dead_end(text)


def test_gujarati_invest_request_never_dead_ends(space):
    sid = make_session(space, "arjun", language="gu")  # nri, moderate band, both vanilla
    frames, fake = run(space, sid, "મારે રોકાણ કરવું છે", [
        resp(tool_calls=[call("get_cash_flow")]),
        resp(text="તમે Index Fund SIP થી શરૂઆત કરી શકો છો, જે તમારા માટે યોગ્ય છે."),
    ], language="gu")

    text = reply_text(frames)
    _no_dead_end(text)
    assert "Gujarati" in system_content(fake)


def test_distress_persona_invest_ask_still_suppresses_selling(space):
    sid = make_session(space, "vikram")
    frames, fake = run(space, sid, "I want to invest in a sip", [
        resp(text="Let's first find you some breathing room before we talk about investing."),
    ])
    routing = [e for e in audit.for_session(space, sid) if e.kind == "routing" and "path" in e.outputs_summary]
    assert routing[0].outputs_summary["path"] == "distress_suppress"
    assert space.leads == []
    # distress mode must not get a product shelf injected — no selling context at all
    assert "ELIGIBLE PRODUCTS" not in system_content(fake)


# --- net worth always states the real figure, never a definition-only deflect


def test_net_worth_question_gets_real_figure_not_literacy_deflection(space):
    sid = make_session(space, "ravi")
    frames, fake = run(space, sid, "what is my net worth?", [
        resp(tool_calls=[call("get_net_worth")]),
        resp(text="Right now your net worth is ₹1,25,173, all held within IDBI since your other accounts aren't linked yet."),
    ])

    assert fake.requests[0].task_class != "literacy"
    assert "1,25,173" in system_content(fake)
    text = reply_text(frames)
    assert "1,25,173" in text
    assert "is the total value of" not in text.lower()  # not a bare dictionary definition


def test_net_worth_question_for_unconnected_aa_persona_states_figure_and_offers_aa(space):
    sid = make_session(space, "arjun")  # nri, aa_available True, not connected
    frames, fake = run(space, sid, "what do I have?", [
        resp(tool_calls=[call("get_net_worth")]),
        resp(text=(
            "From your IDBI accounts alone, you have ₹5,47,386 today. Linking your other accounts through "
            "Account Aggregator would give you the complete picture."
        )),
    ])
    assert "5,47,386" in system_content(fake)
    assert "Account Aggregator" in system_content(fake)
    text = reply_text(frames)
    assert "5,47,386" in text
