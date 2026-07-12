"""Named constants for the analytics engine — every magic number from the
ported old-MVP formulas (`git show 54e7080:backend/app/analytics.py`) lives
here, named, so `categorize.py`/`cashflow.py`/`risk.py`/`segment.py`/
`networth.py` read like their own spec instead of hiding thresholds inline.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

# --- Categorizer: 16 categories (15 explicit + "other"), ordered keyword
# rules, first-match-wins. Ported byte-identical from the old MVP. ---

CATEGORIES: list[str] = [
    "salary", "business_income", "pension", "transfer_in", "food", "shopping",
    "utilities", "rent", "emi", "travel", "entertainment", "healthcare",
    "education", "investment", "cash_withdrawal", "other",
]

CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
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

# Order matters: the first of these with a matching credit txn is treated as
# the persona's "primary income" stream for salary-regularity purposes.
PRIMARY_INCOME_CATEGORIES: tuple[str, ...] = ("salary", "pension", "business_income", "transfer_in")

# --- Behaviour-flag thresholds (old MVP `behaviour_flags`) ---
SALARY_CONSISTENT_REGULARITY_MIN = 0.8
IRREGULAR_INCOME_REGULARITY_MAX = 0.5
EMI_STRESSED_RATIO_MIN = 0.4
CASH_SURPLUS_HEAVY_ABS_INR = 100_000.0
CASH_SURPLUS_HEAVY_RATIO_MIN = 0.4
OVERDRAFT_KEYWORD = "overdraft"

# --- Capacity / tolerance / risk-band formula (old MVP `risk_profile`) ---
CAPACITY_BASE = 40.0
CAPACITY_SURPLUS_RATIO_WEIGHT = 40.0
CAPACITY_SURPLUS_RATIO_CAP = 0.6
CAPACITY_REGULARITY_WEIGHT = 15.0
CAPACITY_EMI_RATIO_WEIGHT = 80.0
CAPACITY_DEPENDENT_PENALTY = 2.0
CAPACITY_EMI_STRESSED_PENALTY = 15.0
CAPACITY_OVERDRAFT_PENALTY = 10.0
CAPACITY_MIN = 5
CAPACITY_MAX = 95

TOLERANCE_BY_RISK_APPETITE: dict[str, int] = {"conservative": 25, "moderate": 55, "growth": 82}
TOLERANCE_DEFAULT = 55

RISK_BAND_CONSERVATIVE_MAX = 40
RISK_BAND_MODERATE_MAX = 70

# --- Suitability segment thresholds ---
SENIOR_AGE_THRESHOLD = 60
# External holding institution/type keywords that mark an NRI-linked account
# (e.g. an "ICICI NRE" FD) — `city`/`city_tier` aren't available on the
# `PersonaProfile` model, so this is the accessible NRI signal.
NRI_INSTITUTION_KEYWORDS = ("nre", "nri")
HNI_EXTERNAL_HOLDINGS_THRESHOLD_INR = 5_000_000.0  # ₹50L in out-of-bank holdings
AFFLUENT_OCCUPATION_KEYWORD = "business"
DEFAULT_SEGMENT = "mass_retail_salaried"

# --- Net worth / external-inefficiency benchmarks ---
# Documented placeholder rate cards for this prototype (no live IDBI rate feed
# yet). Reused across net-worth and refinance-opportunity detection so both
# features agree on "competitive".
IDBI_FD_BENCHMARK_RATE_PCT = 7.25
IDBI_LOAN_REFINANCE_BENCHMARK_RATE_PCT = 10.5


@dataclass(frozen=True)
class MetricParts:
    """Everything `engine.py` needs to assemble one audited `Metric`, before
    the `id`/`as_of`/`computed_at` envelope (which the engine owns) is applied.
    """

    value: float | str | dict
    unit: str
    source_refs: list[str]
    method: str
    inputs: Any  # canonical payload hashed into Metric.input_hash — inputs, not the output value


def stable_hash(payload: Any) -> str:
    """sha256 over a canonical (sorted-keys) JSON encoding of `payload`.

    Same inputs always produce the same hash — `default=str` covers `date`
    objects so callers can pass raw dataclass/dict payloads without
    pre-serializing them.
    """
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
