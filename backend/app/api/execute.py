"""POST /api/execute — confirms a purchase `app.agent.tools.
request_execution` already prepared as an `execution_confirm` card.

The confirm token is validated against the `request_execution` audit entry
that tool already writes for this session (`kind="tool_call"`,
`outputs_summary["confirm_token"]`) — that entry is the durable record of
what was actually offered, so this endpoint needs no confirm-token registry
of its own to prove the offer was genuine and unmodified. Issued receipts are
stored on the owning `Space` (`space.receipts`, keyed by confirm token) purely
so a replayed request returns the identical `Receipt` instead of executing
twice; living on the space, they die with it on reset — a pre-reset confirm
token can never replay into a fresh space.

The vanilla/regulated tag is re-checked here even though `request_execution`
already refuses to prepare a confirm card for a regulated product — a client
could still POST straight to this endpoint with an arbitrary product id and a
fabricated token, and that must 403 regardless of anything else about the
request.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.sessions import resolve_session
from app.catalogue import CATALOGUE
from app.core import audit, events
from app.core.spaces import Space
from app.domain.models import AuditEntry, Receipt

router = APIRouter()

AMOUNT_CAP_INR = 10_00_00_000  # ₹10 crore


class ExecuteRequest(BaseModel):
    session_id: str
    product_id: str
    amount: int
    confirm_token: str


def _find_confirm_entry(space: Space, session_id: str, confirm_token: str) -> AuditEntry | None:
    for entry in space.audit:
        if (
            entry.session_id == session_id
            and entry.kind == "tool_call"
            and entry.name == "request_execution"
            and entry.outputs_summary.get("confirm_token") == confirm_token
        ):
            return entry
    return None


@router.post("/execute", response_model=Receipt)
def execute(body: ExecuteRequest) -> Receipt:
    space, state = resolve_session(body.session_id)

    cached = space.receipts.get(body.confirm_token)
    if cached is not None:
        return cached

    product = CATALOGUE.products.get(body.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"unknown product: {body.product_id}")
    if product.tag != "vanilla":
        raise HTTPException(status_code=403, detail="regulated_product_requires_rm")

    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="amount_must_be_positive")
    if body.amount > AMOUNT_CAP_INR:
        raise HTTPException(status_code=400, detail="amount_exceeds_cap")

    entry = _find_confirm_entry(space, body.session_id, body.confirm_token)
    if (
        entry is None
        or entry.inputs.get("product_id") != body.product_id
        or entry.inputs.get("amount") != body.amount
    ):
        raise HTTPException(status_code=400, detail="invalid_confirm_token")

    now = datetime.now(timezone.utc)
    receipt_id = f"RCT-{uuid.uuid4().hex[:12]}"
    audit_ref = f"aud_{uuid.uuid4().hex[:12]}"
    audit.record(
        space,
        AuditEntry(
            id=audit_ref,
            session_id=body.session_id,
            ts=now,
            kind="execution",
            name="execute",
            inputs={"product_id": body.product_id, "amount": body.amount},
            outputs_summary={"receipt_id": receipt_id, "product_name": product.name},
            refs=[receipt_id, product.id],
        ),
    )

    persona_id = state["persona_id"]
    space.portfolios.setdefault(persona_id, []).append(
        {
            "product_id": product.id,
            "product_name": product.name,
            "amount": body.amount,
            "receipt_id": receipt_id,
        }
    )

    receipt = Receipt(
        receipt_id=receipt_id,
        session_id=body.session_id,
        product_id=product.id,
        product_name=product.name,
        amount=body.amount,
        executed_at=now,
        audit_ref=audit_ref,
    )
    space.receipts[body.confirm_token] = receipt
    events.publish(space.id, {"type": "execution.completed", "payload": receipt.model_dump(mode="json")})
    return receipt
