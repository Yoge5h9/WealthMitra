"""Session creation: POST /api/spaces/{space}/sessions.

A session binds (space, persona, language) and returns a greeting as a list of
the same frames the chat SSE stream uses, so the client renders both paths with
one code path. Session state lives in `Space.sessions`; the session→space index
here lets /api/chat find the owning space without walking every space.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agent.orchestrator import spend_card
from app.agent.prompts import fallback_greeting
from app.analytics import AnalyticsEngine
from app.core import audit
from app.core.spaces import DEFAULT_SPACE_ID, Space, get_space_store
from app.domain.models import AuditEntry, PersonaProfile
from app.onboarding import greeting as onboarding_greeting

router = APIRouter()

# session_id → space_id. If a space is reset its sessions vanish from
# Space.sessions; a stale index entry then 404s in resolve_session, which is
# the behaviour we want (a reset space has no live sessions).
_SESSION_INDEX: dict[str, str] = {}

LANGUAGES = ("en", "hi", "gu")


class SessionRequest(BaseModel):
    persona_id: str
    language: Literal["en", "hi", "gu"] | None = None


def get_space_or_404(space_id: str) -> Space:
    store = get_space_store()
    if space_id == DEFAULT_SPACE_ID:
        return store.default_space()
    try:
        return store.get(space_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown space: {space_id}") from None


def resolve_session(session_id: str) -> tuple[Space, dict]:
    """Find (space, session state) for a session id, or 404."""
    space_id = _SESSION_INDEX.get(session_id)
    if space_id is not None:
        try:
            space = get_space_or_404(space_id)
        except HTTPException:
            space = None
        if space is not None and session_id in space.sessions:
            return space, space.sessions[session_id]
    raise HTTPException(status_code=404, detail=f"unknown session: {session_id}")


@router.post("/spaces/{space_id}/sessions")
def create_session(space_id: str, body: SessionRequest) -> dict:
    space = get_space_or_404(space_id)
    is_new_customer = body.persona_id == "new_to_idbi"
    if not is_new_customer and body.persona_id not in space.personas:
        raise HTTPException(status_code=404, detail=f"unknown persona: {body.persona_id}")

    profile = space.personas[body.persona_id].profile if not is_new_customer else None
    language = body.language or (profile.language if profile and profile.language in LANGUAGES else "en")

    session_id = f"sess_{secrets.token_hex(8)}"
    space.sessions[session_id] = {
        "persona_id": body.persona_id,
        "language": language,
        "history": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _SESSION_INDEX[session_id] = space.id

    if is_new_customer:
        return {"session_id": session_id, "greeting": onboarding_greeting(space, session_id)}

    assert profile is not None
    greeting = _greeting_frames(space, session_id, profile, language)
    return {"session_id": session_id, "greeting": greeting}


def _greeting_frames(
    space: Space, session_id: str, profile: PersonaProfile, language: str
) -> list[dict]:
    """Deterministic localized greeting — opening a session never spends an
    LLM call; the model only engages once the customer actually says something.
    """
    entry_id = f"aud_{uuid.uuid4().hex[:12]}"
    audit.record(
        space,
        AuditEntry(
            id=entry_id,
            session_id=session_id,
            ts=datetime.now(timezone.utc),
            kind="guardrail",
            name="greeting_static",
            inputs={"language": language},
            outputs_summary={"deterministic": True},
            refs=[],
        ),
    )
    metrics = {m.id: m for m in AnalyticsEngine().compute(space, profile.id)}
    return [
        {"type": "avatar", "state": "speaking"},
        {"type": "token", "text": fallback_greeting(profile, language)},
        {"type": "card", "card": spend_card(metrics)},
        {"type": "done", "audit_ref": entry_id},
    ]
