"""Live smoke test — real claude_cli calls on haiku.

Marked `live_llm` and excluded from the default run: it is gated behind
RUN_LIVE_LLM=1 (a shared pytest.ini/conftest marker-filter would be the
tidier exclusion, but this task may not touch those shared files, so the
env gate keeps `make test` green without them). Run explicitly with:

    RUN_LIVE_LLM=1 pytest backend/tests/test_gateway_live.py -m live_llm
"""

import os

import pytest

from app.gateway import Gateway, LLMRequest, Message, ToolSpec

_LIVE = os.environ.get("RUN_LIVE_LLM") == "1"

pytestmark = [
    pytest.mark.live_llm,
    pytest.mark.skipif(not _LIVE, reason="live LLM smoke — set RUN_LIVE_LLM=1 to run"),
]


def _gateway() -> Gateway:
    # Default construction → claude_cli provider from config/models.yaml.
    # intent_assist routes to haiku.
    return Gateway()


def test_live_text_haiku():
    gw = _gateway()
    resp = gw.complete(
        LLMRequest(messages=[Message(role="user", content="Reply with exactly: pong")], task_class="intent_assist")
    )
    assert resp.text is not None
    assert "pong" in resp.text.lower()
    assert resp.tool_calls == []
    assert resp.latency_ms >= 0


def test_live_forced_tool_call_haiku():
    gw = _gateway()
    tools = [
        ToolSpec(
            name="get_balance",
            description="Get the customer's current savings-account balance in INR.",
            input_schema={
                "type": "object",
                "properties": {"account": {"type": "string", "description": "account id, e.g. SA-001"}},
                "required": ["account"],
            },
        )
    ]
    resp = gw.complete(
        LLMRequest(
            messages=[Message(role="user", content="What is the balance for account SA-001? Call the tool to find out.")],
            tools=tools,
            tool_choice="any",
            task_class="intent_assist",
        )
    )
    assert len(resp.tool_calls) >= 1
    assert resp.tool_calls[0].name == "get_balance"
    assert isinstance(resp.tool_calls[0].arguments, dict)
