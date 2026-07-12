"""Persona x credit-card eligibility spread — the honest, source-backed matrix
demoed to judges: real seed data run through the real (unmocked)
`evaluate_card_eligibility`, not a hand-built fixture.

The contract: some personas clearly qualify for the unsecured shelf, one is
genuinely age-limited, and the NRI persona (Arjun) demonstrates the
AA-not-connected -> later-unlock story for the secured card — his qualifying
IDBI deposit only becomes visible to `evaluate_card_eligibility` once
`external.connected` is true (see `app/agent/orchestrator.py`, which only
passes `external_holdings` in that case).
"""

from pathlib import Path

import pytest

from app.catalogue.recommendations import evaluate_card_eligibility
from app.core.spaces import SpaceStore

REAL_SYNTHETIC_DIR = Path(__file__).resolve().parents[2] / "data" / "synthetic"
pytestmark = pytest.mark.skipif(not REAL_SYNTHETIC_DIR.is_dir(), reason="data/synthetic/ not present")

UNSECURED_CARD_IDS = [
    "idbi_aspire_platinum",
    "idbi_royale_signature",
    "idbi_euphoria_world",
    "idbi_winnings",
]
SECURED_CARD_ID = "idbi_imperium_platinum"


@pytest.fixture
def space():
    store = SpaceStore()
    return store.get(store.create_space())


def _statuses(space, persona_id: str, *, metrics: dict | None = None) -> dict:
    persona = space.personas[persona_id]
    results = evaluate_card_eligibility(persona.profile, metrics)
    return {r["card_id"]: r for r in results}


# --- working-age residents: a genuine, honest "eligible" spread ---


@pytest.mark.parametrize("persona_id", ["ravi", "devika", "meera", "priya", "vikram"])
def test_working_age_residents_are_unsecured_eligible(space, persona_id) -> None:
    results = _statuses(space, persona_id)
    for card_id in UNSECURED_CARD_IDS:
        assert results[card_id]["status"] == "eligible", f"{persona_id}/{card_id}: {results[card_id]}"


# --- shanta: genuinely age-limited (61 > the salaried max_age of 60) ---


def test_shanta_is_ineligible_on_age_for_every_unsecured_card(space) -> None:
    results = _statuses(space, "shanta")
    for card_id in UNSECURED_CARD_IDS:
        assert results[card_id]["status"] == "ineligible"
        assert "age" in results[card_id]["reason"].lower()
    # Her real holding is an SBI FD, not IDBI -> the secured path stalls too.
    assert results[SECURED_CARD_ID]["status"] == "needs_more_data"


# --- arjun: NRI residency gate, with the Imperium secured-card alternative ---


def test_arjun_is_unsecured_ineligible_on_residency_with_imperium_alternative(space) -> None:
    results = _statuses(space, "arjun")
    for card_id in UNSECURED_CARD_IDS:
        assert results[card_id]["status"] == "ineligible"
        assert "resident" in results[card_id]["reason"].lower() or "NRI" in results[card_id]["reason"]
        assert results[card_id]["alternative"] is not None
        assert results[card_id]["alternative"]["card_id"] == SECURED_CARD_ID


def test_arjun_imperium_needs_more_data_without_aa_connected(space) -> None:
    # No metrics passed == the live orchestrator's pre-AA-connect shape.
    results = _statuses(space, "arjun")
    assert results[SECURED_CARD_ID]["status"] == "needs_more_data"
    assert results[SECURED_CARD_ID]["alternative"] is None


def test_arjun_imperium_flips_eligible_once_aa_surfaces_his_idbi_deposit(space) -> None:
    persona = space.personas["arjun"]
    metrics = {"external_holdings": [h.model_dump(mode="json") for h in persona.external.holdings]}

    results = _statuses(space, "arjun", metrics=metrics)

    assert results[SECURED_CARD_ID]["status"] == "eligible"
    assert results[SECURED_CARD_ID]["reason"]
