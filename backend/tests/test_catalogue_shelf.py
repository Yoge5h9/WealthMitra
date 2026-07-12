import pytest

from app.catalogue.shelf import compare, eligible_shelf, narrow
from app.catalogue.suitability import CATALOGUE


def test_eligible_shelf_matches_matrix_cell() -> None:
    shelf = eligible_shelf("mass_retail_salaried", "conservative")
    shelf_ids = {product.id for product in shelf}

    assert shelf_ids == {"fd_ladder", "recurring_deposit"}


def test_eligible_shelf_filters_by_category() -> None:
    shelf = eligible_shelf("mass_retail_gig", "conservative", category="deposit")

    assert shelf
    assert all(product.category == "deposit" for product in shelf)
    assert {p.id for p in shelf} == {"recurring_deposit", "flexi_micro_rd"}


def test_eligible_shelf_unknown_segment_raises() -> None:
    with pytest.raises(ValueError, match="segment"):
        eligible_shelf("not_a_segment", "conservative")


def test_eligible_shelf_unknown_risk_band_raises() -> None:
    with pytest.raises(ValueError, match="risk band"):
        eligible_shelf("mass_retail_salaried", "not_a_band")


def test_eligible_shelf_suppressed_cell_returns_empty() -> None:
    assert eligible_shelf("senior", "growth") == []


def test_affordability_rule_excludes_high_minimum_for_non_affluent() -> None:
    # cat2_aif_credit has min_amount == 5,000,000 (₹50L); ₹20k/month * 12 == ₹2.4L, far below it.
    shelf = eligible_shelf(
        "hni",
        "growth",
        monthly_surplus=20_000,
        is_affluent_or_hni=False,
    )

    assert "cat2_aif_credit" not in {p.id for p in shelf}


def test_affordability_rule_skipped_for_affluent_or_hni() -> None:
    shelf = eligible_shelf(
        "hni",
        "growth",
        monthly_surplus=20_000,
        is_affluent_or_hni=True,
    )

    assert "cat2_aif_credit" in {p.id for p in shelf}


def test_affordability_rule_skipped_when_surplus_not_given() -> None:
    shelf = eligible_shelf("hni", "growth")

    assert "cat2_aif_credit" in {p.id for p in shelf}


def test_narrow_is_deterministic_across_repeated_calls() -> None:
    shelf = eligible_shelf("mass_retail_salaried", "moderate")

    first = [p.id for p in narrow("grow my savings", shelf)]
    second = [p.id for p in narrow("grow my savings", shelf)]

    assert first == second


def test_narrow_surfaces_relevant_product_by_keyword() -> None:
    shelf = eligible_shelf("mass_retail_salaried", "moderate")  # [index_fund_sip, elss_fund]

    ranked = narrow("tax", shelf)

    assert ranked[0].id == "elss_fund"


def test_narrow_never_adds_products_outside_the_shelf() -> None:
    shelf = eligible_shelf("mass_retail_salaried", "conservative")

    ranked = narrow("tax", shelf)

    assert {p.id for p in ranked} == {p.id for p in shelf}


def test_compare_returns_only_looked_up_values() -> None:
    products = [CATALOGUE.products["fd_ladder"], CATALOGUE.products["elss_fund"]]

    matrix = compare(products)

    assert matrix.product_ids == ["fd_ladder", "elss_fund"]
    rows_by_feature = {row["feature"]: row["values"] for row in matrix.rows}

    assert rows_by_feature["min_amount"]["fd_ladder"] == f"₹{products[0].min_amount:,}"
    assert rows_by_feature["expected_return"]["elss_fund"] == products[1].expected_return
    assert rows_by_feature["category"]["fd_ladder"] == products[0].category
    assert rows_by_feature["tag"]["fd_ladder"] == "Auto-executable"
    assert rows_by_feature["tag"]["elss_fund"] == "Via your Relationship Manager"


def test_compare_empty_product_list_returns_empty_matrix() -> None:
    matrix = compare([])

    assert matrix.product_ids == []
    assert all(row["values"] == {} for row in matrix.rows)


def test_vanilla_regulated_tags_match_compliance_list() -> None:
    vanilla_ids = {
        "fd_ladder",
        "recurring_deposit",
        "index_fund_sip",
        "liquid_fund_sweep",
        "short_duration_debt",
        "corporate_fd",
        "rbi_floating_bonds",
        "debt_index_core",
        "gsec_ladder",
        "nre_deposit",
        "fcnr_deposit",
        "scss",
        "senior_citizen_fd",
        "treasury_bill_ladder",
        "flexi_micro_rd",
    }
    regulated_ids = {
        "elss_fund",
        "flexicap_mf",
        "balanced_advantage",
        "equity_satellite",
        "pms_lite",
        "rm_allocation",
        "structured_note",
        "aif",
        "repatriable_index",
        "nri_equity",
        "monthly_income_plan",
        "multi_asset_pms",
        "cat2_aif_credit",
    }

    assert vanilla_ids | regulated_ids == set(CATALOGUE.products)

    for product_id in vanilla_ids:
        assert CATALOGUE.products[product_id].tag == "vanilla"
    for product_id in regulated_ids:
        assert CATALOGUE.products[product_id].tag == "regulated"


def test_product_count() -> None:
    assert len(CATALOGUE.products) == 28
