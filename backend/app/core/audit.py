"""Append-only per-space audit trail.

Enforced, not just convention: `AuditEntry` is frozen (mutating a recorded
entry raises), the space's log is a private list whose public accessor
returns an immutable snapshot, and this module — the only mutation path —
exposes no update/delete API. Every tool call, LLM call, routing decision,
guardrail trip, execution, and consent event a space records is permanent
for that space's lifetime (until the space itself is reset).
"""

from typing import TYPE_CHECKING

from app.domain.models import AuditEntry

if TYPE_CHECKING:
    from app.core.spaces import Space


def record(space: "Space", entry: AuditEntry) -> str:
    """Append `entry` to `space`'s audit log and return its id."""
    space._audit_entries.append(entry)
    return entry.id


def for_session(space: "Space", session_id: str) -> list[AuditEntry]:
    """Return every audit entry recorded for `session_id`, in append order.

    The returned list is a fresh snapshot; mutating it never touches the log,
    and the entries themselves are frozen.
    """
    return [entry for entry in space.audit if entry.session_id == session_id]
