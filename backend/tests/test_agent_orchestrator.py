"""Orchestrator turn-pipeline tests with a scripted fake Gateway: the routing
gate fixes the mode before any LLM call, all four modes end-to-end, guardrail
regeneration/fallback, and the mid-session language switch.
"""

from datetime import datetime, timezone

import pytest
from agent_fakes import FakeGateway, call, resp

from app.agent.orchestrator import Orchestrator
from app.catalogue import eligible_shelf
from app.core import audit
from app.core.spaces import get_space_store

_NOW = datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)


@pytest.fixture
def space():
    store = get_space_store()
    return store.get(store.create_space())


def make_session(space, persona_id, language="en") -> str:
    session_id = f"sess_{persona_id}_test"
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


def frame_types(frames):
    return [f["type"] for f in frames]


def cards(frames):
    return [f["card"] for f in frames if f["type"] == "card"]


def reply_text(frames):
    return "".join(f["text"] for f in frames if f["type"] == "token")


def routing_entries(space, session_id):
    return [e for e in audit.for_session(space, session_id) if e.kind == "routing"]


def routing_decisions(space, session_id):
    """Only the `decide()` routing entries — excludes the `lead_created`
    audit entry that `kind == "routing"` also covers, so a test can safely
    look at "the routing decision for the most recent turn" across a
    multi-turn conversation.
    """
    return [e for e in routing_entries(space, session_id) if "path" in e.outputs_summary]


# --- mode: info_only --------------------------------------------------------


def test_info_only_grounded_turn(space):
    sid = make_session(space, "ravi")
    frames, fake = run(space, sid, "how is my spending this month?", [
        resp(tool_calls=[call("get_spend_summary")]),
        resp(text="Your monthly income is ₹85,000 and rent is your biggest spend."),
    ])

    assert routing_entries(space, sid)[0].outputs_summary["path"] == "info_only"
    assert frames[0] == {"type": "avatar", "state": "thinking"}
    assert "₹85,000" in reply_text(frames)
    assert cards(frames)[0]["card_type"] == "spend_summary"
    assert frames[-1]["type"] == "done"
    assert frames[-1]["audit_ref"].startswith("aud_")
    # the routing gate ran BEFORE the first LLM call: mode-scoped tools offered
    assert {t.name for t in fake.requests[0].tools} == {
        t.name for t in __import__("app.agent.tools", fromlist=["tools_for_mode"]).tools_for_mode("info_only")
    }


def test_factual_aspire_question_returns_stored_card_facts_without_mf_or_rm(space):
    sid = make_session(space, "arjun")
    frames, fake = run(space, sid, "tell me about the Aspire card", [])

    assert fake.requests == []
    assert space.leads == []
    card = next(card for card in cards(frames) if card["card_type"] == "credit_product_detail")
    assert card["product"]["id"] == "idbi_aspire_platinum"
    assert card["product"]["eligibility"]["status"] == "ineligible"
    assert all(card["card_type"] != "recommendation" for card in cards(frames))


def test_sse_frame_ordering(space):
    sid = make_session(space, "ravi")
    frames, _ = run(space, sid, "how is my spending?", [
        resp(tool_calls=[call("get_spend_summary")]),
        resp(text="Rent leads your spending."),
    ])
    kinds = frame_types(frames)
    assert kinds[0] == "avatar"
    assert kinds[-1] == "done"
    first_token = kinds.index("token")
    first_card = kinds.index("card")
    assert kinds.index("avatar") < first_token < first_card < kinds.index("done")


def test_tool_loop_caps_at_six_rounds(space):
    sid = make_session(space, "ravi")
    looping = [resp(tool_calls=[call("get_cash_flow")], text=None) for _ in range(10)]
    frames, fake = run(space, sid, "how is my spending?", looping)
    assert len(fake.requests) == 6  # hard cap: no seventh tool round
    assert frames[-1]["type"] == "done"


# --- mode: auto_execute -----------------------------------------------------


def test_auto_execute_prepares_confirm_never_executes(space):
    sid = make_session(space, "ravi")
    product = next(p for p in eligible_shelf("mass_retail_salaried", "moderate", monthly_surplus=20862.0)
                   if p.tag == "vanilla")
    frames, fake = run(space, sid, "I want to invest my surplus", [
        resp(tool_calls=[call("get_cash_flow")]),
        resp(tool_calls=[call("request_execution", {"product_id": product.id, "amount": 5000})]),
        resp(text=f"I can set up {product.name} for ₹5,000 a month. Confirm below."),
    ])

    assert routing_entries(space, sid)[0].outputs_summary["path"] == "auto_execute"
    card_types = [c["card_type"] for c in cards(frames)]
    assert "execution_confirm" in card_types
    confirm = next(c for c in cards(frames) if c["card_type"] == "execution_confirm")
    assert confirm["confirm_token"].startswith("cfm_")
    assert confirm["product_id"] == product.id
    assert space.leads == []  # vanilla path never creates a lead
    assert {"type": "avatar", "state": "celebrating"} in frames
    exec_entries = [e for e in audit.for_session(space, sid) if e.kind == "execution"]
    assert exec_entries == []  # nothing executed


def test_auto_execute_tools_exclude_create_rm_lead(space):
    sid = make_session(space, "ravi")
    _, fake = run(space, sid, "I want to invest my surplus", [resp(text="Happy to help.")])
    names = {t.name for t in fake.requests[0].tools}
    assert "create_rm_lead" not in names
    assert "request_execution" in names


# --- mode: rm_lead ----------------------------------------------------------


def test_rm_lead_builds_packet_deterministically(space):
    sid = make_session(space, "meera", language="gu")
    frames, fake = run(space, sid, "I want to invest in equity mutual funds", [
        resp(text="Our specialist will reach out to you shortly."),
    ])

    assert routing_entries(space, sid)[0].outputs_summary["path"] == "rm_lead"
    assert len(space.leads) == 1
    lead = space.leads[0]
    assert lead.lead_id == "LP-2026-000001"
    assert lead.family == "investment_insurance"
    assert lead.customer["persona_id"] == "meera"
    assert lead.trigger["utterance"] == "I want to invest in equity mutual funds"
    assert 5 <= lead.priority_score <= 99
    # LLM only narrates: lead exists BEFORE any model call, via lead_narrative
    assert fake.requests[0].task_class == "lead_narrative"
    card = next(c for c in cards(frames) if c["card_type"] == "routed_to_rm")
    assert card["lead_id"] == lead.lead_id
    lead_audits = [e for e in routing_entries(space, sid) if e.name == "lead_created"]
    assert lead_audits and lead_audits[0].session_id == sid


def test_rm_lead_tools_exclude_request_execution(space):
    sid = make_session(space, "devika")
    _, fake = run(space, sid, "tell me about PMS", [resp(text="A specialist will call you.")])
    assert routing_entries(space, sid)[0].outputs_summary["path"] == "rm_lead"
    names = {t.name for t in fake.requests[0].tools}
    assert "request_execution" not in names
    assert "create_rm_lead" in names


def test_ineligible_card_application_reaches_dynamic_loop_and_creates_no_lead(space):
    # Named-card "apply" phrasing still routes to rm_lead/loans_cards, but now
    # runs through the same dynamic loop as any other card query: the model
    # must call evaluate_card_eligibility itself rather than the turn being
    # short-circuited before any LLM call.
    sid = make_session(space, "arjun")
    frames, fake = run(space, sid, "I want to apply for Aspire card", [
        resp(tool_calls=[call("evaluate_card_eligibility")]),
        resp(text=(
            "The Aspire Platinum is set up for India-resident profiles, so as an NRI it wouldn't fit you — I "
            "don't want to set the wrong expectation. The Imperium Platinum, secured against an IDBI FD/FCNR "
            "deposit, is a real alternative. Would you like a Relationship Manager to review that path?"
        )),
    ])
    assert routing_entries(space, sid)[0].outputs_summary["path"] == "rm_lead"
    assert space.leads == []
    names = {t.name for t in fake.requests[0].tools}
    assert "evaluate_card_eligibility" in names
    assert "get_eligible_products" not in names
    text = reply_text(frames)
    assert "imperium" in text.lower()


def test_preeligible_card_application_creates_exactly_one_rm_lead(space):
    sid = make_session(space, "ravi")
    frames, _ = run(space, sid, "I want to apply for Aspire card", [
        resp(tool_calls=[call("evaluate_card_eligibility")]),
        resp(tool_calls=[call("create_rm_lead", {"trigger_utterance": "apply for Aspire card", "card_id": "idbi_aspire_platinum"})]),
        resp(text="Done — an RM will review your Aspire Platinum application. This is not an approval."),
    ])

    assert len(space.leads) == 1
    assert space.leads[0].family == "loans_cards"
    assert space.leads[0].tag == "standard"
    routed = next(card for card in cards(frames) if card["card_type"] == "routed_to_rm")
    assert routed["lead_id"] == space.leads[0].lead_id


# --- mode: rm_lead / loans_cards family (the dynamic card conversation) -----


def test_card_query_with_unknown_need_asks_one_clarifying_question(space):
    sid = make_session(space, "ravi")
    frames, fake = run(space, sid, "I want a credit card", [
        resp(text="Happy to help — what matters most to you: everyday rewards, travel, or a big purchase?"),
    ])
    assert routing_entries(space, sid)[0].outputs_summary["path"] == "rm_lead"
    assert space.leads == []
    assert "pending_credit" not in space.sessions[sid]
    assert reply_text(frames).strip().endswith("?")
    names = {t.name for t in fake.requests[0].tools}
    assert "evaluate_card_eligibility" in names
    assert "get_eligible_products" not in names


def test_nri_card_query_runs_empathy_flow_with_alternative_and_creates_no_lead(space):
    sid = make_session(space, "arjun")
    frames, fake = run(space, sid, "which credit card should I get", [
        resp(tool_calls=[call("evaluate_card_eligibility")]),
        resp(text=(
            "Those cards are set up for India-resident profiles, so as an NRI they wouldn't fit you — I don't "
            "want to set the wrong expectation. There is a real alternative: the IDBI Imperium Platinum secured "
            "against an IDBI FD/FCNR deposit. Would you like a Relationship Manager to review that path for you?"
        )),
    ])
    assert routing_entries(space, sid)[0].outputs_summary["path"] == "rm_lead"
    assert space.leads == []
    text = reply_text(frames).lower()
    assert "resident" in text or "nri" in text
    assert "imperium" in text
    assert "relationship manager" in text or " rm " in f" {text} "
    assert space.sessions[sid]["card_mode_open"] is True
    verdicts = fake.requests[0]
    assert {t.name for t in verdicts.tools} == {t.name for t in
        __import__("app.agent.tools", fromlist=["tools_for_mode"]).tools_for_mode("rm_lead", family="loans_cards")}


def test_nri_card_consent_on_the_next_turn_creates_exactly_one_exploratory_lead(space):
    sid = make_session(space, "arjun")
    run(space, sid, "which credit card should I get", [
        resp(tool_calls=[call("evaluate_card_eligibility")]),
        resp(text="Those unsecured cards need India residency, so they wouldn't fit you. The Imperium Platinum, "
                  "secured against an IDBI FD/FCNR deposit, is a real alternative — want an RM to review it?"),
    ])
    assert space.sessions[sid]["card_mode_open"] is True

    frames, fake = run(space, sid, "Yes please", [
        resp(tool_calls=[call("create_rm_lead", {"trigger_utterance": "Imperium secured card, NRI", "card_id": "idbi_imperium_platinum"})]),
        resp(text="Done — an RM will review the Imperium Platinum secured-card path with you. This is not an approval."),
    ])

    assert len(space.leads) == 1
    lead = space.leads[0]
    assert lead.family == "loans_cards"
    assert lead.tag == "exploratory_not_yet_eligible"
    assert lead.eligibility_context["card_id"] == "idbi_imperium_platinum"
    assert "not an approval" in reply_text(frames).lower()
    # a single continuation turn is consumed; the flag never lingers open
    assert space.sessions[sid].get("card_mode_open") is not True
    # the "yes" follow-up reused the SAME card toolset, not the info_only default
    names = {t.name for t in fake.requests[0].tools}
    assert "create_rm_lead" in names and "evaluate_card_eligibility" in names


def test_nri_card_decline_on_the_next_turn_creates_no_lead(space):
    sid = make_session(space, "arjun")
    run(space, sid, "which credit card should I get", [
        resp(tool_calls=[call("evaluate_card_eligibility")]),
        resp(text="Those unsecured cards need India residency, so they wouldn't fit you. The Imperium Platinum, "
                  "secured against an IDBI FD/FCNR deposit, is a real alternative — want an RM to review it?"),
    ])

    frames, fake = run(space, sid, "No thanks", [
        resp(text="No problem — happy to help with anything else about your accounts whenever you're ready."),
    ])

    assert space.leads == []
    assert space.sessions[sid].get("card_mode_open") is not True


def test_resident_eligible_card_query_shortlist_then_consent_creates_one_standard_lead(space):
    sid = make_session(space, "priya")
    _, fake1 = run(space, sid, "I want a credit card, mainly for everyday rewards", [
        resp(tool_calls=[call("evaluate_card_eligibility")]),
        resp(text="Based on your profile, the IDBI Aspire Platinum is a preliminary match for everyday rewards. "
                  "This is not an approval. Would you like an RM to review it?"),
    ])
    assert space.leads == []
    assert space.sessions[sid]["card_mode_open"] is True
    names = {t.name for t in fake1.requests[0].tools}
    assert "get_eligible_products" not in names  # never the investment shelf in card mode

    frames2, _ = run(space, sid, "Yes", [
        resp(tool_calls=[call("create_rm_lead", {"trigger_utterance": "Aspire, everyday rewards", "card_id": "idbi_aspire_platinum"})]),
        resp(text="Done — an RM will review the Aspire Platinum application with you."),
    ])
    assert len(space.leads) == 1
    lead = space.leads[0]
    assert lead.tag == "standard"
    assert lead.family == "loans_cards"
    routed = next(c for c in cards(frames2) if c["card_type"] == "routed_to_rm")
    assert routed["lead_id"] == lead.lead_id


def test_distress_persona_card_query_suppresses_selling_no_shortlist_no_lead(space):
    sid = make_session(space, "vikram")
    frames, fake = run(space, sid, "which credit card should I get", [
        resp(text="Let's first get your cash-flow steady before we talk about a new card."),
    ])
    assert routing_entries(space, sid)[0].outputs_summary["path"] == "distress_suppress"
    assert space.leads == []
    names = {t.name for t in fake.requests[0].tools}
    assert names.isdisjoint({"evaluate_card_eligibility", "create_rm_lead"})
    assert [c["card_type"] for c in cards(frames)] == ["distress_support"]
    assert "card_mode_open" not in space.sessions[sid]


# --- mode: distress_suppress ------------------------------------------------


def test_distress_removes_product_tools_and_emits_support_card(space):
    sid = make_session(space, "vikram")
    frames, fake = run(space, sid, "I can't pay my EMI this month", [
        resp(text="I'm sorry it's tough right now. Let's look at this together."),
    ])

    assert routing_entries(space, sid)[0].outputs_summary["path"] == "distress_suppress"
    names = {t.name for t in fake.requests[0].tools}
    assert names.isdisjoint({"get_eligible_products", "compare_products", "request_execution", "create_rm_lead"})
    assert [c["card_type"] for c in cards(frames)] == ["distress_support"]
    assert {"type": "avatar", "state": "concerned"} in frames
    assert space.leads == []


def test_distress_flag_plus_buy_intent_suppresses(space):
    # vikram carries emi_stressed/overdraft flags; a buy-intent message must
    # suppress even without explicit distress wording.
    sid = make_session(space, "vikram")
    frames, _ = run(space, sid, "I want to invest in a sip", [resp(text="Let's first find you breathing room.")])
    assert routing_entries(space, sid)[0].outputs_summary["path"] == "distress_suppress"
    assert [c["card_type"] for c in cards(frames)] == ["distress_support"]


def test_distress_tool_call_attempt_is_refused_not_crashed(space):
    sid = make_session(space, "vikram")
    frames, fake = run(space, sid, "I missed my EMI, what now?", [
        resp(tool_calls=[call("get_eligible_products")]),  # model misbehaves
        resp(text="Let's review your cash-flow together."),
    ])
    tool_msg = fake.requests[1].messages[-1]
    assert tool_msg.role == "tool"
    assert "error" in (tool_msg.content or "")
    refusals = [e for e in audit.for_session(space, sid)
                if e.kind == "guardrail" and e.name.startswith("tool_refused")]
    assert refusals
    assert frames[-1]["type"] == "done"


# --- BUG1: no internal jargon leaks into customer-facing output -------------

_JARGON_TERMS = ("suitability matrix", "eligible shelf", "'hni'", "pre-eligibility", "mass_retail", "demo")


def test_recommendation_card_and_reply_are_jargon_free(space):
    sid = make_session(space, "ravi")
    frames, _ = run(space, sid, "how is my spending?", [
        resp(tool_calls=[call("get_eligible_products")]),
        resp(text="Based on your surplus, a fixed deposit ladder could work well for you."),
    ])
    rec = next(c for c in cards(frames) if c["card_type"] == "recommendation")
    blob = (reply_text(frames) + " " + " ".join(rec["why"])).lower()
    for term in _JARGON_TERMS:
        assert term not in blob, f"jargon leaked: {term!r}"


def test_factual_card_question_reply_is_jargon_free(space):
    sid = make_session(space, "ravi")
    frames, fake = run(space, sid, "tell me about the Aspire card", [])
    assert fake.requests == []  # static path, no LLM involved
    card = next(c for c in cards(frames) if c["card_type"] == "credit_product_detail")
    assert card["product"]["eligibility"]["status"] == "eligible"
    blob = (reply_text(frames) + " " + " ".join(card["product"]["reasons"])).lower()
    for term in _JARGON_TERMS:
        assert term not in blob, f"jargon leaked: {term!r}"


def test_system_prompt_forbids_internal_jargon_for_every_customer_mode():
    from app.agent import prompts
    from app.domain.models import PersonaProfile

    profile = PersonaProfile(
        id="ravi", name="Ravi Kumar", age=28, city="Mumbai", segment="mass_retail_salaried",
        language="en", risk_tolerance="moderate", dependents=0, occupation="Software Engineer",
        avatar="", story="x",
    )
    for mode in ("info_only", "auto_execute", "rm_lead", "distress_suppress"):
        text = prompts.system_prompt(profile, "mass_retail_salaried", "en", mode).lower()
        assert "never expose internal terms" in text
        assert "suitability matrix" in text
    card_prompt = prompts.system_prompt(
        profile, "mass_retail_salaried", "en", "rm_lead", lead_family="loans_cards", card_context={},
    ).lower()
    assert "never expose internal terms" in card_prompt


# --- BUG2: a card conversation survives a non-affirmative follow-up ---------


def test_card_followup_stating_use_case_stays_in_card_mode(space):
    sid = make_session(space, "ravi")
    run(space, sid, "I want a credit card", [
        resp(text="Happy to help — what matters most to you: everyday rewards, travel, or a big purchase?"),
    ])
    assert space.sessions[sid]["card_mode_open"] is True

    frames, fake = run(space, sid, "for everyday spend", [
        resp(tool_calls=[call("evaluate_card_eligibility")]),
        resp(text="Based on your profile, the IDBI Aspire Platinum fits everyday spend well. This is not an "
                  "approval. Would you like an RM to review it?"),
    ])
    names = {t.name for t in fake.requests[0].tools}
    assert "evaluate_card_eligibility" in names
    assert "get_eligible_products" not in names
    text = reply_text(frames).lower()
    assert "no card" not in text and "no eligible" not in text
    assert space.leads == []
    assert space.sessions[sid]["card_mode_open"] is True


def test_card_followup_pick_for_me_stays_in_card_mode(space):
    sid = make_session(space, "ravi")
    run(space, sid, "I want a credit card", [
        resp(text="Happy to help — what matters most to you: everyday rewards, travel, or a big purchase?"),
    ])
    frames, fake = run(space, sid, "go ahead pick one for me", [
        resp(tool_calls=[call("evaluate_card_eligibility")]),
        resp(text="Based on your profile, the IDBI Aspire Platinum is a preliminary match. Would you like an RM "
                  "to review it?"),
    ])
    names = {t.name for t in fake.requests[0].tools}
    assert "evaluate_card_eligibility" in names
    assert "get_eligible_products" not in names
    assert space.leads == []
    assert space.sessions[sid]["card_mode_open"] is True


def test_card_followup_switching_to_a_different_topic_leaves_card_mode(space):
    sid = make_session(space, "ravi")
    run(space, sid, "I want a credit card", [
        resp(text="Happy to help — what matters most to you: everyday rewards, travel, or a big purchase?"),
    ])
    frames, fake = run(space, sid, "actually tell me about mutual funds", [
        resp(text="A specialist Relationship Manager will follow up with you about mutual funds."),
    ])
    last_decision = routing_decisions(space, sid)[-1]
    assert last_decision.outputs_summary["path"] == "rm_lead"
    assert last_decision.outputs_summary["lead_family"] == "investment_insurance"
    names = {t.name for t in fake.requests[0].tools}
    assert "evaluate_card_eligibility" not in names
    assert space.sessions[sid].get("card_mode_open") is not True


# --- BUG3: an explicit RM-handoff request creates + persists a lead ---------


def test_explicit_rm_handoff_creates_investment_lead(space):
    sid = make_session(space, "devika")
    run(space, sid, "how is my spending?", [
        resp(tool_calls=[call("get_spend_summary")]),
        resp(text="Your biggest spend category is business supplies."),
    ])
    assert space.leads == []

    frames, fake = run(space, sid, "go ahead with rm", [
        resp(text="A specialist Relationship Manager will follow up with you shortly."),
    ])
    assert routing_decisions(space, sid)[-1].outputs_summary["path"] == "rm_lead"
    assert len(space.leads) == 1
    lead = space.leads[0]
    assert lead.family == "investment_insurance"
    assert fake.requests[0].task_class == "lead_narrative"  # lead built before any LLM call
    text = reply_text(frames).lower()
    assert "can't" not in text and "cannot" not in text
    assert "approv" not in text  # never implies approval
    card = next(c for c in cards(frames) if c["card_type"] == "routed_to_rm")
    assert card["lead_id"] == lead.lead_id


def test_explicit_rm_handoff_during_open_card_conversation_uses_loans_cards_family(space):
    sid = make_session(space, "ravi")
    run(space, sid, "I want a credit card", [
        resp(text="Happy to help — what matters most to you: everyday rewards, travel, or a big purchase?"),
    ])
    assert space.sessions[sid]["card_mode_open"] is True

    frames, _ = run(space, sid, "connect me to an rm", [
        resp(tool_calls=[call("create_rm_lead", {"trigger_utterance": "connect me to an rm", "card_id": "idbi_aspire_platinum"})]),
        resp(text="Done — an RM will review the Aspire Platinum application with you. This is not an approval."),
    ])
    assert len(space.leads) == 1
    assert space.leads[0].family == "loans_cards"


def test_distress_persona_explicit_rm_handoff_creates_no_lead(space):
    sid = make_session(space, "vikram")
    frames, _ = run(space, sid, "go ahead with rm", [
        resp(text="Let's first get your cash-flow steady before anything else."),
    ])
    assert routing_entries(space, sid)[0].outputs_summary["path"] == "distress_suppress"
    assert space.leads == []


# --- BUG4: a decline deterministically blocks lead creation -----------------


def test_decline_blocks_lead_even_if_model_calls_create_rm_lead_anyway(space):
    sid = make_session(space, "ravi")
    run(space, sid, "I want a credit card", [
        resp(text="Happy to help — what matters most to you: everyday rewards, travel, or a big purchase?"),
    ])
    assert space.sessions[sid]["card_mode_open"] is True

    frames, fake = run(space, sid, "No thanks", [
        resp(tool_calls=[call("create_rm_lead", {"trigger_utterance": "no thanks", "card_id": "idbi_aspire_platinum"})]),
        resp(text="No problem — happy to help with anything else."),
    ])
    assert space.leads == []
    tool_msg = fake.requests[1].messages[-1]
    assert tool_msg.role == "tool"
    assert "error" in (tool_msg.content or "")
    assert space.sessions[sid].get("card_mode_open") is not True


# --- guardrail: regenerate then fall back -----------------------------------


def test_guardrail_violation_triggers_one_regeneration(space):
    sid = make_session(space, "ravi")
    frames, fake = run(space, sid, "how is my spending?", [
        resp(tool_calls=[call("get_cash_flow")]),
        resp(text="You have ₹9,99,999 sitting idle."),      # hallucinated
        resp(text="You have ₹1,25,173 sitting idle."),      # grounded regen
    ])
    assert "₹1,25,173" in reply_text(frames)
    regen_req = fake.requests[-1]
    assert regen_req.tool_choice == "none"
    assert "₹9,99,999" in regen_req.messages[-1].content  # stricter instruction names the violation
    verdicts = [e for e in audit.for_session(space, sid) if e.kind == "guardrail" and e.name == "number_audit"]
    assert [v.outputs_summary["ok"] for v in verdicts] == [False, True]
    assert verdicts[1].outputs_summary["regenerated"] is True


def test_guardrail_double_failure_falls_back_to_safe_template(space):
    sid = make_session(space, "ravi")
    frames, _ = run(space, sid, "how is my spending?", [
        resp(tool_calls=[call("get_cash_flow")]),
        resp(text="You have ₹9,99,999 idle."),
        resp(text="Fine, you have ₹8,88,888 idle."),         # still hallucinating
    ])
    text = reply_text(frames)
    assert "₹20,862" in text and "₹1,25,173" in text         # template figures, Indian grouping
    assert "9,99,999" not in text and "8,88,888" not in text
    verdicts = [e for e in audit.for_session(space, sid) if e.kind == "guardrail" and e.name == "number_audit"]
    assert verdicts[-1].outputs_summary["fell_back"] is True


def test_clean_reply_skips_regeneration(space):
    sid = make_session(space, "ravi")
    _, fake = run(space, sid, "hello there", [resp(text="Hi Ravi! How can I help today?")])
    assert len(fake.requests) == 1


# --- BUG B: a guarantee ask never falls back to the generic evasive dodge ---


def test_guarantee_ask_double_failure_falls_back_to_an_explicit_refusal_not_a_dodge(space):
    # Reproduces the reported failure: the model tries to explain why it
    # can't confirm the customer's own 20% figure, re-mentions "20%" (an
    # unverified number) both times, the guardrail rejects both attempts, and
    # the turn falls back to the safe template. The generic facts-only
    # template ("Here's what I can confirm... I'll connect you with a
    # specialist") neither confirms nor denies a guarantee — it must instead
    # explicitly refuse the guarantee.
    sid = make_session(space, "ravi")
    frames, _ = run(space, sid, "Can you guarantee me 20% returns if I invest right now?", [
        resp(text="Sure, a 20% return is realistic if markets do well."),
        resp(text="I really can't promise 20%, but it could happen."),
    ])
    text = reply_text(frames)
    assert "no one can guarantee" in text.lower()
    assert "20%" not in text
    assert "connect you with a specialist" not in text.lower()
    verdicts = [e for e in audit.for_session(space, sid) if e.kind == "guardrail" and e.name == "number_audit"]
    assert verdicts[-1].outputs_summary["fell_back"] is True


def test_guarantee_ask_first_pass_clean_reply_is_untouched(space):
    # A reply that already refuses cleanly (no unverified numbers) must pass
    # straight through — the guardrail should never rewrite a compliant reply.
    sid = make_session(space, "ravi")
    frames, fake = run(space, sid, "Can you guarantee me 20% returns?", [
        resp(text="No one can guarantee market returns — I can't promise a fixed outcome here."),
    ])
    assert len(fake.requests) == 1
    text = reply_text(frames)
    assert "no one can guarantee" in text.lower()


# --- BUG C: at most one RM lead per (session, lead_family) ------------------


def test_premium_info_question_then_explicit_rm_consent_creates_exactly_one_lead(space):
    # devika's computed (hni, moderate) shelf is entirely regulated, so a pure
    # "what premium options do I have" question already (correctly) routes to
    # rm_lead and opens a lead — see test_agent_product_surfacing.py's
    # test_hni_premium_options_ask_routes_to_rm_and_names_a_specialist_product.
    # A later explicit "go ahead with rm" in the SAME session must reuse that
    # lead, never open a second one.
    sid = make_session(space, "devika")
    run(space, sid, "what premium investment options do I have?", [
        resp(text="Our IDBI Capital Wealth Management desk fits this — an RM will review it with you."),
    ])
    assert len(space.leads) == 1
    first_lead_id = space.leads[0].lead_id

    frames, _ = run(space, sid, "go ahead with rm", [
        resp(text="Understood — your Relationship Manager already has this and will be in touch."),
    ])
    assert len(space.leads) == 1                       # no duplicate
    assert space.leads[0].lead_id == first_lead_id
    routed = next(c for c in cards(frames) if c["card_type"] == "routed_to_rm")
    assert routed["lead_id"] == first_lead_id


def test_distress_persona_never_creates_a_lead_across_repeated_regulated_asks(space):
    sid = make_session(space, "vikram")
    run(space, sid, "what premium investment options do I have?", [
        resp(text="Let's first get your cash-flow steady."),
    ])
    run(space, sid, "go ahead with rm", [
        resp(text="Let's first get your cash-flow steady."),
    ])
    assert space.leads == []


def test_card_empathy_consent_flow_still_creates_exactly_one_lead(space):
    # The loans_cards consent-gated flow (BUG3/BUG4 above) must be unaffected
    # by the investment_insurance dedup guard — it lives in a separate branch.
    sid = make_session(space, "arjun")
    run(space, sid, "which credit card should I get", [
        resp(tool_calls=[call("evaluate_card_eligibility")]),
        resp(text="Those unsecured cards need India residency, so they wouldn't fit you. The Imperium Platinum, "
                  "secured against an IDBI FD/FCNR deposit, is a real alternative — want an RM to review it?"),
    ])
    run(space, sid, "Yes please", [
        resp(tool_calls=[call("create_rm_lead", {"trigger_utterance": "Imperium secured card, NRI", "card_id": "idbi_imperium_platinum"})]),
        resp(text="Done — an RM will review the Imperium Platinum secured-card path with you. This is not an approval."),
    ])
    assert len(space.leads) == 1
    assert space.leads[0].family == "loans_cards"


# --- language + session state -----------------------------------------------


def test_language_switch_mid_session(space):
    sid = make_session(space, "ravi", language="en")
    _, fake = run(space, sid, "मेरा खर्च कैसा है?", [resp(text="आपका खर्च संतुलित है।")], language="hi")
    assert space.sessions[sid]["language"] == "hi"
    assert "Hindi" in fake.requests[0].messages[0].content


def test_history_carries_into_next_turn_and_is_capped(space):
    sid = make_session(space, "ravi")
    for i in range(10):
        run(space, sid, f"question {i}", [resp(text=f"answer {i}")])
    history = space.sessions[sid]["history"]
    assert len(history) == 16  # capped at HISTORY_LIMIT (8 conversational turns)
    assert history[-1]["content"] == "answer 9"

    _, fake = run(space, sid, "one more", [resp(text="noted")])
    contents = [m.content for m in fake.requests[0].messages]
    assert "answer 9" in contents  # prior turn visible to the model


# --- literacy context profile ------------------------------------------------


def test_literacy_intent_gets_literacy_task_class_and_minimal_context(space):
    sid = make_session(space, "ravi")
    frames, fake = run(space, sid, "what is SIP", [
        resp(tool_calls=[call("get_literacy", {"term": "sip"})]),
        resp(text="A SIP invests a fixed amount every month, so you buy more units when prices dip."),
    ])
    assert routing_entries(space, sid)[0].outputs_summary["path"] == "info_only"
    assert fake.requests[0].task_class == "literacy"
    assert fake.requests[1].task_class == "literacy"

    # 1-2 tool subset, not the full info_only registry.
    tool_names = {t.name for t in fake.requests[0].tools}
    assert tool_names == {"get_literacy"}

    # No metrics dump / mode guidance / product rules in the system prompt.
    sys_content = fake.requests[0].messages[0].content
    assert "spend_by_category" not in sys_content
    assert "get_eligible_products" not in sys_content
    assert len(sys_content) < 700  # far smaller than the ~1600-char full prompt
    assert frames[-1]["type"] == "done"


def test_literacy_turn_caps_history_at_two_turns(space):
    sid = make_session(space, "ravi")
    for i in range(3):
        run(space, sid, f"question {i}", [resp(text=f"answer {i}")])

    _, fake = run(space, sid, "what is FD", [
        resp(tool_calls=[call("get_literacy", {"term": "fd"})]),
        resp(text="A Fixed Deposit locks a lump sum at a fixed rate for a fixed term."),
    ])
    history_msgs = [m for m in fake.requests[0].messages if m.role != "system"][:-1]  # drop the live user msg
    assert len(history_msgs) <= 4  # <= 2 turns (user+assistant pairs)
    assert history_msgs[-1].content == "answer 2"  # most recent turn still visible


def test_literacy_intent_does_not_leak_into_normal_conversational_turn(space):
    sid = make_session(space, "ravi")
    _, fake = run(space, sid, "how is my spending?", [
        resp(tool_calls=[call("get_spend_summary")]),
        resp(text="Rent leads your spending this month."),
    ])
    assert fake.requests[0].task_class == "conversational"
    tool_names = {t.name for t in fake.requests[0].tools}
    assert tool_names == {t.name for t in __import__("app.agent.tools", fromlist=["tools_for_mode"]).tools_for_mode("info_only")}
