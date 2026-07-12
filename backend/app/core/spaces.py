import copy
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from app.domain.models import AuditEntry, LeadPacket, Nudge, PersonaData, load_personas

_BUILD_PENDING_HTML = (
    "<!doctype html><html><head><title>WealthMitra</title></head>"
    "<body><p>frontend build pending</p></body></html>"
)


def _is_reserved(path: str) -> bool:
    return path == "api" or path.startswith("api/") or path == "ws" or path.startswith("ws/")


def mount_spa(app: FastAPI, dist_dir: Path) -> None:
    """Serve the built frontend SPA, or a placeholder page if it hasn't been built yet.

    Registered after all other routers, so explicit routes (e.g. /api/*) always
    match first; this only ever handles paths nothing else claimed.
    """
    index_path = dist_dir / "index.html"

    if not index_path.exists():
        @app.get("/", include_in_schema=False)
        async def build_pending() -> HTMLResponse:
            return HTMLResponse(_BUILD_PENDING_HTML)

        return

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        if _is_reserved(full_path):
            raise HTTPException(status_code=404)

        candidate = dist_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_path)


# --- Judge-isolated demo spaces / in-memory state store ---
#
# Unrelated to the SPA-mounting helpers above; this module is the literal file
# path the build plan names for both, so the two concerns share a file.

DEFAULT_SEED_DIR = Path(__file__).resolve().parents[3] / "data" / "synthetic"
DEFAULT_SPACE_ID = "default"


@dataclass
class Space:
    """One judge-isolated demo world: a deep-copied slice of seed state."""

    id: str
    personas: dict[str, PersonaData]
    portfolios: dict = field(default_factory=dict)
    leads: list[LeadPacket] = field(default_factory=list)
    nudges: list[Nudge] = field(default_factory=list)
    sessions: dict = field(default_factory=dict)
    # The demo's only cold-start profile. It is deliberately small and
    # self-declared, but survives new chat sessions within the same demo space.
    new_customer_profile: dict = field(default_factory=dict)
    # Executed-purchase receipts keyed by confirm token (idempotent replay);
    # living on the space means a reset discards them with everything else.
    receipts: dict = field(default_factory=dict)
    # Append-only audit log: the ONLY mutation path is app.core.audit.record,
    # which appends to this private list. Readers get an immutable snapshot.
    _audit_entries: list[AuditEntry] = field(default_factory=list, repr=False)

    @property
    def audit(self) -> tuple[AuditEntry, ...]:
        """Read-only snapshot of the audit log, in append order."""
        return tuple(self._audit_entries)


class SpaceStore:
    """Owns one seed load of the persona roster and hands out independent spaces.

    Seed personas are parsed once, at construction. Every space created from
    this store gets its own `copy.deepcopy` of that seed — mutating one space's
    personas/portfolios/leads/nudges/sessions/audit never affects another, and
    `reset` restores the pristine seed by discarding the mutated copy.
    """

    def __init__(self, seed_dir: Path | None = None) -> None:
        self._seed_personas = load_personas(seed_dir or DEFAULT_SEED_DIR)
        self._spaces: dict[str, Space] = {}

    def _seeded_space(self, space_id: str) -> Space:
        return Space(id=space_id, personas=copy.deepcopy(self._seed_personas))

    def create_space(self) -> str:
        """Create a new, independently-seeded space and return its id."""
        space_id = secrets.token_hex(4)
        self._spaces[space_id] = self._seeded_space(space_id)
        return space_id

    def get(self, space_id: str) -> Space:
        try:
            return self._spaces[space_id]
        except KeyError:
            raise KeyError(f"unknown space: {space_id}") from None

    def reset(self, space_id: str) -> None:
        """Discard `space_id`'s state and reseed it from the pristine seed."""
        self.get(space_id)  # raises KeyError if the space doesn't exist
        self._spaces[space_id] = self._seeded_space(space_id)

    def default_space(self) -> Space:
        """Return the well-known shared default space, creating it on first use."""
        if DEFAULT_SPACE_ID not in self._spaces:
            self._spaces[DEFAULT_SPACE_ID] = self._seeded_space(DEFAULT_SPACE_ID)
        return self._spaces[DEFAULT_SPACE_ID]


_default_store: SpaceStore | None = None


def get_space_store() -> SpaceStore:
    """Lazily construct and return the process-wide `SpaceStore` singleton.

    Lazy rather than a module-level `= SpaceStore()`: this module is imported
    by `app.main` (for `mount_spa`) regardless of whether `data/synthetic/` is
    populated yet, and eager loading here would make every unrelated test that
    imports the app fail if the seed data is momentarily invalid.
    """
    global _default_store
    if _default_store is None:
        _default_store = SpaceStore()
    return _default_store
