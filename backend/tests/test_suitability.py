import json
from pathlib import Path

import pytest

from app.catalogue.suitability import CATALOGUE, RISK_BANDS, is_suppressed, load_catalogue, reasons


def test_all_eighteen_cells_resolve_or_are_suppressed() -> None:
    segments = CATALOGUE.segments()
    assert len(segments) == 6

    cells = [(segment, band) for segment in segments for band in RISK_BANDS]
    assert len(cells) == 18

    for segment, band in cells:
        product_ids = CATALOGUE.matrix[segment][band]
        if not product_ids:
            assert is_suppressed(segment, band), f"({segment}, {band}) is empty but not suppressed"
        else:
            for product_id in product_ids:
                assert product_id in CATALOGUE.products


def test_senior_growth_is_the_only_suppressed_cell() -> None:
    suppressed_cells = [
        (segment, band)
        for segment in CATALOGUE.segments()
        for band in RISK_BANDS
        if is_suppressed(segment, band)
    ]
    assert suppressed_cells == [("senior", "growth")]
    assert CATALOGUE.matrix["senior"]["growth"] == []


def test_every_matrix_product_id_exists_in_catalog() -> None:
    for segment, bands in CATALOGUE.matrix.items():
        for band, product_ids in bands.items():
            for product_id in product_ids:
                assert product_id in CATALOGUE.products, (
                    f"matrix references unknown product '{product_id}' at ({segment}, {band})"
                )


def test_hni_cells_are_non_empty() -> None:
    for band in RISK_BANDS:
        assert CATALOGUE.matrix["hni"][band], f"hni/{band} shelf is empty"


def test_reasons_are_human_readable_and_mention_the_product() -> None:
    product = CATALOGUE.products["fd_ladder"]
    out = reasons("mass_retail_salaried", "conservative", product)

    assert isinstance(out, list) and out
    assert all(isinstance(reason, str) and reason for reason in out)
    assert any(product.name in reason for reason in out)


def test_load_catalogue_rejects_matrix_id_not_in_products(tmp_path: Path) -> None:
    (tmp_path / "products.json").write_text(
        json.dumps(
            [
                {
                    "id": "fd_ladder",
                    "name": "IDBI FD Ladder",
                    "tag": "vanilla",
                    "category": "deposit",
                    "min_amount": 10000,
                    "expected_return": "6.8-7.4% p.a.",
                    "description": "Laddered fixed deposits.",
                }
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "suitability_matrix.json").write_text(
        json.dumps(
            {
                "mass_retail_salaried": {
                    "conservative": ["fd_ladder"],
                    "moderate": ["does_not_exist"],
                    "growth": [],
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does_not_exist"):
        load_catalogue(tmp_path)


def test_load_catalogue_rejects_unsuppressed_empty_cell(tmp_path: Path) -> None:
    (tmp_path / "products.json").write_text(
        json.dumps(
            [
                {
                    "id": "fd_ladder",
                    "name": "IDBI FD Ladder",
                    "tag": "vanilla",
                    "category": "deposit",
                    "min_amount": 10000,
                    "expected_return": "6.8-7.4% p.a.",
                    "description": "Laddered fixed deposits.",
                }
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "suitability_matrix.json").write_text(
        json.dumps(
            {
                "mass_retail_salaried": {
                    "conservative": ["fd_ladder"],
                    "moderate": [],
                    "growth": [],
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="empty"):
        load_catalogue(tmp_path)


def test_load_catalogue_rejects_unknown_risk_band(tmp_path: Path) -> None:
    (tmp_path / "products.json").write_text(
        json.dumps(
            [
                {
                    "id": "fd_ladder",
                    "name": "IDBI FD Ladder",
                    "tag": "vanilla",
                    "category": "deposit",
                    "min_amount": 10000,
                    "expected_return": "6.8-7.4% p.a.",
                    "description": "Laddered fixed deposits.",
                }
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "suitability_matrix.json").write_text(
        json.dumps(
            {
                "mass_retail_salaried": {
                    "conservative": ["fd_ladder"],
                    "moderate": [],
                    "growth": [],
                    "aggressive": ["fd_ladder"],
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown risk band"):
        load_catalogue(tmp_path)


def test_load_catalogue_rejects_missing_risk_band(tmp_path: Path) -> None:
    (tmp_path / "products.json").write_text(
        json.dumps(
            [
                {
                    "id": "fd_ladder",
                    "name": "IDBI FD Ladder",
                    "tag": "vanilla",
                    "category": "deposit",
                    "min_amount": 10000,
                    "expected_return": "6.8-7.4% p.a.",
                    "description": "Laddered fixed deposits.",
                }
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "suitability_matrix.json").write_text(
        json.dumps({"mass_retail_salaried": {"conservative": ["fd_ladder"]}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing risk band"):
        load_catalogue(tmp_path)
