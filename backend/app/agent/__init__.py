"""Agent Orchestrator package — the compliance-gate-first LLM tool loop (Task 10)."""

from .orchestrator import Orchestrator
from .tools import ComplianceError, ToolContext, tools_for_mode

_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """Process-wide orchestrator singleton, built lazily so importing the app
    never constructs a Gateway (and its provider) as an import side effect.
    """
    global _orchestrator
    if _orchestrator is None:
        from app.gateway import Gateway

        _orchestrator = Orchestrator(Gateway())
    return _orchestrator


def set_orchestrator(orchestrator: Orchestrator | None) -> None:
    """Override the singleton — the seam tests use to inject a fake gateway."""
    global _orchestrator
    _orchestrator = orchestrator


__all__ = [
    "ComplianceError",
    "Orchestrator",
    "ToolContext",
    "get_orchestrator",
    "set_orchestrator",
    "tools_for_mode",
]
