"""Deterministic cash-flow aggregation: monthly income/spend/surplus,
categorized spend, salary regularity, emi ratio, and behaviour flags — all
derived from the persona's transaction ledger. `build_cashflow` runs the
aggregation once per `compute()` call; the `*_parts` functions below turn
pieces of that bundle into audited `MetricParts`.

Deliberate departure from a naive approach: `idle_balance` is NOT read from a
static `profile.idle_balance` field. The `PersonaProfile` model declares
`ConfigDict(extra="ignore")` and does not list `idle_balance` (nor
`city_tier`/`employment`) among its fields, so that data is silently dropped
during validation — it's unreachable from `PersonaData` by the time a `Space`
hands us a persona. Rather than re-parsing the persona JSON off disk (which
would duplicate the persona loader and could disagree with whatever `seed_dir`
a given `Space` was actually built from), `idle_balance` here is the ledger's
net cash position (Σcredits − Σdebits) over the observed transaction window —
a fully-computed, always-available substitute.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date

from app.domain.models import PersonaData

from .categorize import categorize
from .constants import (
    CASH_SURPLUS_HEAVY_ABS_INR,
    CASH_SURPLUS_HEAVY_RATIO_MIN,
    EMI_STRESSED_RATIO_MIN,
    IRREGULAR_INCOME_REGULARITY_MAX,
    MetricParts,
    OVERDRAFT_KEYWORD,
    PRIMARY_INCOME_CATEGORIES,
    SALARY_CONSISTENT_REGULARITY_MIN,
)


@dataclass(frozen=True)
class CashflowBundle:
    persona_id: str
    months: int
    last_txn_date: date
    all_txn_ids: list[str]
    credit_ids: list[str]
    debit_ids: list[str]
    monthly_income: float
    monthly_spend: float
    monthly_surplus: float
    categories_monthly: dict[str, float]  # category -> monthly average debit spend
    category_debit_ids: dict[str, list[str]]  # category -> contributing debit txn ids
    primary_income_category: str | None
    primary_income_credit_ids: list[str]
    salary_regularity: float
    emi_ratio: float
    behaviour_flags: list[str]
    overdraft_txn_ids: list[str]
    net_ledger_position: float  # Σcredits − Σdebits over the full window; substitutes idle_balance
    record_by_id: dict[str, dict]  # txn id -> {"amount","date","type"} — for input_hash payloads


def _rupee(value: float) -> float:
    """Round to the nearest whole rupee so every surface agrees."""
    return float(round(value))


def _coefficient_of_variation(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean = statistics.fmean(values)
    if mean <= 0:
        return 0.0
    return statistics.pstdev(values) / mean


def build_cashflow(persona: PersonaData) -> CashflowBundle:
    txns = persona.transactions
    months = max(len({t.date.isoformat()[:7] for t in txns}), 1)
    last_txn_date = max((t.date for t in txns), default=date.min)

    credits = [t for t in txns if t.type == "credit"]
    debits = [t for t in txns if t.type == "debit"]

    credit_total = sum(t.amount for t in credits)
    debit_total = sum(t.amount for t in debits)
    monthly_income = _rupee(credit_total / months)
    monthly_spend = _rupee(debit_total / months)
    monthly_surplus = _rupee(monthly_income - monthly_spend)

    category_totals: dict[str, float] = {}
    category_debit_ids: dict[str, list[str]] = {}
    for t in debits:
        cat = categorize(t.description)
        category_totals[cat] = category_totals.get(cat, 0.0) + t.amount
        category_debit_ids.setdefault(cat, []).append(t.id)
    categories_monthly = {
        cat: _rupee(total / months)
        for cat, total in sorted(category_totals.items(), key=lambda kv: -kv[1])
    }

    primary_income_category: str | None = None
    for candidate in PRIMARY_INCOME_CATEGORIES:
        if any(categorize(t.description) == candidate for t in credits):
            primary_income_category = candidate
            break

    primary_income_credit_ids: list[str] = []
    salary_regularity = 0.0
    if primary_income_category is not None:
        primary_credits = [t for t in credits if categorize(t.description) == primary_income_category]
        primary_income_credit_ids = [t.id for t in primary_credits]
        if primary_credits:
            counts_by_month: dict[str, int] = {}
            for t in primary_credits:
                key = t.date.isoformat()[:7]
                counts_by_month[key] = counts_by_month.get(key, 0) + 1
            coverage = min(1.0, len(counts_by_month) / months)
            amount_consistency = max(0.0, 1.0 - _coefficient_of_variation([t.amount for t in primary_credits]))
            count_consistency = max(0.0, 1.0 - _coefficient_of_variation([float(c) for c in counts_by_month.values()]))
            salary_regularity = round(coverage * amount_consistency * count_consistency, 2)

    emi_monthly = categories_monthly.get("emi", 0.0)
    emi_ratio = (emi_monthly / monthly_income) if monthly_income > 0 else 0.0
    surplus_ratio = (monthly_surplus / monthly_income) if monthly_income > 0 else 0.0

    overdraft_txn_ids = [t.id for t in txns if OVERDRAFT_KEYWORD in t.description.lower()]

    flags: list[str] = []
    if salary_regularity >= SALARY_CONSISTENT_REGULARITY_MIN:
        flags.append("salary_consistent")
    if salary_regularity < IRREGULAR_INCOME_REGULARITY_MAX:
        flags.append("irregular_income")
    if emi_ratio > EMI_STRESSED_RATIO_MIN:
        flags.append("emi_stressed")
    if monthly_surplus > CASH_SURPLUS_HEAVY_ABS_INR or surplus_ratio > CASH_SURPLUS_HEAVY_RATIO_MIN:
        flags.append("cash_surplus_heavy")
    if overdraft_txn_ids:
        flags.append("overdraft")

    return CashflowBundle(
        persona_id=persona.profile.id,
        months=months,
        last_txn_date=last_txn_date,
        all_txn_ids=[t.id for t in txns],
        credit_ids=[t.id for t in credits],
        debit_ids=[t.id for t in debits],
        monthly_income=monthly_income,
        monthly_spend=monthly_spend,
        monthly_surplus=monthly_surplus,
        categories_monthly=categories_monthly,
        category_debit_ids=category_debit_ids,
        primary_income_category=primary_income_category,
        primary_income_credit_ids=primary_income_credit_ids,
        salary_regularity=salary_regularity,
        emi_ratio=emi_ratio,  # full precision — risk.py's capacity formula consumes this raw
        behaviour_flags=flags,
        overdraft_txn_ids=overdraft_txn_ids,
        net_ledger_position=_rupee(credit_total - debit_total),
        record_by_id={t.id: {"amount": t.amount, "date": t.date.isoformat(), "type": t.type} for t in txns},
    )


def _records(bundle: CashflowBundle, ids: list[str]) -> list[dict]:
    """Look up the raw {amount, date, type} record for each id — used to make
    input_hash payloads reflect real data changes, not just which ids were used."""
    return [bundle.record_by_id[i] for i in ids]


def _no_data_ref(bundle: CashflowBundle, what: str) -> list[str]:
    return [f"persona:{bundle.persona_id}:no_{what}"]


def monthly_income_parts(bundle: CashflowBundle) -> MetricParts:
    return MetricParts(
        value=bundle.monthly_income,
        unit="inr",
        source_refs=bundle.credit_ids or _no_data_ref(bundle, "credits"),
        method="monthly_income_v1",
        inputs={"credits": _records(bundle, bundle.credit_ids), "months": bundle.months},
    )


def monthly_surplus_parts(bundle: CashflowBundle) -> MetricParts:
    return MetricParts(
        value=bundle.monthly_surplus,
        unit="inr",
        source_refs=bundle.all_txn_ids or _no_data_ref(bundle, "transactions"),
        method="monthly_surplus_v1",
        inputs={"txns": _records(bundle, bundle.all_txn_ids), "months": bundle.months},
    )


def idle_balance_parts(bundle: CashflowBundle) -> MetricParts:
    return MetricParts(
        value=bundle.net_ledger_position,
        unit="inr",
        source_refs=bundle.all_txn_ids or _no_data_ref(bundle, "transactions"),
        method="idle_balance_v1_ledger_proxy",
        inputs={"txns": _records(bundle, bundle.all_txn_ids)},
    )


def spend_by_category_parts(bundle: CashflowBundle) -> MetricParts:
    return MetricParts(
        value=dict(bundle.categories_monthly),
        unit="json",
        source_refs=bundle.debit_ids or _no_data_ref(bundle, "debits"),
        method="spend_by_category_v1",
        inputs={
            "category_debits": {cat: _records(bundle, ids) for cat, ids in bundle.category_debit_ids.items()},
            "months": bundle.months,
        },
    )


def savings_rate_parts(bundle: CashflowBundle) -> MetricParts:
    rate = (bundle.monthly_surplus / bundle.monthly_income) if bundle.monthly_income > 0 else 0.0
    return MetricParts(
        value=round(rate, 4),
        unit="ratio",
        source_refs=bundle.all_txn_ids or _no_data_ref(bundle, "transactions"),
        method="savings_rate_v1",
        inputs={"txns": _records(bundle, bundle.all_txn_ids), "months": bundle.months},
    )


def salary_regularity_parts(bundle: CashflowBundle) -> MetricParts:
    return MetricParts(
        value=bundle.salary_regularity,
        unit="ratio",
        source_refs=bundle.primary_income_credit_ids or _no_data_ref(bundle, "primary_income"),
        method="salary_regularity_v1",
        inputs={
            "primary_income_category": bundle.primary_income_category,
            "credits": _records(bundle, bundle.primary_income_credit_ids),
            "months": bundle.months,
        },
    )


def emi_ratio_parts(bundle: CashflowBundle) -> MetricParts:
    emi_ids = bundle.category_debit_ids.get("emi", [])
    refs = emi_ids + bundle.credit_ids
    return MetricParts(
        value=round(bundle.emi_ratio, 4),
        unit="ratio",
        source_refs=refs or _no_data_ref(bundle, "emi_or_income"),
        method="emi_ratio_v1",
        inputs={
            "emi_debits": _records(bundle, emi_ids),
            "credits": _records(bundle, bundle.credit_ids),
            "months": bundle.months,
        },
    )


def behaviour_flags_parts(bundle: CashflowBundle) -> MetricParts:
    return MetricParts(
        value={"flags": list(bundle.behaviour_flags)},
        unit="json",
        source_refs=bundle.all_txn_ids or _no_data_ref(bundle, "transactions"),
        method="behaviour_flags_v1",
        inputs={
            "salary_regularity": bundle.salary_regularity,
            "emi_ratio": bundle.emi_ratio,
            "monthly_surplus": bundle.monthly_surplus,
            "monthly_income": bundle.monthly_income,
            "overdraft_txn_ids": bundle.overdraft_txn_ids,
        },
    )
