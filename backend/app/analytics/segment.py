"""Suitability segment (canonical id set includes `mass_retail_gig`) — a
demographic bucket derived deterministically from age, external
holdings, occupation text, and transaction-derived behaviour flags.

`city_tier` and `employment` aren't available on the `PersonaProfile`
model (see `cashflow.py` module docstring for why), so this derivation only
uses fields the model actually exposes: `age`, `occupation` (free text),
external holding/liability records, and the behaviour flags computed in
`cashflow.py`. The one exception is the `irregular_income` branch: gig/irregular
earners don't have a clean *derivable* id distinct from "mass_retail" without
`employment`, so that branch falls back to the persona's own seeded
`profile.segment` as one input signal — exactly as flagged in the task brief.
That fallback is why `priya` (gig worker) reproduces `mass_retail_gig` rather
than a generic "irregular" bucket the schema doesn't otherwise support.
"""

from __future__ import annotations

from app.domain.models import PersonaData

from .cashflow import CashflowBundle
from .constants import (
    AFFLUENT_OCCUPATION_KEYWORD,
    DEFAULT_SEGMENT,
    HNI_EXTERNAL_HOLDINGS_THRESHOLD_INR,
    MetricParts,
    NRI_INSTITUTION_KEYWORDS,
    SENIOR_AGE_THRESHOLD,
)


def suitability_segment_parts(persona: PersonaData, bundle: CashflowBundle) -> MetricParts:
    profile = persona.profile
    external = persona.external

    if profile.age >= SENIOR_AGE_THRESHOLD:
        return MetricParts(
            value="senior",
            unit="label",
            source_refs=[f"profile:{profile.id}:age"],
            method="suitability_segment_v1:senior",
            inputs={"age": profile.age},
        )

    nri_holding_ids = [
        h.id
        for h in external.holdings
        if any(kw in h.institution.lower() or kw in h.type.lower() for kw in NRI_INSTITUTION_KEYWORDS)
    ]
    if nri_holding_ids:
        return MetricParts(
            value="nri",
            unit="label",
            source_refs=nri_holding_ids,
            method="suitability_segment_v1:nri",
            inputs={"nri_holding_ids": nri_holding_ids},
        )

    external_holdings_total = sum(h.amount for h in external.holdings)
    if external_holdings_total >= HNI_EXTERNAL_HOLDINGS_THRESHOLD_INR:
        return MetricParts(
            value="hni",
            unit="label",
            source_refs=[h.id for h in external.holdings],
            method="suitability_segment_v1:hni",
            inputs={"external_holdings_total": external_holdings_total},
        )

    is_business_occupation = AFFLUENT_OCCUPATION_KEYWORD in profile.occupation.lower()
    if is_business_occupation and "cash_surplus_heavy" in bundle.behaviour_flags:
        return MetricParts(
            value="affluent",
            unit="label",
            source_refs=[f"profile:{profile.id}:occupation", *bundle.all_txn_ids],
            method="suitability_segment_v1:affluent",
            inputs={"occupation": profile.occupation, "behaviour_flags": bundle.behaviour_flags},
        )

    if "irregular_income" in bundle.behaviour_flags:
        return MetricParts(
            value=profile.segment,
            unit="label",
            source_refs=[*bundle.all_txn_ids, f"profile:{profile.id}:segment"],
            method="suitability_segment_v1:irregular_income_profile_fallback",
            inputs={"behaviour_flags": bundle.behaviour_flags, "profile_segment": profile.segment},
        )

    return MetricParts(
        value=DEFAULT_SEGMENT,
        unit="label",
        source_refs=[f"profile:{profile.id}:occupation", f"profile:{profile.id}:age"],
        method="suitability_segment_v1:default",
        inputs={"age": profile.age, "occupation": profile.occupation},
    )
