"""Trigger/generator unit tests (Task 13) — each function in isolation, with
lightweight synthetic `Metric`s/personas so the assertions are exact and
don't depend on the shape of the seed data files.
"""

from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.domain.models import Metric
from app.nudges import triggers

_AS_OF = date(2026, 7, 1)
_COMPUTED_AT = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _metric(metric_id: str, value) -> Metric:
    return Metric(
        id=metric_id, value=value, unit="json", as_of=_AS_OF,
        source_refs=[], method="test_v1", input_hash="x", computed_at=_COMPUTED_AT,
    )


def _metrics(**values) -> dict[str, Metric]:
    return {k: _metric(k, v) for k, v in values.items()}


# --- idle_balance_high --------------------------------------------------------


def test_idle_balance_high_fires_when_over_2x_surplus_and_25k():
    metrics = _metrics(idle_balance=100_000.0, monthly_surplus=20_000.0)
    c = triggers.idle_balance_high(metrics)
    assert c is not None
    assert c.kind == "functional" and c.intent == "opportunity"
    assert c.amount == 100_000.0
    assert c.facts == {"idle_balance": 100_000.0, "monthly_surplus": 20_000.0}


def test_idle_balance_high_silent_below_threshold():
    metrics = _metrics(idle_balance=20_000.0, monthly_surplus=15_000.0)  # < 25k floor
    assert triggers.idle_balance_high(metrics) is None

    metrics2 = _metrics(idle_balance=40_000.0, monthly_surplus=25_000.0)  # not > 2x surplus
    assert triggers.idle_balance_high(metrics2) is None


# --- salary_credit_moment ------------------------------------------------------


def test_salary_credit_moment_fires_on_salary_consistent_flag():
    metrics = _metrics(
        behaviour_flags={"flags": ["salary_consistent"]}, monthly_surplus=15_000.0, monthly_income=80_000.0,
    )
    c = triggers.salary_credit_moment(metrics)
    assert c is not None
    assert c.intent == "opportunity" and c.template_id == "sip_due"
    assert c.amount == 15_000.0


def test_salary_credit_moment_silent_without_flag():
    metrics = _metrics(behaviour_flags={"flags": ["irregular_income"]}, monthly_surplus=1000.0, monthly_income=5000.0)
    assert triggers.salary_credit_moment(metrics) is None


# --- goal_drift / goal_celebration ---------------------------------------------


def _goal(name, ratio, required=1000.0):
    return {"name": name, "progress_ratio": ratio, "monthly_required_inr": required}


def test_goal_drift_fires_below_40_percent_per_goal():
    metrics = _metrics(goal_progress={"goals": [_goal("A", 0.1), _goal("B", 0.5), _goal("C", 0.39)]})
    hits = triggers.goal_drift(metrics)
    assert {c.facts["goal_name"] for c in hits} == {"A", "C"}
    assert {c.nonce for c in hits} == {"0", "2"}
    assert all(c.intent == "motivational" for c in hits)


def test_goal_celebration_fires_above_60_percent_per_goal():
    metrics = _metrics(goal_progress={"goals": [_goal("A", 0.61), _goal("B", 0.5), _goal("C", 0.9)]})
    hits = triggers.goal_celebration(metrics)
    assert {c.facts["goal_name"] for c in hits} == {"A", "C"}
    assert all(c.kind == "relational" and c.intent == "celebration" for c in hits)


def test_goal_drift_and_celebration_disjoint_bands():
    # nothing between 0.4 and 0.6 (inclusive of 0.4, exclusive of >0.6) fires either.
    metrics = _metrics(goal_progress={"goals": [_goal("A", 0.4), _goal("B", 0.6)]})
    assert triggers.goal_drift(metrics) == []
    assert triggers.goal_celebration(metrics) == []


# --- tax_window -----------------------------------------------------------------


def test_tax_window_fires_jan_through_mar_only():
    for month in (1, 2, 3):
        assert triggers.tax_window(datetime(2026, month, 15)) is not None
    for month in (4, 6, 7, 12):
        assert triggers.tax_window(datetime(2026, month, 15)) is None


# --- fd_maturity (documented no-op against the current schema) -----------------


def test_fd_maturity_empty_when_not_connected():
    persona = SimpleNamespace(external=SimpleNamespace(connected=False, holdings=[]))
    assert triggers.fd_maturity(persona) == []


def test_fd_maturity_empty_without_maturity_metadata():
    holding = SimpleNamespace(id="h1", type="FD", institution="HDFC Bank", amount=100_000.0, rate=7.0)
    persona = SimpleNamespace(external=SimpleNamespace(connected=True, holdings=[holding]))
    assert triggers.fd_maturity(persona) == []  # no maturity_date attribute -> silently skipped


def test_fd_maturity_fires_when_metadata_present():
    # Proves the logic works the day `maturity_date` metadata exists, even
    # though today's `ExternalHolding` schema drops it.
    holding = SimpleNamespace(
        id="h1", type="FD", institution="HDFC Bank", amount=100_000.0, rate=7.0,
        maturity_date=date(2026, 8, 1),
    )
    persona = SimpleNamespace(external=SimpleNamespace(connected=True, holdings=[holding]))
    hits = triggers.fd_maturity(persona)
    assert len(hits) == 1
    assert hits[0].facts == {"institution": "HDFC Bank", "amount": 100_000.0}
    assert hits[0].source_metric_ids == ["h1"]


# --- external_refinance ----------------------------------------------------------


def _inefficiency(available=True, underperforming=None, refinanceable=None, impact=0.0):
    return {
        "available": available,
        "underperforming_holdings": underperforming or [],
        "refinanceable_liabilities": refinanceable or [],
        "estimated_annual_impact_inr": impact,
    }


def test_external_refinance_none_when_not_connected():
    persona = SimpleNamespace(external=SimpleNamespace(connected=False))
    metrics = _metrics(external_inefficiency=_inefficiency())
    assert triggers.external_refinance(metrics, persona) is None


def test_external_refinance_none_when_connected_but_nothing_inefficient():
    persona = SimpleNamespace(external=SimpleNamespace(connected=True))
    metrics = _metrics(external_inefficiency=_inefficiency(available=True))
    assert triggers.external_refinance(metrics, persona) is None


def test_external_refinance_fires_on_underperforming_fd_or_refinanceable_loan():
    persona = SimpleNamespace(external=SimpleNamespace(connected=True))
    metrics = _metrics(external_inefficiency=_inefficiency(
        underperforming=[{"holding_id": "hold-1", "type": "FD", "rate": 7.0, "benchmark": 7.25}],
        refinanceable=[{"liability_id": "liab-1", "type": "personal_loan", "rate": 14.0, "benchmark": 10.5}],
        impact=19000.0,
    ))
    c = triggers.external_refinance(metrics, persona)
    assert c is not None
    assert c.amount == 19000.0
    assert c.source_metric_ids == ["external_inefficiency", "hold-1", "liab-1"]


# --- overspend_vs_baseline --------------------------------------------------------


def _txn(id_, month_day, amount, description):
    return SimpleNamespace(id=id_, date=date(2026, *month_day), amount=amount, type="debit", description=description)


def test_overspend_vs_baseline_fires_on_a_category_spike():
    txns = [
        _txn("t1", (5, 1), 1000.0, "swiggy order"),
        _txn("t2", (6, 1), 1000.0, "swiggy order"),
        _txn("t3", (7, 1), 5000.0, "swiggy order"),  # latest month, 5x baseline
    ]
    persona = SimpleNamespace(transactions=txns)
    c = triggers.overspend_vs_baseline(persona)
    assert c is not None
    assert c.facts["category"] == "food"
    assert c.facts["current_month_spend"] == 5000.0
    assert c.amount == 5000.0 - 1000.0


def test_overspend_vs_baseline_silent_without_a_prior_month_to_compare():
    txns = [_txn("t1", (7, 1), 5000.0, "swiggy order")]
    persona = SimpleNamespace(transactions=txns)
    assert triggers.overspend_vs_baseline(persona) is None


def test_overspend_vs_baseline_silent_when_consistent():
    txns = [
        _txn("t1", (5, 1), 1000.0, "swiggy order"),
        _txn("t2", (6, 1), 1100.0, "swiggy order"),
        _txn("t3", (7, 1), 1050.0, "swiggy order"),
    ]
    persona = SimpleNamespace(transactions=txns)
    assert triggers.overspend_vs_baseline(persona) is None


# --- emi_stress_protective ---------------------------------------------------------


def test_emi_stress_protective_fires_on_emi_stressed_or_overdraft():
    for flags in (["emi_stressed"], ["overdraft"], ["emi_stressed", "overdraft"]):
        metrics = _metrics(behaviour_flags={"flags": flags}, emi_ratio=0.5, monthly_surplus=1000.0)
        c = triggers.emi_stress_protective(metrics)
        assert c is not None and c.intent == "protective"


def test_emi_stress_protective_silent_otherwise():
    metrics = _metrics(behaviour_flags={"flags": ["salary_consistent"]}, emi_ratio=0.1, monthly_surplus=1000.0)
    assert triggers.emi_stress_protective(metrics) is None


# --- relational generators ---------------------------------------------------------


def test_monthly_money_story_picks_top_category():
    metrics = _metrics(
        monthly_income=80_000.0, monthly_surplus=20_000.0, savings_rate=0.25,
        spend_by_category={"food": 5000.0, "rent": 25000.0},
    )
    c = triggers.monthly_money_story(metrics)
    assert c is not None
    assert c.kind == "relational"
    assert c.facts["top_category"] == "rent"


def test_literacy_micro_lesson_rotates_by_day_of_year():
    a = triggers.literacy_micro_lesson(datetime(2026, 1, 1))
    b = triggers.literacy_micro_lesson(datetime(2026, 1, 2))
    assert a.template_id.startswith("literacy_")
    assert a.template_id != b.template_id  # adjacent days land on different topics


def test_festival_tip_windows_including_year_wrap():
    assert triggers.festival_tip(datetime(2026, 10, 20)).template_id == "diwali_budgeting"
    assert triggers.festival_tip(datetime(2026, 12, 30)).template_id == "new_year_planning"
    assert triggers.festival_tip(datetime(2027, 1, 2)).template_id == "new_year_planning"  # wraps the year
    assert triggers.festival_tip(datetime(2026, 8, 10)).template_id == "independence_savings_pledge"
    assert triggers.festival_tip(datetime(2026, 7, 12)) is None
