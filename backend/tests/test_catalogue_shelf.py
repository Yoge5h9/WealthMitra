import pytest

from app.catalogue.shelf import compare, eligible_shelf, narrow
from app.catalogue.suitability import CATALOGUE


def test_eligible_shelf_matches_matrix_cell() -> None:
    shelf = eligible_shelf("mass_retail_salaried", "conservative")
    shelf_ids = {product.id for product in shelf}

    assert shelf_ids == {
        "fd_regular", "fd_suvidha_tax_saver", "recurring_deposit", "ppf", "ssy",
        "rbi_floating_bond", "insurance_term",
    }


def test_eligible_shelf_filters_by_category() -> None:
    shelf = eligible_shelf("mass_retail_gig", "conservative", category="deposit")

    assert shelf
    assert all(product.category == "deposit" for product in shelf)
    assert {p.id for p in shelf} == {"fd_regular", "recurring_deposit"}


def test_eligible_shelf_unknown_segment_raises() -> None:
    with pytest.raises(ValueError, match="segment"):
        eligible_shelf("not_a_segment", "conservative")


def test_eligible_shelf_unknown_risk_band_raises() -> None:
    with pytest.raises(ValueError, match="risk band"):
        eligible_shelf("mass_retail_salaried", "not_a_band")


def test_eligible_shelf_suppressed_cell_returns_empty() -> None:
    assert eligible_shelf("senior", "growth") == []


def test_affordability_rule_excludes_high_minimum_for_non_affluent() -> None:
    # pms/aif carry SEBI-mandated Rs 50L/Rs 1cr minimums; Rs 20k/month * 12 == Rs 2.4L,
    # far below either.
    shelf = eligible_shelf(
        "hni",
        "growth",
        monthly_surplus=20_000,
        is_affluent_or_hni=False,
    )

    shelf_ids = {p.id for p in shelf}
    assert "pms" not in shelf_ids
    assert "aif" not in shelf_ids


def test_affordability_rule_skipped_for_affluent_or_hni() -> None:
    shelf = eligible_shelf(
        "hni",
        "growth",
        monthly_surplus=20_000,
        is_affluent_or_hni=True,
    )

    assert "aif" in {p.id for p in shelf}


def test_affordability_rule_skipped_when_surplus_not_given() -> None:
    shelf = eligible_shelf("hni", "growth")

    assert "aif" in {p.id for p in shelf}


def test_narrow_is_deterministic_across_repeated_calls() -> None:
    shelf = eligible_shelf("mass_retail_salaried", "moderate")

    first = [p.id for p in narrow("grow my savings", shelf)]
    second = [p.id for p in narrow("grow my savings", shelf)]

    assert first == second


def test_narrow_surfaces_relevant_product_by_keyword() -> None:
    shelf = eligible_shelf("mass_retail_salaried", "moderate")  # [mf_index_sip, mf_elss_direct, nps]

    ranked = narrow("tax", shelf)

    assert ranked[0].id == "mf_elss_direct"


def test_narrow_never_adds_products_outside_the_shelf() -> None:
    shelf = eligible_shelf("mass_retail_salaried", "conservative")

    ranked = narrow("tax", shelf)

    assert {p.id for p in ranked} == {p.id for p in shelf}


def test_compare_returns_only_looked_up_values() -> None:
    products = [CATALOGUE.products["fd_regular"], CATALOGUE.products["mf_elss_direct"]]

    matrix = compare(products)

    assert matrix.product_ids == ["fd_regular", "mf_elss_direct"]
    rows_by_feature = {row["feature"]: row["values"] for row in matrix.rows}

    assert rows_by_feature["min_amount"]["fd_regular"] == f"₹{products[0].min_amount:,}"
    assert rows_by_feature["expected_return"]["mf_elss_direct"] == products[1].expected_return
    assert rows_by_feature["category"]["fd_regular"] == products[0].category
    assert rows_by_feature["tag"]["fd_regular"] == "Auto-executable"
    assert rows_by_feature["tag"]["mf_elss_direct"] == "Auto-executable"


def test_compare_empty_product_list_returns_empty_matrix() -> None:
    matrix = compare([])

    assert matrix.product_ids == []
    assert all(row["values"] == {} for row in matrix.rows)


def test_vanilla_regulated_tags_match_compliance_list() -> None:
    vanilla_ids = {
        "fd_regular",
        "fd_senior_citizen",
        "fd_chiranjeevi",
        "fd_suvidha_tax_saver",
        "fd_utsav",
        "recurring_deposit",
        "ppf",
        "ssy",
        "scss",
        "nps",
        "rbi_floating_bond",
        "rbi_retail_direct_gsec",
        "mf_index_sip",
        "mf_elss_direct",
        "mf_liquid",
        "demat_trading",
        "nre_deposit",
        "nro_deposit",
        "fcnr_deposit",
    }
    regulated_ids = {
        "mf_active_equity",
        "insurance_term",
        "insurance_ulip",
        "insurance_health",
        "insurance_general",
        "pms",
        "aif",
        "wealth_advisory",
    }

    assert vanilla_ids | regulated_ids == set(CATALOGUE.products)

    for product_id in vanilla_ids:
        assert CATALOGUE.products[product_id].tag == "vanilla"
    for product_id in regulated_ids:
        assert CATALOGUE.products[product_id].tag == "regulated"


def test_product_count() -> None:
    assert len(CATALOGUE.products) == 27


def test_no_fabricated_mutual_fund_scheme_or_amc_names() -> None:
    """The MF shelf is presented as a category (index/ELSS/liquid/active), never
    a specific fund-house or scheme name we don't have verified real-world backing
    for — see the sourced research this catalogue was built from.
    """
    banned_fragments = ("hdfc", "icici prudential", "sbi mutual", "axis mutual", "kotak mutual", "nippon", "franklin")
    for product in CATALOGUE.products.values():
        if product.category != "mutual_fund":
            continue
        blob = f"{product.name} {product.description}".lower()
        for fragment in banned_fragments:
            assert fragment not in blob, f"{product.id} appears to fabricate an AMC name: {fragment!r}"
