"""`AnalyticsEngine` — the single deterministic entry point for every audited
`Metric` in the WealthMitra financial-analysis spine.

"Compute the numbers here; the LLM only ever explains/phrases them" — nothing
in this module ever calls an LLM, and every `Metric` it returns carries real
provenance (`source_refs`, `method`, `input_hash`) so a downstream guardrail
or auditor can trace any figure back to the transactions/holdings that
produced it.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.spaces import Space
from app.domain.models import Metric

from . import networth, risk, segment
from .cashflow import (
    behaviour_flags_parts,
    build_cashflow,
    emi_ratio_parts,
    idle_balance_parts,
    monthly_income_parts,
    monthly_surplus_parts,
    salary_regularity_parts,
    savings_rate_parts,
    spend_by_category_parts,
)
from .constants import stable_hash

METRIC_IDS: tuple[str, ...] = (
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
)


class AnalyticsEngine:
    """Deterministic financial-analysis engine: transactions/holdings in, audited `Metric`s out."""

    def compute(
        self,
        space: Space,
        persona_id: str,
        metric_ids: list[str] | None = None,
        now: datetime | None = None,
    ) -> list[Metric]:
        try:
            persona = space.personas[persona_id]
        except KeyError:
            raise KeyError(f"unknown persona: {persona_id}") from None

        requested = list(metric_ids) if metric_ids is not None else list(METRIC_IDS)
        unknown = [mid for mid in requested if mid not in METRIC_IDS]
        if unknown:
            raise ValueError(f"unknown metric id(s): {unknown}")

        bundle = build_cashflow(persona)
        capacity = risk.capacity_score_parts(persona.profile, bundle)
        tolerance = risk.tolerance_score_parts(persona.profile)

        parts_by_id = {
            "monthly_income": monthly_income_parts(bundle),
            "monthly_surplus": monthly_surplus_parts(bundle),
            "idle_balance": idle_balance_parts(bundle),
            "spend_by_category": spend_by_category_parts(bundle),
            "savings_rate": savings_rate_parts(bundle),
            "salary_regularity": salary_regularity_parts(bundle),
            "behaviour_flags": behaviour_flags_parts(bundle),
            "emi_ratio": emi_ratio_parts(bundle),
            "capacity_score": capacity,
            "tolerance_score": tolerance,
            "risk_band": risk.risk_band_parts(capacity, tolerance),
            "suitability_segment": segment.suitability_segment_parts(persona, bundle),
            "net_worth": networth.net_worth_parts(persona, bundle),
            "asset_mix": networth.asset_mix_parts(persona, bundle),
            "external_inefficiency": networth.external_inefficiency_parts(persona),
            "goal_progress": networth.goal_progress_parts(persona),
        }

        as_of = bundle.last_txn_date
        computed_at = now if now is not None else datetime.now(timezone.utc)
        return [
            Metric(
                id=metric_id,
                value=parts_by_id[metric_id].value,
                unit=parts_by_id[metric_id].unit,
                as_of=as_of,
                source_refs=parts_by_id[metric_id].source_refs,
                method=parts_by_id[metric_id].method,
                input_hash=stable_hash(parts_by_id[metric_id].inputs),
                computed_at=computed_at,
            )
            for metric_id in requested
        ]
