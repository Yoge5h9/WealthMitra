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
