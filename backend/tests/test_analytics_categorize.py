"""Categorizer: ordered-keyword rules, first-match-wins, ported byte-identical
from the old MVP. Accuracy is checked against the generator's own labels on
every real synthetic persona's transaction description.
"""

from pathlib import Path

import pytest

from app.analytics.categorize import categorize
from app.core.spaces import SpaceStore

REAL_SYNTHETIC_DIR = Path(__file__).resolve().parents[2] / "data" / "synthetic"
CATEGORIZER_ACCURACY_FLOOR = 0.9


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("Monthly salary credit", "salary"),
        ("EPFO Pension credit", "pension"),
        ("Client payment received - Invoice #221", "business_income"),
        ("NEFT Inward remittance", "transfer_in"),
        ("EMI auto-debit - home loan", "emi"),
        ("House rent payment", "rent"),
        ("SIP - Nifty Index Fund", "investment"),
        ("Electricity bill payment", "utilities"),
        ("Swiggy order", "food"),
        ("Amazon purchase", "shopping"),
        ("Uber ride", "travel"),
        ("Netflix subscription", "entertainment"),
        ("Apollo Pharmacy bill", "healthcare"),
        ("Coursera course fee", "education"),
        ("ATM cash withdrawal", "cash_withdrawal"),
        ("Random unclassified merchant XYZ", "other"),
    ],
)
def test_categorize_matches_expected_category(description: str, expected: str) -> None:
    assert categorize(description) == expected


def test_categorize_is_case_insensitive() -> None:
    assert categorize("SWIGGY ORDER") == "food"
    assert categorize("swiggy order") == "food"


def test_categorize_first_match_wins_ordering() -> None:
    # "emi" keyword rule is checked before "rent" — a description matching both
    # ("emi" appears nowhere near "rent" in real data, but the ordering itself
    # must hold since first-match-wins is the contract, not per-category accuracy).
    assert categorize("EMI installment for rent-free flat") == "emi"


@pytest.mark.skipif(not REAL_SYNTHETIC_DIR.is_dir(), reason="data/synthetic/ not present")
def test_categorizer_accuracy_against_generator_labels() -> None:
    store = SpaceStore()
    space = store.get(store.create_space())

    total = 0
    correct = 0
    for persona in space.personas.values():
        for txn in persona.transactions:
            total += 1
            if categorize(txn.description) == txn.category:
                correct += 1

    assert total > 0
    accuracy = correct / total
    assert accuracy >= CATEGORIZER_ACCURACY_FLOOR, f"categorizer accuracy {accuracy:.3f} below floor"
