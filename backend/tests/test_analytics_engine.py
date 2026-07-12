"""AnalyticsEngine interface contract: metric-id filtering, error handling,
provenance completeness (non-empty source_refs on every Metric), and
input_hash stability — using the lightweight `fixtures/personas` dir so these
tests are independent of the real synthetic dataset's exact figures.
"""

from pathlib import Path

import pytest

from app.analytics.engine import METRIC_IDS, AnalyticsEngine
from app.core.spaces import SpaceStore

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "personas"


@pytest.fixture
def space():
    store = SpaceStore(seed_dir=FIXTURES_DIR)
    return store.get(store.create_space())


@pytest.fixture
def engine() -> AnalyticsEngine:
    return AnalyticsEngine()


def test_metric_ids_matches_the_brief_exactly() -> None:
    assert list(METRIC_IDS) == [
        "monthly_income",
        "monthly_surplus",
        "idle_balance",
        "spend_by_category",
        "savings_rate",
        "salary_regularity",
        "behaviour_flags",
        "emi_ratio",
        "capacity_score",
        "tolerance_score",
        "risk_band",
        "suitability_segment",
        "net_worth",
        "asset_mix",
        "external_inefficiency",
        "goal_progress",
    ]


def test_compute_with_no_metric_ids_returns_all_of_them(engine, space) -> None:
    metrics = engine.compute(space, "ravi")

    assert [m.id for m in metrics] == list(METRIC_IDS)


def test_compute_with_explicit_metric_ids_returns_only_those_in_that_order(engine, space) -> None:
    metrics = engine.compute(space, "ravi", metric_ids=["risk_band", "monthly_income"])

    assert [m.id for m in metrics] == ["risk_band", "monthly_income"]


def test_compute_unknown_metric_id_raises_value_error(engine, space) -> None:
    with pytest.raises(ValueError):
        engine.compute(space, "ravi", metric_ids=["not_a_real_metric"])


def test_compute_unknown_persona_raises_key_error(engine, space) -> None:
    with pytest.raises(KeyError):
        engine.compute(space, "no-such-persona")


@pytest.mark.parametrize("persona_id", ["ravi", "priya"])
def test_every_metric_has_non_empty_source_refs(engine, space, persona_id) -> None:
    metrics = engine.compute(space, persona_id)

    for metric in metrics:
        assert metric.source_refs, f"{persona_id}/{metric.id} has empty source_refs"


@pytest.mark.parametrize("persona_id", ["ravi", "priya"])
def test_every_metric_has_a_method_and_input_hash(engine, space, persona_id) -> None:
    metrics = engine.compute(space, persona_id)

    for metric in metrics:
        assert metric.method
        assert len(metric.input_hash) == 64  # sha256 hex digest


def test_input_hash_is_stable_across_repeated_computation(engine, space) -> None:
    first = engine.compute(space, "ravi", metric_ids=["monthly_income", "capacity_score"])
    second = engine.compute(space, "ravi", metric_ids=["monthly_income", "capacity_score"])

    assert first[0].input_hash == second[0].input_hash
    assert first[1].input_hash == second[1].input_hash


def test_input_hash_is_stable_across_independent_spaces_with_same_seed(engine) -> None:
    store_a = SpaceStore(seed_dir=FIXTURES_DIR)
    store_b = SpaceStore(seed_dir=FIXTURES_DIR)
    space_a = store_a.get(store_a.create_space())
    space_b = store_b.get(store_b.create_space())

    metric_a = engine.compute(space_a, "ravi", metric_ids=["monthly_income"])[0]
    metric_b = engine.compute(space_b, "ravi", metric_ids=["monthly_income"])[0]

    assert metric_a.input_hash == metric_b.input_hash


@pytest.mark.parametrize("metric_id", ["idle_balance", "monthly_income", "net_worth"])
def test_input_hash_changes_when_a_txn_amount_changes(engine, space, metric_id) -> None:
    """Guards every hash-path class: cashflow builders hashing txn records
    (idle_balance, monthly_income) and networth's internal-leg derivation —
    mutating an amount while keeping the same txn ids MUST change the hash."""
    before = engine.compute(space, "ravi", metric_ids=[metric_id])[0]

    space.personas["ravi"].transactions[0].amount = 999999.0

    after = engine.compute(space, "ravi", metric_ids=[metric_id])[0]
    assert before.value != after.value  # the mutation genuinely moved the metric
    assert before.input_hash != after.input_hash


def test_net_worth_and_asset_mix_exclude_external_until_connected(engine, space) -> None:
    metrics = {m.id: m for m in engine.compute(space, "ravi")}

    assert metrics["net_worth"].value["external_connected"] is False
    assert metrics["net_worth"].value["external"] == 0.0
    assert "mutual_fund" not in metrics["asset_mix"].value

    space.personas["ravi"].external.connected = True
    metrics_connected = {m.id: m for m in engine.compute(space, "ravi")}

    assert metrics_connected["net_worth"].value["external_connected"] is True
    assert metrics_connected["net_worth"].value["external"] == 50000.0
    assert metrics_connected["asset_mix"].value["mutual_fund"] == 50000.0


def test_external_inefficiency_reports_consent_gated_when_not_connected(engine, space) -> None:
    metrics = {m.id: m for m in engine.compute(space, "priya")}

    assert metrics["external_inefficiency"].value == {"available": False}
    assert "consent_gated" in metrics["external_inefficiency"].method


def test_goal_progress_handles_persona_with_no_goals(engine, space) -> None:
    space.personas["priya"].goals = []
    metrics = {m.id: m for m in engine.compute(space, "priya")}

    assert metrics["goal_progress"].value == {"goals": []}
    assert metrics["goal_progress"].source_refs  # still non-empty


def test_as_of_is_the_persona_last_transaction_date(engine, space) -> None:
    metrics = engine.compute(space, "ravi")
    ravi = space.personas["ravi"]
    expected_last_date = max(t.date for t in ravi.transactions)

    assert all(m.as_of == expected_last_date for m in metrics)
