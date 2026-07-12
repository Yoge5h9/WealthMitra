"""GET /api/customer/{session_id}/nudges — the customer's
current, LLM-phrased nudge feed.

`app.nudges.engine` mints day-bucketed deterministic ids, so this endpoint
caches the feed per (space, persona) for the calendar day it was generated —
a repeat GET the same day is a pure read (no second LLM round-trip) and
`nudge.created` is only published for ids the space has never seen before,
so refreshing the feed never spams the WS with duplicate events.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.api.sessions import resolve_session
from app.core import events
from app.nudges import generate_nudges

router = APIRouter()


@router.get("/customer/{session_id}/nudges")
def customer_nudges(session_id: str) -> list[dict]:
    space, state = resolve_session(session_id)
    persona_id = state["persona_id"]
    now = datetime.now(timezone.utc)

    existing = [n for n in space.nudges if n.persona_id == persona_id]
    if existing and all(n.created_at.date() == now.date() for n in existing):
        return [n.model_dump(mode="json") for n in existing]

    known_ids = {n.id for n in existing}
    fresh = generate_nudges(space, persona_id, now=now, use_llm=True)

    space.nudges = [n for n in space.nudges if n.persona_id != persona_id] + fresh
    for nudge in fresh:
        if nudge.id not in known_ids:
            events.publish(space.id, {"type": "nudge.created", "payload": nudge.model_dump(mode="json")})

    return [n.model_dump(mode="json") for n in fresh]
