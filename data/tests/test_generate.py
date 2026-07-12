"""Self-contained tests for data/generate.py.

No backend imports: the backend is being rebuilt concurrently by another agent.
The categorizer keyword table below is mirrored (read-only, for verification)
from the frozen `backend/app/analytics.py` at commit 54e7080 — a later task
ports the exact table into the rebuilt backend.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
SYNTH = ROOT / "synthetic"
GENERATE = ROOT / "generate.py"
PERSONAS = ["ravi", "shanta", "meera", "arjun", "vikram", "devika", "priya"]

# Mirrored verification-only copy of the analytics categorizer keyword rules.
_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("salary", ("salary",)),
    ("pension", ("pension",)),
    ("business_income", ("client payment", "business receipt", "invoice", "consulting fee", "professional fees")),
    ("transfer_in", ("inward remittance", "nre credit", "fund transfer in", "neft inward", "imps credit", "amount received")),
    ("emi", ("emi", "loan installment", "loan instalment")),
    ("rent", ("rent",)),
    ("investment", ("sip", "mutual fund", "fd booking", "recurring deposit", "rd installment", "nps contribution", "elss")),
    ("utilities", ("electricity", "broadband", "mobile recharge", "gas bill", "water bill", "dth", "postpaid")),
    ("food", ("swiggy", "zomato", "bigbasket", "restaurant", "grocery", "grocer", "cafe", "eatery")),
    ("shopping", ("amazon", "flipkart", "myntra", "reliance retail", "lifestyle store", "mall")),
    ("travel", ("uber", "ola", "irctc", "indigo", "makemytrip", "petrol", "fuel", "redbus", "airlines")),
    ("entertainment", ("netflix", "hotstar", "spotify", "bookmyshow", "prime video", "movie")),
    ("healthcare", ("pharmacy", "apollo", "hospital", "medical", "diagnostic", "medplus")),
    ("education", ("school fee", "tuition", "coursera", "udemy", "college")),
    ("cash_withdrawal", ("atm", "cash withdrawal")),
]


def categorize(description: str) -> str:
    text = description.lower()
    for category, keywords in _RULES:
        if any(k in text for k in keywords):
            return category
    return "other"


def load(persona: str) -> dict[str, Any]:
    return json.loads((SYNTH / f"{persona}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session", autouse=True)
def regenerate_once() -> None:
    subprocess.run([sys.executable, str(GENERATE)], check=True, cwd=ROOT)


# --- determinism ---------------------------------------------------------

def test_regeneration_is_byte_identical(tmp_path: Path) -> None:
    before = {p.name: p.read_bytes() for p in SYNTH.glob("*.json")}
    subprocess.run([sys.executable, str(GENERATE)], check=True, cwd=ROOT)
    after = {p.name: p.read_bytes() for p in SYNTH.glob("*.json")}
    assert before == after


def test_produces_exactly_seven_files() -> None:
    files = sorted(p.stem for p in SYNTH.glob("*.json"))
    assert files == sorted(PERSONAS)


# --- schema validation -----------------------------------------------------

PROFILE_REQUIRED = {
    "id", "name", "age", "city", "segment", "language", "risk_tolerance",
    "dependents", "occupation", "avatar", "story",
}
TXN_REQUIRED = {"id", "date", "amount", "type", "category", "description", "account"}
GOAL_REQUIRED = {"name", "horizon_years", "target", "saved_so_far"}
HOLDING_REQUIRED = {"id", "type", "institution", "amount", "rate"}
LIABILITY_REQUIRED = {"id", "type", "lender", "principal", "rate", "emi"}
EXTERNAL_REQUIRED = {"aa_available", "connected", "holdings", "liabilities"}


@pytest.mark.parametrize("persona", PERSONAS)
def test_schema_top_level(persona: str) -> None:
    data = load(persona)
    assert set(data.keys()) >= {"profile", "transactions", "goals", "external"}


@pytest.mark.parametrize("persona", PERSONAS)
def test_schema_profile(persona: str) -> None:
    profile = load(persona)["profile"]
    assert PROFILE_REQUIRED <= profile.keys()
    assert isinstance(profile["id"], str) and profile["id"] == persona
    assert isinstance(profile["age"], int) and 18 <= profile["age"] <= 100
    assert isinstance(profile["story"], str) and len(profile["story"]) > 20
    assert isinstance(profile["occupation"], str) and profile["occupation"]
    avatar = profile["avatar"]
    assert isinstance(avatar, str) and avatar
    assert avatar.isascii(), "avatar must be a short string identifier, not an emoji"


@pytest.mark.parametrize("persona", PERSONAS)
def test_schema_transactions(persona: str) -> None:
    data = load(persona)
    txns = data["transactions"]
    assert len(txns) > 0
    seen_ids = set()
    for t in txns:
        assert TXN_REQUIRED <= t.keys()
        assert t["id"] not in seen_ids, f"duplicate txn id {t['id']!r}"
        seen_ids.add(t["id"])
        assert t["type"] in ("credit", "debit")
        assert t["account"] in ("sa", "ca", "cc")
        assert isinstance(t["amount"], (int, float)) and t["amount"] > 0
        assert t["description"], "every transaction must have a description"
        expected = categorize(t["description"])
        assert expected == t["category"], (
            f"{persona}: description {t['description']!r} categorizes as "
            f"{expected!r} but stored category is {t['category']!r}"
        )
    # chronological order preserved after id assignment
    dates = [t["date"] for t in txns]
    assert dates == sorted(dates)


@pytest.mark.parametrize("persona", PERSONAS)
def test_schema_goals(persona: str) -> None:
    goals = load(persona)["goals"]
    for g in goals:
        assert GOAL_REQUIRED <= g.keys()
        assert g["target"] > 0
        assert g["saved_so_far"] >= 0
        assert g["horizon_years"] > 0


@pytest.mark.parametrize("persona", PERSONAS)
def test_schema_external(persona: str) -> None:
    external = load(persona)["external"]
    assert EXTERNAL_REQUIRED <= external.keys()
    assert isinstance(external["aa_available"], bool)
    assert isinstance(external["connected"], bool)
    seen_ids = set()
    for h in external["holdings"]:
        assert HOLDING_REQUIRED <= h.keys()
        assert h["id"] not in seen_ids
        seen_ids.add(h["id"])
        assert h["amount"] > 0
    for l in external["liabilities"]:
        assert LIABILITY_REQUIRED <= l.keys()
        assert l["id"] not in seen_ids
        seen_ids.add(l["id"])
        assert l["principal"] > 0
        assert l["emi"] > 0


# --- per-persona shape assertions (exercise the documented demo paths) ---

def _months_present(txns: list[dict[str, Any]]) -> int:
    return len({t["date"][:7] for t in txns})


def _monthly_income(txns: list[dict[str, Any]]) -> float:
    credits = sum(t["amount"] for t in txns if t["type"] == "credit")
    return credits / _months_present(txns)


def _monthly_category_spend(txns: list[dict[str, Any]], category: str) -> float:
    total = sum(t["amount"] for t in txns if t["type"] == "debit" and t["category"] == category)
    return total / _months_present(txns)


def test_vikram_is_emi_stressed() -> None:
    data = load("vikram")
    income = _monthly_income(data["transactions"])
    emi = _monthly_category_spend(data["transactions"], "emi")
    assert emi / income > 0.4
    assert data["external"]["liabilities"][0]["rate"] == 14.0


def test_meera_is_cash_surplus_heavy() -> None:
    data = load("meera")
    txns = data["transactions"]
    income = _monthly_income(txns)
    spend = sum(
        _monthly_category_spend(txns, cat)
        for cat in {t["category"] for t in txns if t["type"] == "debit"}
    )
    surplus = income - spend
    assert surplus / income > 0.4 or surplus > 100000


def test_ravi_has_auto_execute_sip() -> None:
    data = load("ravi")
    assert any(t["category"] == "investment" for t in data["transactions"])
    assert data["profile"]["segment"] == "mass_retail_salaried"


def test_shanta_is_conservative_voice_first() -> None:
    profile = load("shanta")["profile"]
    assert profile["language"] == "hi"
    assert profile["risk_tolerance"] == "conservative"


def test_arjun_is_nri() -> None:
    profile = load("arjun")["profile"]
    assert profile["segment"] == "nri"
    assert any(t["category"] == "transfer_in" for t in load("arjun")["transactions"])


def test_devika_is_hni_with_rich_external_holdings() -> None:
    data = load("devika")
    assert data["external"]["aa_available"] is True
    total_holdings = sum(h["amount"] for h in data["external"]["holdings"])
    assert total_holdings > 15_000_000
    assert len(data["external"]["holdings"]) >= 4


def test_priya_has_no_aa_and_no_salary_pattern() -> None:
    data = load("priya")
    assert data["external"]["aa_available"] is False
    assert data["external"]["holdings"] == []
    assert data["external"]["liabilities"] == []

    credits = [t for t in data["transactions"] if t["type"] == "credit"]
    assert not any(t["category"] == "salary" for t in credits)

    # a fixed salary would show the same (day-of-month, amount) pair almost every month;
    # guard against accidentally generating a regular payroll-like pattern.
    pattern_counts = Counter((t["date"][8:10], t["amount"]) for t in credits)
    assert max(pattern_counts.values()) <= 2


def test_all_personas_are_self_contained() -> None:
    for persona in PERSONAS:
        data = load(persona)
        assert len(data["transactions"]) >= 20
        assert len(data["goals"]) >= 1
