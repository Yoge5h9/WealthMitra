"""Suitability Matrix: loads the product catalog + segment×risk_band grid, validates it at
load time, and answers "is this cell suppressed" / "why this shelf" questions.

Pure config lookup — this module never decides whether to recommend anything;
`shelf.py` builds the actual eligible shelf on top of the `Catalogue` it loads here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.domain.models import Product

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

RISK_BANDS: tuple[str, ...] = ("conservative", "moderate", "growth")

# Cells intentionally empty by product policy (not a config gap). Any other
# empty cell in suitability_matrix.json is treated as a bug and rejected at load.
SUPPRESSED: set[tuple[str, str]] = {("senior", "growth")}


@dataclass(frozen=True)
class Catalogue:
    products: dict[str, Product]
    matrix: dict[str, dict[str, list[str]]]

    def segments(self) -> list[str]:
        return list(self.matrix.keys())


def load_catalogue(config_dir: Path = _CONFIG_DIR) -> Catalogue:
    """Load and validate `products.json` + `suitability_matrix.json` from `config_dir`.

    Raises `ValueError` on any structural problem: an unknown risk band, a
    matrix cell missing a required band, a product id in the matrix that
    doesn't exist in the catalog, or a non-suppressed cell that's empty.
    """
    products_raw = json.loads((config_dir / "products.json").read_text(encoding="utf-8"))
    products = {p["id"]: Product(**p) for p in products_raw}

    matrix: dict[str, dict[str, list[str]]] = json.loads(
        (config_dir / "suitability_matrix.json").read_text(encoding="utf-8")
    )

    for segment, bands in matrix.items():
        unknown_bands = sorted(set(bands) - set(RISK_BANDS))
        if unknown_bands:
            raise ValueError(
                f"suitability_matrix.json: segment '{segment}' has unknown risk band(s) {unknown_bands}"
            )
        missing_bands = sorted(set(RISK_BANDS) - set(bands))
        if missing_bands:
            raise ValueError(
                f"suitability_matrix.json: segment '{segment}' is missing risk band(s) {missing_bands}"
            )

        for band, product_ids in bands.items():
            unknown_products = [pid for pid in product_ids if pid not in products]
            if unknown_products:
                raise ValueError(
                    f"suitability_matrix.json: segment '{segment}' band '{band}' "
                    f"references unknown product id(s) {unknown_products}"
                )
            if not product_ids and (segment, band) not in SUPPRESSED:
                raise ValueError(
                    f"suitability_matrix.json: segment '{segment}' band '{band}' is empty "
                    "but not declared in SUPPRESSED"
                )

    return Catalogue(products=products, matrix=matrix)


CATALOGUE = load_catalogue()


def is_suppressed(segment: str, band: str) -> bool:
    return (segment, band) in SUPPRESSED


def reasons(segment: str, band: str, product: Product) -> list[str]:
    """Human-readable, audit-friendly explanation for why `product` is on this shelf."""
    return [
        f"'{segment}' investors in the '{band}' risk band are matched to this shelf by the suitability matrix.",
        "Risk band is derived conservatively as min(capacity, tolerance).",
        f"'{product.name}' requires a minimum of ₹{product.min_amount:,} and is tagged '{product.tag}'.",
    ]
