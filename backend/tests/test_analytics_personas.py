"""Exact-math assertions per persona, against the real synthetic dataset.

Expected numbers were independently derived by running the ported formulas
(categorizer + salary-regularity + capacity/tolerance/band) against
`data/synthetic/*.json` before the engine was wired up, so these figures are
a pre-registered oracle, not back-solved from the implementation.
"""

from pathlib import Path

import pytest

from app.analytics.engine import AnalyticsEngine
from app.core.spaces import SpaceStore

REAL_SYNTHETIC_DIR = Path(__file__).resolve().parents[2] / "data" / "synthetic"
pytestmark = pytest.mark.skipif(not REAL_SYNTHETIC_DIR.is_dir(), reason="data/synthetic/ not present")


@pytest.fixture
def space():
    store = SpaceStore()
    return store.get(store.create_space())


@pytest.fixture
def engine() -> AnalyticsEngine:
    return AnalyticsEngine()


def _by_id(metrics) -> dict:
    return {m.id: m for m in metrics}


# --- ravi: steady salaried surplus -> auto SIP path ---


def test_ravi_exact_monthly_figures_and_surplus(engine, space) -> None:
    metrics = _by_id(engine.compute(space, "ravi"))

    assert metrics["monthly_income"].value == 85000.0
    assert metrics["monthly_surplus"].value == 20862.0
    assert metrics["salary_regularity"].value == 1.0
    assert metrics["behaviour_flags"].value == {"flags": ["salary_consistent"]}
    assert metrics["capacity_score"].value == 71.0
    assert metrics["tolerance_score"].value == 55.0
    assert metrics["risk_band"].value == "moderate"
    assert metrics["suitability_segment"].value == "mass_retail_salaried"


# --- vikram: EMI-stressed, overdraft -> distress path ---


def test_vikram_emi_stressed_and_overdraft_flags(engine, space) -> None:
    metrics = _by_id(engine.compute(space, "vikram"))

    assert metrics["emi_ratio"].value > 0.4
    flags = metrics["behaviour_flags"].value["flags"]
    assert "emi_stressed" in flags
    assert "overdraft" in flags
    assert metrics["capacity_score"].value == 15.0
    assert metrics["risk_band"].value == "conservative"
    assert metrics["suitability_segment"].value == "mass_retail_salaried"


# --- priya: gig worker, irregular income, no AA ---


def test_priya_irregular_income_no_salary_consistent(engine, space) -> None:
    metrics = _by_id(engine.compute(space, "priya"))

    flags = metrics["behaviour_flags"].value["flags"]
    assert "irregular_income" in flags
    assert "salary_consistent" not in flags
    assert metrics["salary_regularity"].value == 0.21


def test_priya_suitability_segment_reproduces_seed_via_documented_fallback(engine, space) -> None:
    metrics = _by_id(engine.compute(space, "priya"))
    segment_metric = metrics["suitability_segment"]

    # Priya's seeded profile.segment IS "mass_retail_gig"; the gig/irregular
    # branch can't be cleanly derived without `employment` (dropped by PersonaProfile),
    # so it falls back to the profile's own field — the method string must say so.
    assert segment_metric.value == "mass_retail_gig"
    assert segment_metric.value == space.personas["priya"].profile.segment
    assert "profile_fallback" in segment_metric.method


def test_priya_external_inefficiency_unavailable_without_aa(engine, space) -> None:
    metrics = _by_id(engine.compute(space, "priya"))

    assert metrics["external_inefficiency"].value == {"available": False}


# --- devika: HNI, external only counted post AA-connect ---


def test_devika_suitability_segment_is_hni(engine, space) -> None:
    metrics = _by_id(engine.compute(space, "devika"))
    assert metrics["suitability_segment"].value == "hni"


def test_devika_net_worth_excludes_external_until_connected(engine, space) -> None:
    before = _by_id(engine.compute(space, "devika"))["net_worth"]
    assert before.value["external_connected"] is False
    assert before.value["external"] == 0.0
    total_before = before.value["total"]

    space.personas["devika"].external.connected = True
    after = _by_id(engine.compute(space, "devika"))["net_worth"]

    assert after.value["external_connected"] is True
    assert after.value["external"] > 0.0
    assert after.value["total"] > total_before


def test_devika_external_inefficiency_flags_underperforming_fds_not_her_loan(engine, space) -> None:
    space.personas["devika"].external.connected = True
    metrics = _by_id(engine.compute(space, "devika"))
    result = metrics["external_inefficiency"].value

    assert result["available"] is True
    assert len(result["underperforming_holdings"]) == 2  # both FDs are below the 7.25% benchmark
    # Devika's business loan is at 9.5% — below the 10.5% refinance benchmark, so it's fine.
    assert result["refinanceable_liabilities"] == []


# --- meera: cash-surplus-heavy business owner -> RM equity lead ---


def test_meera_cash_surplus_heavy_and_affluent_segment(engine, space) -> None:
    metrics = _by_id(engine.compute(space, "meera"))

    assert "cash_surplus_heavy" in metrics["behaviour_flags"].value["flags"]
    assert metrics["monthly_surplus"].value == 454427.0
    assert metrics["suitability_segment"].value == "affluent"
    assert metrics["risk_band"].value == "growth"


# --- shanta: senior, conservative shelf ---


def test_shanta_suitability_segment_is_senior(engine, space) -> None:
    metrics = _by_id(engine.compute(space, "shanta"))

    assert metrics["suitability_segment"].value == "senior"
    assert metrics["risk_band"].value == "conservative"
    assert metrics["tolerance_score"].value == 25.0


# --- arjun: nri via external NRE holding ---


def test_arjun_suitability_segment_is_nri(engine, space) -> None:
    metrics = _by_id(engine.compute(space, "arjun"))
    assert metrics["suitability_segment"].value == "nri"


# --- vikram's external loan is refinanceable once connected ---


def test_vikram_external_inefficiency_flags_refinanceable_loan(engine, space) -> None:
    space.personas["vikram"].external.connected = True
    metrics = _by_id(engine.compute(space, "vikram"))
    result = metrics["external_inefficiency"].value

    assert result["available"] is True
    assert len(result["refinanceable_liabilities"]) == 1
    assert result["refinanceable_liabilities"][0]["liability_id"] == "liab-vikram-1"
    assert result["estimated_annual_impact_inr"] > 0


# --- suitability_segment reproduces every persona's seeded profile.segment ---


@pytest.mark.parametrize(
    "persona_id",
    ["ravi", "vikram", "priya", "devika", "meera", "shanta", "arjun"],
)
def test_suitability_segment_reproduces_seeded_segment_for_every_persona(engine, space, persona_id) -> None:
    metrics = _by_id(engine.compute(space, persona_id))
    seeded_segment = space.personas[persona_id].profile.segment

    assert metrics["suitability_segment"].value == seeded_segment


# --- goal progress: exact math for ravi's two goals ---


def test_ravi_goal_progress_exact_math(engine, space) -> None:
    metrics = _by_id(engine.compute(space, "ravi"))
    goals = metrics["goal_progress"].value["goals"]

    emergency = next(g for g in goals if g["name"] == "Emergency fund")
    assert emergency["target"] == 300000
    assert emergency["saved_so_far"] == 140000
    assert emergency["progress_ratio"] == pytest.approx(0.4667, abs=1e-4)
    assert emergency["monthly_required_inr"] == 13333

    retirement = next(g for g in goals if g["name"] == "Retirement corpus")
    assert retirement["progress_ratio"] == pytest.approx(0.012, abs=1e-4)
    assert retirement["monthly_required_inr"] == 65867
