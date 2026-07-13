"""Space lifecycle + persona roster: POST /api/spaces,
POST /api/spaces/{space}/reset, GET /api/personas.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.sessions import get_space_or_404
from app.core import events
from app.core.spaces import DEFAULT_SPACE_ID, get_space_store

router = APIRouter()


@router.post("/spaces")
def create_space() -> dict:
    space_id = get_space_store().create_space()
    return {"space_id": space_id}


@router.post("/spaces/{space_id}/reset")
def reset_space(space_id: str) -> dict:
    store = get_space_store()
    if space_id == DEFAULT_SPACE_ID:
        store.default_space()  # ensure it exists before resetting it
    try:
        store.reset(space_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown space: {space_id}") from None
    events.publish(space_id, {"type": "space.reset", "payload": {"space_id": space_id}})
    return {"space_id": space_id, "reset": True}


@router.get("/personas")
def list_personas() -> list[dict]:
    """Roster cards for persona selection. Reads the well-known default space's
    persona set, which is the shared seed roster — every space is deep-copied
    from the same seed, so this reflects every space's starting roster.

    Excludes "new_to_idbi": onboarding injects a synthetic persona under that
    id once a cold-start customer completes their profile, but the frontend
    supplies its own "New to IDBI" showcase card — the runtime-injected one
    must not leak in as a duplicate roster entry.
    """
    space = get_space_or_404(DEFAULT_SPACE_ID)
    return [
        {
            "id": persona_id,
            "name": persona.profile.name,
            "age": persona.profile.age,
            "city": persona.profile.city,
            "segment": persona.profile.segment,
            "language": persona.profile.language,
            "avatar": persona.profile.avatar,
            "story": persona.profile.story,
        }
        for persona_id, persona in sorted(space.personas.items())
        if persona_id != "new_to_idbi"
    ]
