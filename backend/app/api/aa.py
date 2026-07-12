"""POST /api/aa/consent — the two-step Account Aggregator
consent state machine.

Two independent, revocable grants per session (compliance ADR: the AA
artefact authorising data *transfer* is never the same thing as the DPDP
consent authorising *processing/advisory use*):

  * `step="transfer"`   — the AA data-pull consent.
  * `step="processing"` — the DPDP consent to use that data for advisory work.

Both granted flips `persona.external.connected` on, which is the single flag
every analytics/tool module already reads to decide whether external
holdings/liabilities are in scope (see `app.analytics.networth`'s docstring
and `app.agent.tools.get_holdings`) — this endpoint is the ONLY writer of
that flag. Revoking either grant flips it back off, hiding external data
again without discarding the persona's underlying holdings/liabilities.

This session's consent state is also what `app.agent.orchestrator._build_lead`
reads (via `_consent_snapshot`) to fill `LeadPacket.consent` for every lead
created afterwards — connecting AA here is what makes a subsequent chat-built
lead carry a real consent record instead of the `{None, False}` placeholder.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.analytics import AnalyticsEngine
from app.analytics.constants import IDBI_LOAN_REFINANCE_BENCHMARK_RATE_PCT
from app.api.sessions import resolve_session
from app.catalogue import eligible_shelf
from app.core import audit, events
from app.core.spaces import Space
from app.domain.models import AuditEntry, PersonaData
from app.routing import build_lead_packet

router = APIRouter()

_AFFLUENT_SEGMENTS = frozenset({"affluent", "hni"})


class AAConsentRequest(BaseModel):
    session_id: str
    step: Literal["transfer", "processing"]
    granted: bool


class AAState(BaseModel):
    aa_available: bool
    transfer_granted: bool
    processing_granted: bool
    connected: bool
    holdings: list[dict] | None = None


@router.post("/aa/consent", response_model=AAState)
def aa_consent(body: AAConsentRequest) -> AAState:
    space, state = resolve_session(body.session_id)
    persona_id = state["persona_id"]

    # The cold-start path has no seeded PersonaData yet. It can still record
    # both explicit permissions so a fresh customer sees the same consent
    # model before an account is linked; there is deliberately no fabricated
    # external holding or analytics result to reveal.
    if persona_id == "new_to_idbi":
        consent = state.setdefault(
            "aa_consent",
            {"transfer_granted": False, "processing_granted": False, "consent_id": None},
        )
        if body.step == "transfer":
            consent["transfer_granted"] = body.granted
            consent["consent_id"] = f"aa_{uuid.uuid4().hex[:12]}" if body.granted else None
        else:
            consent["processing_granted"] = body.granted
        connected = bool(consent["transfer_granted"] and consent["processing_granted"])
        audit.record(
            space,
            AuditEntry(
                id=f"aud_{uuid.uuid4().hex[:12]}",
                session_id=body.session_id,
                ts=datetime.now(timezone.utc),
                kind="consent",
                name=f"aa_{body.step}",
                inputs={"step": body.step, "granted": body.granted, "cold_start": True},
                outputs_summary={"connected": connected, "external_data_available": False},
                refs=["onboarding:v1"],
            ),
        )
        return AAState(
            aa_available=True,
            transfer_granted=consent["transfer_granted"],
            processing_granted=consent["processing_granted"],
            connected=connected,
            holdings=[],
        )

    persona = space.personas[persona_id]
    ext = persona.external

    if not ext.aa_available:
        return AAState(
            aa_available=False, transfer_granted=False, processing_granted=False,
            connected=False, holdings=None,
        )

    consent = state.setdefault(
        "aa_consent",
        {"transfer_granted": False, "processing_granted": False, "consent_id": None, "refi_lead_created": False},
    )
    was_connected = ext.connected

    if body.step == "transfer":
        consent["transfer_granted"] = body.granted
        consent["consent_id"] = f"aa_{uuid.uuid4().hex[:12]}" if body.granted else None
    else:
        consent["processing_granted"] = body.granted

    connected = bool(consent["transfer_granted"] and consent["processing_granted"])
    ext.connected = connected

    now = datetime.now(timezone.utc)
    audit.record(
        space,
        AuditEntry(
            id=f"aud_{uuid.uuid4().hex[:12]}",
            session_id=body.session_id,
            ts=now,
            kind="consent",
            name=f"aa_{body.step}",
            inputs={"step": body.step, "granted": body.granted},
            outputs_summary={"connected": connected},
            refs=[],
        ),
    )

    holdings = [h.model_dump(mode="json") for h in ext.holdings] if connected else None

    if connected and not was_connected:
        events.publish(
            space.id,
            {
                "type": "aa.connected",
                "payload": {"session_id": body.session_id, "persona_id": persona_id, "holdings": holdings},
            },
        )
        _maybe_create_refi_lead(space, body.session_id, persona_id, persona, consent, now)

    return AAState(
        aa_available=True,
        transfer_granted=consent["transfer_granted"],
        processing_granted=consent["processing_granted"],
        connected=connected,
        holdings=holdings,
    )


def _maybe_create_refi_lead(
    space: Space, session_id: str, persona_id: str, persona: PersonaData, consent: dict, now: datetime
) -> None:
    """Idempotent: fires at most once per session, the first time AA connects
    with a refinanceable (>10.5% IDBI benchmark) external liability. Re-consent
    after a revoke-and-reconnect never creates a second lead — `refi_lead_created`
    is sticky for the life of the session.
    """
    if consent["refi_lead_created"]:
        return

    metrics = {m.id: m for m in AnalyticsEngine().compute(space, persona_id, now=now)}
    inefficiency = metrics["external_inefficiency"].value
    refinanceable = inefficiency.get("refinanceable_liabilities", []) if inefficiency.get("available") else []
    if not refinanceable:
        return
    worst = max(refinanceable, key=lambda item: item["rate"])

    segment = str(metrics["suitability_segment"].value)
    band = str(metrics["risk_band"].value)
    surplus = float(metrics["monthly_surplus"].value)
    shelf = eligible_shelf(segment, band, monthly_surplus=surplus, is_affluent_or_hni=segment in _AFFLUENT_SEGMENTS)

    ext = persona.external
    lead_metrics = {
        "monthly_income": metrics["monthly_income"].value,
        "monthly_surplus": metrics["monthly_surplus"].value,
        "idle_balance": metrics["idle_balance"].value,
        "external_holdings": [h.model_dump(mode="json") for h in ext.holdings],
        "liabilities": [l.model_dump(mode="json") for l in ext.liabilities],
        "capacity_score": metrics["capacity_score"].value,
        "tolerance_score": metrics["tolerance_score"].value,
        "risk_band": band,
        "goals": metrics["goal_progress"].value.get("goals", []),
    }
    trigger = (
        f"AA connected: {worst['type']} at {worst['rate']}% exceeds the IDBI refinance benchmark "
        f"of {IDBI_LOAN_REFINANCE_BENCHMARK_RATE_PCT}%."
    )
    lead = build_lead_packet(
        persona.profile, lead_metrics, shelf, trigger, "loans_cards", seq=len(space.leads) + 1, now=now
    )
    lead = lead.model_copy(
        update={
            "consent": {
                "aa_consent_id": consent["consent_id"],
                "advice_consent": bool(consent["processing_granted"]),
            }
        }
    )
    space.leads.append(lead)
    consent["refi_lead_created"] = True

    audit.record(
        space,
        AuditEntry(
            id=f"aud_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            ts=now,
            kind="routing",
            name="lead_created",
            inputs={"family": "loans_cards", "trigger": "aa_connect_high_rate_liability"},
            outputs_summary={"lead_id": lead.lead_id, "priority_score": lead.priority_score},
            refs=[lead.lead_id],
        ),
    )
    events.publish(space.id, {"type": "lead.created", "payload": lead.model_dump(mode="json")})
