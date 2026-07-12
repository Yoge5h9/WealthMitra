"""Net worth, asset mix, external inefficiency, and goal progress.

Consent invariant: `persona.external.holdings`/`liabilities` only enter
`net_worth`/`asset_mix`/`external_inefficiency` once `persona.external.connected`
is true. That flag is flipped by the AA-consent flow (Task 12), never by this
module — analytics only reads it.
"""

from __future__ import annotations

from app.domain.models import PersonaData

from .cashflow import CashflowBundle
from .constants import (
    IDBI_FD_BENCHMARK_RATE_PCT,
    IDBI_LOAN_REFINANCE_BENCHMARK_RATE_PCT,
    MetricParts,
)


def net_worth_parts(persona: PersonaData, bundle: CashflowBundle) -> MetricParts:
    internal = bundle.net_ledger_position
    external = persona.external
    connected = external.connected

    holding_ids = [h.id for h in external.holdings] if connected else []
    liability_ids = [l.id for l in external.liabilities] if connected else []
    external_holdings_total = sum(h.amount for h in external.holdings) if connected else 0.0
    external_liabilities_total = sum(l.principal for l in external.liabilities) if connected else 0.0
    external_net = external_holdings_total - external_liabilities_total
    total = internal + external_net

    refs = [*bundle.all_txn_ids, *holding_ids, *liability_ids]
    return MetricParts(
        value={
            "internal": internal,
            "external": external_net if connected else 0.0,
            "total": total,
            "external_connected": connected,
        },
        unit="json",
        source_refs=refs or [f"persona:{persona.profile.id}:no_data"],
        method="net_worth_v1",
        inputs={
            "internal": internal,
            "connected": connected,
            "external_holdings_total": external_holdings_total,
            "external_liabilities_total": external_liabilities_total,
        },
    )


def asset_mix_parts(persona: PersonaData, bundle: CashflowBundle) -> MetricParts:
    connected = persona.external.connected
    mix: dict[str, float] = {"bank_balance": bundle.net_ledger_position}
    holding_ids: list[str] = []
    if connected:
        for h in persona.external.holdings:
            mix[h.type] = mix.get(h.type, 0.0) + h.amount
            holding_ids.append(h.id)

    refs = [*bundle.all_txn_ids, *holding_ids]
    return MetricParts(
        value=mix,
        unit="json",
        source_refs=refs or [f"persona:{persona.profile.id}:no_data"],
        method="asset_mix_v1",
        inputs={"connected": connected, "mix": mix},
    )


def external_inefficiency_parts(persona: PersonaData) -> MetricParts:
    external = persona.external
    if not external.connected:
        return MetricParts(
            value={"available": False},
            unit="json",
            source_refs=[f"persona:{persona.profile.id}:external.connected"],
            method="external_inefficiency_v1:consent_gated",
            inputs={"connected": False},
        )

    underperforming_holdings = [
        {"holding_id": h.id, "type": h.type, "rate": h.rate, "benchmark": IDBI_FD_BENCHMARK_RATE_PCT}
        for h in external.holdings
        if h.type == "FD" and h.rate is not None and h.rate < IDBI_FD_BENCHMARK_RATE_PCT
    ]
    refinanceable_liabilities = [
        {"liability_id": l.id, "type": l.type, "rate": l.rate, "benchmark": IDBI_LOAN_REFINANCE_BENCHMARK_RATE_PCT}
        for l in external.liabilities
        if l.rate > IDBI_LOAN_REFINANCE_BENCHMARK_RATE_PCT
    ]
    fd_opportunity_inr = sum(
        h.amount * (IDBI_FD_BENCHMARK_RATE_PCT - h.rate) / 100.0
        for h in external.holdings
        if h.type == "FD" and h.rate is not None and h.rate < IDBI_FD_BENCHMARK_RATE_PCT
    )
    loan_saving_inr = sum(
        l.principal * (l.rate - IDBI_LOAN_REFINANCE_BENCHMARK_RATE_PCT) / 100.0
        for l in external.liabilities
        if l.rate > IDBI_LOAN_REFINANCE_BENCHMARK_RATE_PCT
    )

    all_ids = [h.id for h in external.holdings] + [l.id for l in external.liabilities]
    return MetricParts(
        value={
            "available": True,
            "underperforming_holdings": underperforming_holdings,
            "refinanceable_liabilities": refinanceable_liabilities,
            "estimated_annual_impact_inr": round(fd_opportunity_inr + loan_saving_inr),
        },
        unit="json",
        source_refs=all_ids or [f"persona:{persona.profile.id}:no_external_data"],
        method="external_inefficiency_v1",
        inputs={
            "holdings": [{"id": h.id, "type": h.type, "rate": h.rate, "amount": h.amount} for h in external.holdings],
            "liabilities": [{"id": l.id, "rate": l.rate, "principal": l.principal} for l in external.liabilities],
        },
    )


def goal_progress_parts(persona: PersonaData) -> MetricParts:
    goals = persona.goals
    if not goals:
        return MetricParts(
            value={"goals": []},
            unit="json",
            source_refs=[f"persona:{persona.profile.id}:no_goals"],
            method="goal_progress_v1",
            inputs={"goals": []},
        )

    entries = []
    refs = []
    for idx, g in enumerate(goals):
        refs.append(f"goal:{persona.profile.id}:{idx}")
        progress_ratio = (g.saved_so_far / g.target) if g.target > 0 else 0.0
        remaining = max(g.target - g.saved_so_far, 0.0)
        months_left = max(g.horizon_years, 0) * 12
        monthly_required_inr = (remaining / months_left) if months_left > 0 else remaining
        entries.append(
            {
                "name": g.name,
                "target": g.target,
                "saved_so_far": g.saved_so_far,
                "horizon_years": g.horizon_years,
                "progress_ratio": round(progress_ratio, 4),
                "monthly_required_inr": round(monthly_required_inr),
            }
        )

    return MetricParts(
        value={"goals": entries},
        unit="json",
        source_refs=refs,
        method="goal_progress_v1",
        inputs={
            "goals": [
                {"name": g.name, "target": g.target, "saved_so_far": g.saved_so_far, "horizon_years": g.horizon_years}
                for g in goals
            ]
        },
    )
