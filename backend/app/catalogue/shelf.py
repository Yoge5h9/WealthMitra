"""Deterministic shelf building on top of the loaded `Catalogue` — eligible-shelf lookup,
in-shelf ranking, and side-by-side comparison. No RAG, no LLM, no recommendation decision:
this module only narrows a matrix cell down, it never widens one and never decides whether
to act on it (that's the orchestrator's + routing engine's job).
"""

from __future__ import annotations

from app.domain.models import FeatureMatrix, Product

from .suitability import CATALOGUE, RISK_BANDS, Catalogue

_TAG_DISPLAY = {
    "vanilla": "Auto-executable",
    "regulated": "Via your Relationship Manager",
}


def eligible_shelf(
    segment: str,
    risk_band: str,
    category: str | None = None,
    *,
    monthly_surplus: float | None = None,
    is_affluent_or_hni: bool = False,
    catalogue: Catalogue = CATALOGUE,
) -> list[Product]:
    """Resolve the suitability-matrix cell for (segment, risk_band), then narrow it by
    an optional category and, unless the persona is affluent/HNI, an affordability rule
    (excludes any product whose min_amount exceeds a year of surplus).

    Raises `ValueError` for a segment or risk band the loaded matrix doesn't know about.
    """
    if segment not in catalogue.matrix:
        raise ValueError(f"unknown segment '{segment}'")
    if risk_band not in RISK_BANDS:
        raise ValueError(f"unknown risk band '{risk_band}'")

    product_ids = catalogue.matrix[segment][risk_band]
    shelf = [catalogue.products[pid] for pid in product_ids]

    if category is not None:
        shelf = [product for product in shelf if product.category == category]

    if monthly_surplus is not None and not is_affluent_or_hni:
        annual_capacity = monthly_surplus * 12
        shelf = [product for product in shelf if product.min_amount <= annual_capacity]

    return shelf


def narrow(need: str, shelf: list[Product]) -> list[Product]:
    """Deterministically rank `shelf` for a stated `need`: keyword relevance to the need
    (matched against name/category/description) first, then lower min_amount, then id —
    for stable, reproducible ordering. Never reorders in a way that adds a product that
    wasn't already in `shelf`.
    """
    need_lower = need.strip().lower()

    def relevance_rank(product: Product) -> int:
        haystack = f"{product.name} {product.category} {product.description}".lower()
        return 0 if need_lower and need_lower in haystack else 1

    return sorted(shelf, key=lambda product: (relevance_rank(product), product.min_amount, product.id))


def compare(products: list[Product]) -> FeatureMatrix:
    """Side-by-side comparison of `products` — every value is looked up from the Product
    record, never computed or estimated.
    """
    product_ids = [product.id for product in products]
    rows = [
        {"feature": "min_amount", "values": {p.id: f"₹{p.min_amount:,}" for p in products}},
        {"feature": "expected_return", "values": {p.id: p.expected_return for p in products}},
        {"feature": "category", "values": {p.id: p.category for p in products}},
        {"feature": "tag", "values": {p.id: _TAG_DISPLAY[p.tag] for p in products}},
    ]
    return FeatureMatrix(product_ids=product_ids, rows=rows)
