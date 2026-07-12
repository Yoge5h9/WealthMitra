"""Live nudge-copy smoke on the real claude_cli provider (`nudge_copy` -> haiku).

Env-gated like test_agent_live.py / test_gateway_live.py:

    RUN_LIVE_LLM=1 pytest backend/tests/test_nudges_live.py -m live_llm -s
"""

import os
from datetime import datetime, timezone

import pytest

from app.core.spaces import get_space_store
from app.gateway import Gateway
from app.gateway.providers.claude_cli import ClaudeCLIProvider
from app.nudges import generate_nudges

_LIVE = os.environ.get("RUN_LIVE_LLM") == "1"

pytestmark = [
    pytest.mark.live_llm,
    pytest.mark.skipif(not _LIVE, reason="live LLM smoke — set RUN_LIVE_LLM=1 to run"),
]

_HAIKU_ROUTING = {tc: "haiku" for tc in
                  ("intent_assist", "conversational", "nudge_copy", "lead_narrative", "literacy")}


def test_live_nudge_copy_ravi():
    gateway = Gateway(provider=ClaudeCLIProvider(pricing={}), provider_name="claude_cli", routing=_HAIKU_ROUTING)
    store = get_space_store()
    space = store.get(store.create_space())
    now = datetime.now(timezone.utc)

    nudges = generate_nudges(space, "ravi", now=now, use_llm=True, gateway=gateway)
    assert nudges
    for n in nudges:
        print(f"\n[{n.kind}/{n.intent}] {n.title}\n  {n.body}")
        assert n.title.strip() and n.body.strip()
