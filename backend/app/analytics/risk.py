"""Two-axis risk scoring: `capacity_score` (data-derived affordability) and
`tolerance_score` (profile-declared appetite), reconciled via
`risk_band = f(min(capacity, tolerance))` — a persona never gets steered into
a band their cash flow can't support, even if their stated risk appetite is
aggressive (and vice versa).
"""

from __future__ import annotations

from app.domain.models import PersonaProfile

from .cashflow import CashflowBundle
from .constants import (
    CAPACITY_BASE,
    CAPACITY_DEPENDENT_PENALTY,
    CAPACITY_EMI_RATIO_WEIGHT,
    CAPACITY_EMI_STRESSED_PENALTY,
    CAPACITY_MAX,
    CAPACITY_MIN,
    CAPACITY_OVERDRAFT_PENALTY,
    CAPACITY_REGULARITY_WEIGHT,
    CAPACITY_SURPLUS_RATIO_CAP,
    CAPACITY_SURPLUS_RATIO_WEIGHT,
    MetricParts,
    RISK_BAND_CONSERVATIVE_MAX,
    RISK_BAND_MODERATE_MAX,
    TOLERANCE_BY_RISK_APPETITE,
    TOLERANCE_DEFAULT,
)


def _capacity_raw(profile: PersonaProfile, bundle: CashflowBundle) -> float:
    surplus_ratio = (bundle.monthly_surplus / bundle.monthly_income) if bundle.monthly_income > 0 else 0.0
    capped_surplus_ratio = min(max(surplus_ratio, 0.0), CAPACITY_SURPLUS_RATIO_CAP)

    capacity = CAPACITY_BASE
    capacity += capped_surplus_ratio / CAPACITY_SURPLUS_RATIO_CAP * CAPACITY_SURPLUS_RATIO_WEIGHT
    capacity += bundle.salary_regularity * CAPACITY_REGULARITY_WEIGHT
    capacity -= bundle.emi_ratio * CAPACITY_EMI_RATIO_WEIGHT
    capacity -= profile.dependents * CAPACITY_DEPENDENT_PENALTY
    if "emi_stressed" in bundle.behaviour_flags:
        capacity -= CAPACITY_EMI_STRESSED_PENALTY
    if "overdraft" in bundle.behaviour_flags:
        capacity -= CAPACITY_OVERDRAFT_PENALTY
    return capacity


def capacity_score_parts(profile: PersonaProfile, bundle: CashflowBundle) -> MetricParts:
    raw = _capacity_raw(profile, bundle)
    score = int(max(CAPACITY_MIN, min(CAPACITY_MAX, round(raw))))
    refs = bundle.credit_ids + bundle.category_debit_ids.get("emi", [])
    return MetricParts(
        value=float(score),
        unit="score",
        source_refs=refs or [f"profile:{bundle.persona_id}:dependents"],
        method="capacity_score_v1",
        inputs={
            "monthly_income": bundle.monthly_income,
            "monthly_surplus": bundle.monthly_surplus,
            "salary_regularity": bundle.salary_regularity,
            "emi_ratio": bundle.emi_ratio,
            "dependents": profile.dependents,
            "behaviour_flags": bundle.behaviour_flags,
        },
    )


def tolerance_score_parts(profile: PersonaProfile) -> MetricParts:
    score = TOLERANCE_BY_RISK_APPETITE.get(profile.risk_tolerance, TOLERANCE_DEFAULT)
    return MetricParts(
        value=float(score),
        unit="score",
        source_refs=[f"profile:{profile.id}:risk_tolerance"],
        method="tolerance_score_v1",
        inputs={"risk_tolerance": profile.risk_tolerance},
    )


def _band(score: float) -> str:
    if score < RISK_BAND_CONSERVATIVE_MAX:
        return "conservative"
    if score < RISK_BAND_MODERATE_MAX:
        return "moderate"
    return "growth"


def risk_band_parts(capacity: MetricParts, tolerance: MetricParts) -> MetricParts:
    band_score = min(capacity.value, tolerance.value)  # type: ignore[type-var]
    band = _band(band_score)
    refs = list(dict.fromkeys(capacity.source_refs + tolerance.source_refs))
    return MetricParts(
        value=band,
        unit="label",
        source_refs=refs,
        method="risk_band_v1",
        inputs={"capacity_score": capacity.value, "tolerance_score": tolerance.value},
    )
