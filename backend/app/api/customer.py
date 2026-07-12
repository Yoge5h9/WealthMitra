"""Customer-facing read views: GET /api/customer/{session_id}/summary,
GET /api/audit/{session_id}. A persona-keyed variant of the summary,
GET /api/spaces/{space_id}/customers/{persona_id}/summary, serves the RM
console — a LeadPacket carries persona_id but no session id, so the RM
customer-360 cannot resolve a session.

Both are pure reads over already-computed state: the summary re-runs
`AnalyticsEngine` (the same deterministic source every tool/lead uses) and the
audit view replays `app.core.audit.for_session` verbatim. External
holdings/liabilities are only ever included once `persona.external.connected`
is true — that gate lives in the analytics layer itself (see
`app.analytics.networth`), so it applies here for free.
"""

from __future__ import annotations

from fastapi import APIRouter

from fastapi import HTTPException

from app.analytics import AnalyticsEngine
from app.api.sessions import get_space_or_404, resolve_session
from app.core import audit
from app.core.spaces import Space

router = APIRouter()


@router.get("/customer/{session_id}/summary")
def customer_summary(session_id: str) -> dict:
    space, state = resolve_session(session_id)
    return _summary(space, state["persona_id"])


@router.get("/spaces/{space_id}/customers/{persona_id}/summary")
def rm_customer_summary(space_id: str, persona_id: str) -> dict:
    space = get_space_or_404(space_id)
    if persona_id not in space.personas:
        raise HTTPException(status_code=404, detail=f"unknown persona: {persona_id}")
    return _summary(space, persona_id)


def _summary(space: Space, persona_id: str) -> dict:
    persona = space.personas[persona_id]
    profile = persona.profile
    ext = persona.external

    metrics = {m.id: m.value for m in AnalyticsEngine().compute(space, persona_id)}

    return {
        "profile": {
            "persona_id": persona_id,
            "name": profile.name,
            "age": profile.age,
            "city": profile.city,
            "segment": profile.segment,
            "language": profile.language,
            "avatar": profile.avatar,
        },
        "metrics": {
            "net_worth": metrics["net_worth"],
            "monthly_income": metrics["monthly_income"],
            "monthly_surplus": metrics["monthly_surplus"],
            "idle_balance": metrics["idle_balance"],
            "spend_by_category": dict(metrics["spend_by_category"]),
            "risk_band": metrics["risk_band"],
            "segment": metrics["suitability_segment"],
            "goal_progress": metrics["goal_progress"],
        },
        "holdings": {
            "aa_connected": ext.connected,
            "internal_bank_balance": metrics["idle_balance"],
            "external": [h.model_dump(mode="json") for h in ext.holdings] if ext.connected else [],
            "external_liabilities": [l.model_dump(mode="json") for l in ext.liabilities] if ext.connected else [],
        },
        "goals": metrics["goal_progress"].get("goals", []),
    }


@router.get("/audit/{session_id}")
def customer_audit(session_id: str) -> list[dict]:
    space, _state = resolve_session(session_id)
    return [entry.model_dump(mode="json") for entry in audit.for_session(space, session_id)]
