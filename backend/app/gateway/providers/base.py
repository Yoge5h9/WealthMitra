"""Helpers shared across provider adapters."""

Pricing = dict[str, dict[str, float]]


def cost_usd(pricing: Pricing, model: str, input_tokens: int, output_tokens: int) -> float:
    """USD cost estimate for a call, from the per-model per-Mtoken table.

    Unknown models cost 0.0 rather than raising — a missing price row must
    never break a live response; it surfaces as a zero estimate in the audit.
    """
    row = pricing.get(model)
    if not row:
        return 0.0
    return round(
        input_tokens / 1_000_000 * row.get("input_per_mtok", 0.0)
        + output_tokens / 1_000_000 * row.get("output_per_mtok", 0.0),
        6,
    )
