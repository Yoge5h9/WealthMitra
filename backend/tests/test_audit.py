from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core import audit
from app.core.spaces import SpaceStore
from app.domain.models import AuditEntry

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "personas"


@pytest.fixture
def space():
    store = SpaceStore(seed_dir=FIXTURES_DIR)
    return store.get(store.create_space())


def _entry(entry_id: str, session_id: str, kind: str = "tool_call") -> AuditEntry:
    return AuditEntry(
        id=entry_id,
        session_id=session_id,
        ts=datetime(2026, 7, 11, 12, 0, 0),
        kind=kind,
        name="get_profile",
        inputs={},
        outputs_summary={},
        refs=[],
    )


def test_record_appends_to_space_audit_log(space) -> None:
    entry = _entry("a1", "s1")

    returned_id = audit.record(space, entry)

    assert returned_id == "a1"
    assert space.audit == (entry,)


def test_record_is_append_only(space) -> None:
    audit.record(space, _entry("a1", "s1"))
    audit.record(space, _entry("a2", "s1"))

    assert [e.id for e in space.audit] == ["a1", "a2"]


def test_for_session_filters_by_session_id(space) -> None:
    audit.record(space, _entry("a1", "s1"))
    audit.record(space, _entry("a2", "s2"))
    audit.record(space, _entry("a3", "s1"))

    assert [e.id for e in audit.for_session(space, "s1")] == ["a1", "a3"]
    assert [e.id for e in audit.for_session(space, "s2")] == ["a2"]


def test_for_session_returns_empty_list_for_unknown_session(space) -> None:
    audit.record(space, _entry("a1", "s1"))

    assert audit.for_session(space, "unknown") == []


def test_recorded_entry_cannot_be_mutated_in_place(space) -> None:
    audit.record(space, _entry("a1", "s1"))

    stored = audit.for_session(space, "s1")[0]
    with pytest.raises(ValidationError):
        stored.name = "TAMPERED"

    assert space.audit[0].name == "get_profile"


def test_space_audit_accessor_is_an_immutable_snapshot(space) -> None:
    audit.record(space, _entry("a1", "s1"))

    snapshot = space.audit
    assert isinstance(snapshot, tuple)
    assert not hasattr(snapshot, "clear")
    assert not hasattr(snapshot, "append")


def test_mutating_for_session_result_does_not_touch_the_log(space) -> None:
    audit.record(space, _entry("a1", "s1"))

    entries = audit.for_session(space, "s1")
    entries.clear()

    assert [e.id for e in space.audit] == ["a1"]
    assert [e.id for e in audit.for_session(space, "s1")] == ["a1"]


def test_space_audit_property_cannot_be_replaced(space) -> None:
    audit.record(space, _entry("a1", "s1"))

    with pytest.raises(AttributeError):
        space.audit = ()

    assert [e.id for e in space.audit] == ["a1"]
