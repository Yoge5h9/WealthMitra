"""Nudge engine package (Task 13) — functional + relational, quota-enforced.

`generate_nudges` is the public entry point every caller (the `get_nudges`
tool, `GET /api/customer/{session_id}/nudges`) should use.
"""

from .engine import FUNCTIONAL_CAP, generate_nudges, set_gateway

__all__ = ["FUNCTIONAL_CAP", "generate_nudges", "set_gateway"]
