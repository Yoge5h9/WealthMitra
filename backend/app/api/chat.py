"""POST /api/chat — the conversational turn as an SSE stream.

Frames: {"type":"token"|"card"|"avatar"|"done", ...}, one per SSE `data:` line.
The orchestrator yields plain dicts; this endpoint only serializes them — every
compliance decision (routing gate, tool gating, number audit) happened before a
frame reaches the wire.

The `done` frame carries an optional `error: true` field (an extension of the
C.6 shape): if anything raises mid-turn the stream still closes with a `done`
frame, so the client never hangs on a half-finished conversation.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent import get_orchestrator
from app.api.sessions import resolve_session
from app.core import audit
from app.core.spaces import Space
from app.domain.models import AuditEntry

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    language: Literal["en", "hi", "gu"] | None = None


def _sse(frame: dict) -> str:
    return f"data: {json.dumps(frame, ensure_ascii=False)}\n\n"


def _record_turn_failure(space: Space, session_id: str, exc: Exception) -> str:
    entry_id = f"aud_{uuid.uuid4().hex[:12]}"
    audit.record(
        space,
        AuditEntry(
            id=entry_id,
            session_id=session_id,
            ts=datetime.now(timezone.utc),
            kind="guardrail",
            name="turn_failed",
            inputs={},
            outputs_summary={"error": type(exc).__name__, "message": str(exc)[:200]},
            refs=[],
        ),
    )
    return entry_id


@router.post("/chat")
def chat(body: ChatRequest) -> StreamingResponse:
    space, _state = resolve_session(body.session_id)
    orchestrator = get_orchestrator()

    def stream() -> Iterator[str]:
        try:
            for frame in orchestrator.run_turn(space, body.session_id, body.message, body.language):
                yield _sse(frame)
        except Exception as exc:  # noqa: BLE001 — the stream must always close with a done frame
            ref = _record_turn_failure(space, body.session_id, exc)
            yield _sse({"type": "done", "audit_ref": ref, "error": True})

    return StreamingResponse(stream(), media_type="text/event-stream")
