"""Pure domain models — the canonical backend contracts.

Field names/types are the single source of truth for these shapes; this
module has no behaviour beyond validation and the persona-file loader.
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Metric(BaseModel):
    """Audit-grade universal output for every computed figure."""

    id: str
    value: float | str | dict
    unit: str  # "inr" | "ratio" | "score" | "label" | "json"
    as_of: date
    source_refs: list[str]  # txn ids / holding ids / config keys
    method: str  # formula id + version, e.g. "capacity_v1"
    input_hash: str  # sha256 of canonical inputs
    computed_at: datetime


class LeadPacket(BaseModel):
    """The structured hand-off packet routed to a human Relationship Manager."""

    lead_id: str  # "LP-2026-000123"
    family: Literal["investment_insurance", "loans_cards"]
    status: Literal["new", "contacted", "converted"] = "new"
    customer: dict  # {persona_id, name, segment, age_band, city_tier, language}
    trigger: dict  # {type, utterance, ts}
    financial_snapshot: dict  # {monthly_income, monthly_surplus, idle_balance, external_holdings, liabilities}
    risk: dict  # {capacity_score, tolerance_score, band}
    goals: list[dict]  # [{name, horizon_years, target}]
    suitability: dict  # {recommended_shelf: [...], excluded: [...], reasons: [...]}
    next_best_action: str
    consent: dict  # {aa_consent_id | None, advice_consent: bool}
    priority_score: int  # 5..99
    created_at: datetime
    # A card lead built for a not-yet-eligible product (e.g. an NRI's secured-card
    # path before the qualifying deposit is AA-visible) is tagged so the RM never
    # mistakes it for an approval-ready application.
    tag: Literal["standard", "exploratory_not_yet_eligible"] = "standard"
    eligibility_context: dict | None = None


class Product(BaseModel):
    """Product-catalogue entry."""

    id: str
    name: str
    tag: Literal["vanilla", "regulated"]
    category: str  # deposit|mutual_fund|bond|govt_scheme|pms|aif|structured|insurance|portfolio
    min_amount: int
    expected_return: str  # display string, e.g. "7.4% p.a."
    description: str


class Receipt(BaseModel):
    """Confirmation record for an executed vanilla-product purchase."""

    receipt_id: str
    session_id: str
    product_id: str
    product_name: str
    amount: int
    executed_at: datetime
    audit_ref: str


class Nudge(BaseModel):
    """Proactive, event-driven message surfaced to a customer."""

    id: str
    persona_id: str
    kind: Literal["functional", "relational"]
    intent: Literal["motivational", "protective", "opportunity", "contextual", "literacy", "celebration"]
    title: str
    body: str
    language: str
    source_metric_ids: list[str]
    created_at: datetime


class AuditEntry(BaseModel):
    """Append-only audit-trail entry; see app.core.audit.

    Frozen: a recorded entry can never be altered in place, only appended.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    session_id: str
    ts: datetime
    kind: Literal["tool_call", "llm_call", "routing", "guardrail", "execution", "consent"]
    name: str
    inputs: dict
    outputs_summary: dict
    refs: list[str]


class FeatureMatrix(BaseModel):
    """Side-by-side product comparison, values looked up not computed."""

    product_ids: list[str]
    rows: list[dict]  # [{feature: "min_amount", values: {product_id: display_str}}] — looked-up only


# --- Persona JSON schema (data/synthetic/<id>.json) ---
#
# Real persona files carry a few legacy fields beyond this schema (e.g.
# `city_tier`, `employment`, `idle_balance` on the profile). These models
# tolerate and drop unknown fields rather than rejecting the file.


class _PersonaFileModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class PersonaProfile(_PersonaFileModel):
    id: str
    name: str
    age: int
    city: str
    segment: str
    language: str
    risk_tolerance: str
    dependents: int
    occupation: str
    avatar: str
    story: str


class Transaction(_PersonaFileModel):
    id: str
    date: date
    amount: float
    type: Literal["credit", "debit"]
    category: str
    description: str
    account: Literal["sa", "ca", "cc"]


class Goal(_PersonaFileModel):
    name: str
    horizon_years: int
    target: float
    saved_so_far: float


class ExternalHolding(_PersonaFileModel):
    id: str
    type: str
    institution: str
    amount: float
    rate: float | None = None  # not every holding type (e.g. equity) has a fixed rate


class ExternalLiability(_PersonaFileModel):
    id: str
    type: str
    lender: str
    principal: float
    rate: float
    emi: float


class PersonaExternal(_PersonaFileModel):
    aa_available: bool
    connected: bool
    holdings: list[ExternalHolding]
    liabilities: list[ExternalLiability]


class PersonaData(_PersonaFileModel):
    profile: PersonaProfile
    transactions: list[Transaction]
    goals: list[Goal]
    external: PersonaExternal


def load_personas(dir: Path) -> dict[str, PersonaData]:
    """Load every `<id>.json` file in `dir` into a `PersonaData`, keyed by filename stem.

    Raises `pydantic.ValidationError` (or `json.JSONDecodeError` for malformed JSON)
    on the first bad file — the caller decides whether that's fatal.
    """
    personas: dict[str, PersonaData] = {}
    for path in sorted(dir.glob("*.json")):
        raw = json.loads(path.read_text())
        personas[path.stem] = PersonaData.model_validate(raw)
    return personas
