"""RM lead queue: GET /api/spaces/{space}/leads,
POST /api/leads/{lead_id}/status.

Lead lookup across spaces: a `lead_id` (e.g. "LP-2026-000123") is only unique
*within* the space that minted it, and `LeadPacket` carries no space id of its
own — so the status endpoint takes the owning space explicitly, as a REQUIRED
`space_id` query parameter (a request without it is a 422, never a silent
guess at some default space). This keeps the route un-nested (`/api/leads/
{lead_id}/status`) while still being
unambiguous about which space's lead is being updated.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.sessions import get_space_or_404
from app.core import events

router = APIRouter()


class LeadStatusRequest(BaseModel):
    status: Literal["new", "contacted", "converted"]


@router.get("/spaces/{space_id}/leads")
def list_leads(space_id: str) -> list[dict]:
    space = get_space_or_404(space_id)
    ordered = sorted(space.leads, key=lambda lead: lead.priority_score, reverse=True)
    return [lead.model_dump(mode="json") for lead in ordered]


@router.post("/leads/{lead_id}/status")
def update_lead_status(lead_id: str, body: LeadStatusRequest, space_id: str) -> dict:
    space = get_space_or_404(space_id)
    for index, lead in enumerate(space.leads):
        if lead.lead_id == lead_id:
            updated = lead.model_copy(update={"status": body.status})
            space.leads[index] = updated
            events.publish(space.id, {"type": "lead.updated", "payload": updated.model_dump(mode="json")})
            return updated.model_dump(mode="json")
    raise HTTPException(status_code=404, detail=f"unknown lead: {lead_id}")
