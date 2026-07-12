from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.domain.models import (
    AuditEntry,
    LeadPacket,
    Metric,
    Nudge,
    Product,
    Receipt,
    Transaction,
)


def _metric_kwargs(**overrides: object) -> dict:
    base = dict(
        id="m1",
        value=1234.5,
        unit="inr",
        as_of=date(2026, 7, 11),
        source_refs=["txn-1"],
        method="capacity_v1",
        input_hash="deadbeef",
        computed_at=datetime(2026, 7, 11, 12, 0, 0),
    )
    base.update(overrides)
    return base


def test_metric_accepts_valid_fields() -> None:
    metric = Metric(**_metric_kwargs())

    assert metric.id == "m1"
    assert metric.unit == "inr"


def test_metric_rejects_missing_required_field() -> None:
    kwargs = _metric_kwargs()
    del kwargs["method"]

    with pytest.raises(ValidationError):
        Metric(**kwargs)


def test_transaction_rejects_bad_type_enum() -> None:
    with pytest.raises(ValidationError):
        Transaction(
            id="t1",
            date=date(2026, 6, 1),
            amount=100,
            type="wire",  # not "credit" | "debit"
            category="misc",
            description="bad",
            account="sa",
        )


def test_transaction_rejects_bad_account_enum() -> None:
    with pytest.raises(ValidationError):
        Transaction(
            id="t1",
            date=date(2026, 6, 1),
            amount=100,
            type="credit",
            category="misc",
            description="bad",
            account="wallet",  # not "sa" | "ca" | "cc"
        )


def test_product_rejects_bad_tag_enum() -> None:
    with pytest.raises(ValidationError):
        Product(
            id="p1",
            name="Mystery Fund",
            tag="exotic",  # not "vanilla" | "regulated"
            category="mutual_fund",
            min_amount=500,
            expected_return="7.4% p.a.",
            description="desc",
        )


def test_lead_packet_rejects_bad_family_enum() -> None:
    with pytest.raises(ValidationError):
        LeadPacket(
            lead_id="LP-2026-000001",
            family="crypto",  # not "investment_insurance" | "loans_cards"
            customer={},
            trigger={},
            financial_snapshot={},
            risk={},
            goals=[],
            suitability={},
            next_best_action="call",
            consent={},
            priority_score=50,
            created_at=datetime(2026, 7, 11, 12, 0, 0),
        )


def test_lead_packet_defaults_status_to_new() -> None:
    lead = LeadPacket(
        lead_id="LP-2026-000001",
        family="loans_cards",
        customer={"persona_id": "vikram"},
        trigger={"type": "distress_signal"},
        financial_snapshot={},
        risk={},
        goals=[],
        suitability={},
        next_best_action="refinance",
        consent={"advice_consent": True},
        priority_score=80,
        created_at=datetime(2026, 7, 11, 12, 0, 0),
    )

    assert lead.status == "new"


def test_receipt_rejects_missing_field() -> None:
    with pytest.raises(ValidationError):
        Receipt(
            receipt_id="R1",
            session_id="s1",
            product_id="p1",
            amount=1000,
            executed_at=datetime(2026, 7, 11, 12, 0, 0),
            audit_ref="a1",
        )  # missing product_name


def test_nudge_rejects_bad_intent_enum() -> None:
    with pytest.raises(ValidationError):
        Nudge(
            id="n1",
            persona_id="ravi",
            kind="functional",
            intent="urgent",  # not in the allowed Literal set
            title="t",
            body="b",
            language="en",
            source_metric_ids=[],
            created_at=datetime(2026, 7, 11, 12, 0, 0),
        )


def test_audit_entry_rejects_bad_kind_enum() -> None:
    with pytest.raises(ValidationError):
        AuditEntry(
            id="a1",
            session_id="s1",
            ts=datetime(2026, 7, 11, 12, 0, 0),
            kind="notification",  # not in the allowed Literal set
            name="foo",
            inputs={},
            outputs_summary={},
            refs=[],
        )


def test_audit_entry_accepts_valid_kind() -> None:
    entry = AuditEntry(
        id="a1",
        session_id="s1",
        ts=datetime(2026, 7, 11, 12, 0, 0),
        kind="tool_call",
        name="get_profile",
        inputs={},
        outputs_summary={"ok": True},
        refs=[],
    )

    assert entry.kind == "tool_call"
