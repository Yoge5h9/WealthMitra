"""Live orchestrator smoke — one mini-conversation per routing mode on the
real claude_cli provider, all task classes pinned to haiku for cost.

Env-gated like test_gateway_live.py:

    RUN_LIVE_LLM=1 pytest backend/tests/test_agent_live.py -m live_llm -s
"""

import os
from datetime import datetime, timezone

import pytest

from app.agent.orchestrator import Orchestrator
from app.core import audit
from app.core.spaces import get_space_store
from app.gateway import Gateway
from app.gateway.providers.claude_cli import ClaudeCLIProvider

_LIVE = os.environ.get("RUN_LIVE_LLM") == "1"

pytestmark = [
    pytest.mark.live_llm,
    pytest.mark.skipif(not _LIVE, reason="live LLM smoke — set RUN_LIVE_LLM=1 to run"),
]

_HAIKU_ROUTING = {tc: "haiku" for tc in
                  ("intent_assist", "conversational", "nudge_copy", "lead_narrative", "literacy")}


def _orchestrator() -> Orchestrator:
    gw = Gateway(provider=ClaudeCLIProvider(pricing={}), provider_name="claude_cli", routing=_HAIKU_ROUTING)
    return Orchestrator(gw)


def _run(persona_id: str, message: str, language: str = "en"):
    store = get_space_store()
    space = store.get(store.create_space())
    session_id = f"sess_live_{persona_id}"
    space.sessions[session_id] = {
        "persona_id": persona_id, "language": language, "history": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    frames = list(_orchestrator().run_turn(space, session_id, message))
    reply = "".join(f["text"] for f in frames if f["type"] == "token")
    cards = [f["card"]["card_type"] for f in frames if f["type"] == "card"]
    routing = [e for e in audit.for_session(space, session_id) if e.kind == "routing"]
    print(f"\n[{persona_id} | {language}] {message}\n  -> mode={routing[0].outputs_summary['path']}"
          f" cards={cards}\n  reply: {reply}\n")
    return space, session_id, frames, reply, cards, routing


def test_live_info_only_ravi():
    _, _, frames, reply, _, routing = _run("ravi", "How is my spending looking this month?")
    assert routing[0].outputs_summary["path"] == "info_only"
    assert reply.strip()
    assert frames[-1]["type"] == "done"


def test_live_auto_execute_ravi():
    space, _, frames, reply, cards, routing = _run("ravi", "I want to invest my monthly surplus, can you set something up?")
    assert routing[0].outputs_summary["path"] == "auto_execute"
    assert reply.strip()
    assert space.leads == []  # vanilla path must never create a lead
    receipt_cards = [c for c in cards if c == "execution_receipt"]
    assert not receipt_cards  # and never a receipt without explicit confirm


def test_live_rm_lead_meera():
    space, _, _, reply, cards, routing = _run("meera", "I want to invest in equity mutual funds", language="gu")
    assert routing[0].outputs_summary["path"] == "rm_lead"
    assert len(space.leads) == 1
    assert "routed_to_rm" in cards
    assert reply.strip()


def test_live_distress_vikram():
    space, sid, _, reply, cards, routing = _run("vikram", "I can't pay my EMI this month, I'm really stressed")
    assert routing[0].outputs_summary["path"] == "distress_suppress"
    assert "distress_support" in cards
    assert space.leads == []
    tool_calls = [e for e in audit.for_session(space, sid) if e.kind == "tool_call"]
    assert all(e.name not in ("get_eligible_products", "request_execution", "create_rm_lead")
               for e in tool_calls)
    assert reply.strip()
