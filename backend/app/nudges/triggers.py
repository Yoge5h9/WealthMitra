"""Deterministic trigger/generator detection for the nudge engine (Task 13).

Every function here is a pure read over `Metric`s (already computed by
`AnalyticsEngine`) and/or the persona's own data — none of them call an LLM or
invent a figure. Each hit is returned as a `Candidate`: enough to render a
deterministic i18n template (`app.nudges.templates`) and to build the
guardrail's allowed-figure set, before any LLM ever sees it.

Two trigger families:
  * "functional" — task-oriented, may include a selling nudge (`opportunity`)
    or a supportive one (`protective`, `motivational`, `contextual`).
  * "relational" — never selling: recaps, literacy, celebration, seasonal tips.

`app.nudges.engine` is the only caller; it owns quota/ordering/distress
policy. This module only detects candidates — it never drops or reorders them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.analytics.categorize import categorize
from app.analytics.constants import (
    IDBI_FD_BENCHMARK_RATE_PCT,
    IDBI_LOAN_REFINANCE_BENCHMARK_RATE_PCT,
)
from app.domain.models import Metric, PersonaData

IDLE_BALANCE_SURPLUS_MULTIPLIER = 2.0
IDLE_BALANCE_MIN_INR = 25_000.0

GOAL_DRIFT_MAX_RATIO = 0.4
GOAL_CELEBRATE_MIN_RATIO = 0.6

TAX_WINDOW_MONTHS = frozenset({1, 2, 3})

OVERSPEND_RATIO_MULTIPLIER = 1.5
OVERSPEND_MIN_ABS_INR = 2_000.0

_LITERACY_TOPICS: tuple[str, ...] = (
    "emergency_fund", "power_of_sip", "diversification", "credit_score",
)

# (start (month, day), end (month, day), template_id). Inclusive; a window
# whose end is numerically before its start wraps the calendar year
# (e.g. Dec 25 -> Jan 5).
_FESTIVAL_WINDOWS: tuple[tuple[tuple[int, int], tuple[int, int], str], ...] = (
    ((10, 15), (11, 15), "diwali_budgeting"),
    ((12, 25), (1, 5), "new_year_planning"),
    ((8, 1), (8, 15), "independence_savings_pledge"),
)


@dataclass(frozen=True)
class Candidate:
    """One detected nudge, pre-copy: deterministic facts only."""

    kind: str  # "functional" | "relational"
    intent: str  # motivational|protective|opportunity|contextual|literacy|celebration
    template_id: str
    facts: dict = field(default_factory=dict)
    source_metric_ids: list[str] = field(default_factory=list)
    amount: float = 0.0  # ordering key for opportunity nudges; 0 elsewhere
    nonce: str = ""  # disambiguates multiple hits of the same template (e.g. per-goal)


def _flags(metrics: dict[str, Metric]) -> list[str]:
    return list(metrics["behaviour_flags"].value.get("flags", []))


# --- functional triggers -----------------------------------------------------


def idle_balance_high(metrics: dict[str, Metric]) -> Candidate | None:
    idle = float(metrics["idle_balance"].value)
    surplus = float(metrics["monthly_surplus"].value)
    if idle > IDLE_BALANCE_SURPLUS_MULTIPLIER * surplus and idle > IDLE_BALANCE_MIN_INR:
        return Candidate(
            kind="functional", intent="opportunity", template_id="idle_balance_high",
            facts={"idle_balance": idle, "monthly_surplus": surplus},
            source_metric_ids=["idle_balance", "monthly_surplus"], amount=idle,
        )
    return None


def salary_credit_moment(metrics: dict[str, Metric]) -> Candidate | None:
    """AKA sip_due: fires on the same salary-consistent signal the suitability
    matrix already uses to steer this persona toward structured SIPs."""
    if "salary_consistent" not in _flags(metrics):
        return None
    surplus = float(metrics["monthly_surplus"].value)
    income = float(metrics["monthly_income"].value)
    return Candidate(
        kind="functional", intent="opportunity", template_id="sip_due",
        facts={"monthly_surplus": surplus, "monthly_income": income},
        source_metric_ids=["behaviour_flags", "monthly_surplus", "monthly_income"], amount=surplus,
    )


def goal_drift(metrics: dict[str, Metric]) -> list[Candidate]:
    goals = metrics["goal_progress"].value.get("goals", [])
    out: list[Candidate] = []
    for idx, g in enumerate(goals):
        if g["progress_ratio"] < GOAL_DRIFT_MAX_RATIO:
            out.append(Candidate(
                kind="functional", intent="motivational", template_id="goal_drift",
                facts={
                    "goal_name": g["name"], "progress_ratio": g["progress_ratio"],
                    "monthly_required_inr": g["monthly_required_inr"],
                },
                source_metric_ids=["goal_progress"], amount=float(g["monthly_required_inr"]), nonce=str(idx),
            ))
    return out


def tax_window(now: datetime) -> Candidate | None:
    if now.month not in TAX_WINDOW_MONTHS:
        return None
    return Candidate(kind="functional", intent="opportunity", template_id="tax_window")


def fd_maturity(persona: PersonaData) -> list[Candidate]:
    """Near-maturity FD reminder from holding metadata.

    `ExternalHolding` does not carry a maturity date
    field today — any such key in the seed JSON is silently dropped by
    `extra="ignore"` validation, so this is a documented no-op against the
    current schema. Written defensively (`getattr`, never assumes the
    attribute exists) so it activates for free the day a maturity field is
    added, without another code change.
    """
    if not persona.external.connected:
        return []
    out: list[Candidate] = []
    for h in persona.external.holdings:
        if h.type != "FD":
            continue
        maturity = getattr(h, "maturity_date", None)
        if maturity is None:
            continue
        out.append(Candidate(
            kind="functional", intent="opportunity", template_id="fd_maturity",
            facts={"institution": h.institution, "amount": h.amount},
            source_metric_ids=[h.id], amount=float(h.amount), nonce=h.id,
        ))
    return out


def external_refinance(metrics: dict[str, Metric], persona: PersonaData) -> Candidate | None:
    """Out-of-bank optimisation opportunity: an underperforming FD (below the
    IDBI benchmark rate) or a refinanceable liability (above the IDBI
    refinance benchmark) — both signals `external_inefficiency` already
    unifies into one estimated annual impact.
    """
    if not persona.external.connected:
        return None
    inefficiency = metrics["external_inefficiency"].value
    if not inefficiency.get("available"):
        return None
    underperforming = inefficiency.get("underperforming_holdings", [])
    refinanceable = inefficiency.get("refinanceable_liabilities", [])
    if not underperforming and not refinanceable:
        return None
    impact = float(inefficiency.get("estimated_annual_impact_inr", 0))
    ids = [h["holding_id"] for h in underperforming] + [l["liability_id"] for l in refinanceable]
    return Candidate(
        kind="functional", intent="opportunity", template_id="external_refinance",
        facts={
            "estimated_annual_impact_inr": impact,
            "underperforming_count": len(underperforming),
            "refinanceable_count": len(refinanceable),
            "fd_benchmark_pct": IDBI_FD_BENCHMARK_RATE_PCT,
            "loan_benchmark_pct": IDBI_LOAN_REFINANCE_BENCHMARK_RATE_PCT,
        },
        source_metric_ids=["external_inefficiency", *ids], amount=impact,
    )


def overspend_vs_baseline(persona: PersonaData) -> Candidate | None:
    """Month-over-month category overspend, computed straight from the
    ledger (not `spend_by_category`, which is a whole-window monthly
    average — see `cashflow.py`'s own `idle_balance` deviation note for the
    same "the metric we have isn't the granularity this needs" situation).
    Flags the worst-overage category vs its average in every OTHER observed
    month, when it exceeds both a relative (1.5x) and absolute (₹2,000) bar.
    """
    txns = persona.transactions
    debits = [t for t in txns if t.type == "debit"]
    if not debits:
        return None
    latest_month = max(t.date for t in txns).isoformat()[:7]

    current: dict[str, float] = {}
    baseline_totals: dict[str, float] = {}
    baseline_ids: dict[str, list[str]] = {}
    other_months: set[str] = set()
    current_ids: dict[str, list[str]] = {}
    for t in debits:
        month_key = t.date.isoformat()[:7]
        cat = categorize(t.description)
        if month_key == latest_month:
            current[cat] = current.get(cat, 0.0) + t.amount
            current_ids.setdefault(cat, []).append(t.id)
        else:
            baseline_totals[cat] = baseline_totals.get(cat, 0.0) + t.amount
            baseline_ids.setdefault(cat, []).append(t.id)
            other_months.add(month_key)

    if not other_months:
        return None
    n_other = len(other_months)

    best: tuple[str, float, float, float] | None = None  # category, overage, current, baseline
    for cat, cur_total in current.items():
        baseline = baseline_totals.get(cat, 0.0) / n_other
        if baseline <= 0:
            continue
        overage = cur_total - baseline
        if cur_total > baseline * OVERSPEND_RATIO_MULTIPLIER and overage > OVERSPEND_MIN_ABS_INR:
            if best is None or overage > best[1]:
                best = (cat, overage, cur_total, baseline)

    if best is None:
        return None
    cat, overage, cur_total, baseline = best
    refs = current_ids.get(cat, [])
    return Candidate(
        kind="functional", intent="contextual", template_id="overspend_vs_baseline",
        facts={"category": cat, "current_month_spend": cur_total, "baseline_spend": round(baseline)},
        source_metric_ids=["spend_by_category", *refs], amount=overage,
    )


def emi_stress_protective(metrics: dict[str, Metric]) -> Candidate | None:
    flags = _flags(metrics)
    if "emi_stressed" not in flags and "overdraft" not in flags:
        return None
    emi_ratio = float(metrics["emi_ratio"].value)
    surplus = float(metrics["monthly_surplus"].value)
    return Candidate(
        kind="functional", intent="protective", template_id="emi_stress_protective",
        facts={"emi_ratio": emi_ratio, "monthly_surplus": surplus},
        source_metric_ids=["behaviour_flags", "emi_ratio", "monthly_surplus"],
    )


# --- relational generators ---------------------------------------------------


def monthly_money_story(metrics: dict[str, Metric]) -> Candidate | None:
    income = float(metrics["monthly_income"].value)
    spend = dict(metrics["spend_by_category"].value)
    if income <= 0 and not spend:
        return None
    surplus = float(metrics["monthly_surplus"].value)
    savings_rate = float(metrics["savings_rate"].value)
    top_category = max(spend.items(), key=lambda kv: kv[1])[0] if spend else "general"
    return Candidate(
        kind="relational", intent="motivational", template_id="monthly_money_story",
        facts={
            "monthly_income": income, "monthly_surplus": surplus,
            "savings_rate": savings_rate, "top_category": top_category,
        },
        source_metric_ids=["monthly_income", "monthly_surplus", "savings_rate", "spend_by_category"],
    )


def literacy_micro_lesson(now: datetime) -> Candidate:
    """Rotates through a small curated table by day-of-year — no persisted
    state needed to avoid repeating the same tip on back-to-back calls the
    same day, and it naturally cycles day to day.
    """
    topic = _LITERACY_TOPICS[now.timetuple().tm_yday % len(_LITERACY_TOPICS)]
    return Candidate(kind="relational", intent="literacy", template_id=f"literacy_{topic}")


def goal_celebration(metrics: dict[str, Metric]) -> list[Candidate]:
    goals = metrics["goal_progress"].value.get("goals", [])
    out: list[Candidate] = []
    for idx, g in enumerate(goals):
        if g["progress_ratio"] > GOAL_CELEBRATE_MIN_RATIO:
            out.append(Candidate(
                kind="relational", intent="celebration", template_id="goal_celebration",
                facts={"goal_name": g["name"], "progress_ratio": g["progress_ratio"]},
                source_metric_ids=["goal_progress"], nonce=str(idx),
            ))
    return out


def _in_window(month: int, day: int, start: tuple[int, int], end: tuple[int, int]) -> bool:
    today = (month, day)
    if start <= end:
        return start <= today <= end
    return today >= start or today <= end  # wraps year boundary (e.g. Dec 25 -> Jan 5)


def festival_tip(now: datetime) -> Candidate | None:
    for start, end, template_id in _FESTIVAL_WINDOWS:
        if _in_window(now.month, now.day, start, end):
            return Candidate(kind="relational", intent="contextual", template_id=template_id)
    return None


__all__ = [
    "Candidate",
    "idle_balance_high",
    "salary_credit_moment",
    "goal_drift",
    "tax_window",
    "fd_maturity",
    "external_refinance",
    "overspend_vs_baseline",
    "emi_stress_protective",
    "monthly_money_story",
    "literacy_micro_lesson",
    "goal_celebration",
    "festival_tip",
]
