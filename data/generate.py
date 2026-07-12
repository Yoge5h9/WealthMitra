"""Deterministic synthetic data generator for WealthMitra personas.

Seed is fixed (7) so the committed JSON files are reproducible. Every transaction
description contains a keyword the analytics categorizer maps back to the stored
category, so categorization accuracy is verifiable. No real PII is ever used.

Schema: data/tests/test_generate.py validates every output file against
the domain models' persona schema.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

SEED = 7
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "synthetic"
MONTHS: list[tuple[int, int]] = [(2026, m) for m in range(1, 7)]

FOOD = ["Swiggy order", "Zomato dinner", "BigBasket groceries", "Local restaurant bill", "Grocery store", "Cafe eatery"]
SHOPPING = ["Amazon purchase", "Flipkart order", "Myntra fashion", "Reliance Retail store", "Lifestyle store"]
UTILITIES = ["Electricity bill", "Mobile recharge", "Broadband bill", "Gas bill piped"]
TRAVEL = ["Uber ride", "Ola cab", "IRCTC train ticket", "Petrol fuel", "IndiGo airlines"]
ENTERTAINMENT = ["Netflix subscription", "Spotify subscription", "BookMyShow movie", "Prime Video subscription"]
HEALTHCARE = ["Apollo pharmacy", "Medical checkup", "MedPlus pharmacy", "Diagnostic lab test"]


def _txn(y: int, m: int, day: int, amount: float, ttype: str, category: str, desc: str, account: str) -> dict[str, Any]:
    return {
        "date": f"{y:04d}-{m:02d}-{day:02d}",
        "amount": float(amount),
        "type": ttype,
        "category": category,
        "description": desc,
        "account": account,
    }


def _pick(rng: random.Random, pool: list[str]) -> str:
    return pool[rng.randrange(len(pool))]


def gen_ravi(rng: random.Random) -> dict[str, Any]:
    txns: list[dict[str, Any]] = []
    for y, m in MONTHS:
        txns.append(_txn(y, m, 1, 85000, "credit", "salary", "Salary credit - Infosys Ltd", "sa"))
        txns.append(_txn(y, m, 3, 32000, "debit", "rent", "House rent payment", "sa"))
        txns.append(_txn(y, m, 4, rng.randint(3500, 5000), "debit", "other", "Household supplies and maid", "sa"))
        txns.append(_txn(y, m, 5, 5000, "debit", "investment", "SIP - Nifty Index Fund", "sa"))
        txns.append(_txn(y, m, 8, rng.randint(1200, 1900), "debit", "utilities", "Electricity bill", "sa"))
        txns.append(_txn(y, m, 10, 399, "debit", "utilities", "Mobile recharge postpaid", "sa"))
        txns.append(_txn(y, m, 12, 799, "debit", "utilities", "Broadband bill", "sa"))
        txns.append(_txn(y, m, 5, 649, "debit", "entertainment", "Netflix subscription", "cc"))
        txns.append(_txn(y, m, 6, 119, "debit", "entertainment", "Spotify subscription", "cc"))
        for _ in range(rng.randint(6, 9)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(220, 900), "debit", "food", _pick(rng, FOOD), "cc"))
        for _ in range(rng.randint(2, 4)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(600, 3200), "debit", "shopping", _pick(rng, SHOPPING), "cc"))
        for _ in range(rng.randint(4, 6)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(150, 1200), "debit", "travel", _pick(rng, TRAVEL), "cc"))
        if rng.random() < 0.5:
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(500, 2000), "debit", "healthcare", _pick(rng, HEALTHCARE), "sa"))
        if m == 3:
            txns.append(_txn(y, m, 4, rng.randint(1500, 3000), "debit", "shopping", "Lifestyle store - Holi shopping", "cc"))
        txns.append(_txn(y, m, rng.randint(14, 24), rng.randint(2000, 6000), "debit", "cash_withdrawal", "ATM cash withdrawal", "sa"))
    profile = {
        "id": "ravi", "name": "Ravi Sharma", "age": 28, "city": "Mumbai", "city_tier": "urban_t1",
        "segment": "mass_retail_salaried", "language": "en", "risk_tolerance": "moderate",
        "employment": "salaried", "occupation": "Software Engineer", "dependents": 0, "idle_balance": 140000,
        "avatar": "young_professional_male",
        "story": (
            "Ravi is a 28-year-old software engineer in Mumbai who draws a steady salary and has just started "
            "investing through a Nifty index SIP. He wants his surplus to work harder without touching his "
            "day-to-day cash flow."
        ),
    }
    external = {
        "aa_available": True,
        "connected": False,
        "holdings": [
            {"type": "FD", "institution": "HDFC Bank", "amount": 150000, "rate": 6.5},
            {"type": "NPS", "institution": "NSDL", "amount": 90000, "rate": None},
        ],
        "liabilities": [],
    }
    goals = [
        {"name": "Emergency fund", "horizon_years": 1, "target": 300000, "saved_so_far": 140000},
        {"name": "Retirement corpus", "horizon_years": 25, "target": 20000000, "saved_so_far": 240000},
    ]
    return {"profile": profile, "transactions": txns, "goals": goals, "external": external}


def gen_shanta(rng: random.Random) -> dict[str, Any]:
    txns: list[dict[str, Any]] = []
    for y, m in MONTHS:
        txns.append(_txn(y, m, 1, 18000, "credit", "pension", "Pension credit - EPFO", "sa"))
        if m in (3, 6):
            txns.append(_txn(y, m, 2, 10500, "credit", "other", "FD interest credit payout", "sa"))
        txns.append(_txn(y, m, 9, rng.randint(600, 1000), "debit", "utilities", "Electricity bill", "sa"))
        txns.append(_txn(y, m, 11, 199, "debit", "utilities", "Mobile recharge", "sa"))
        for _ in range(rng.randint(4, 6)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(200, 700), "debit", "food", _pick(rng, FOOD), "sa"))
        for _ in range(rng.randint(1, 2)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(500, 2500), "debit", "healthcare", _pick(rng, HEALTHCARE), "sa"))
        for _ in range(2):
            txns.append(_txn(y, m, rng.randint(6, 26), rng.randint(2000, 4000), "debit", "cash_withdrawal", "ATM cash withdrawal", "sa"))
    profile = {
        "id": "shanta", "name": "Shanta Devi", "age": 61, "city": "Sitapur", "city_tier": "rural",
        "segment": "senior", "language": "hi", "risk_tolerance": "conservative",
        "employment": "retired", "occupation": "Retired School Teacher", "dependents": 0, "idle_balance": 150000,
        "avatar": "senior_woman",
        "fd_amount": 600000, "fd_rate": 7.0, "fd_maturity_date": "2026-07-25",
        "story": (
            "Shanta is a 61-year-old retired schoolteacher living in Sitapur on her pension and a fixed deposit. "
            "She wants safe, simple ways to make her savings last, explained to her in Hindi."
        ),
    }
    external = {
        "aa_available": True,
        "connected": False,
        "holdings": [{"type": "FD", "institution": "SBI", "amount": 200000, "rate": 6.8}],
        "liabilities": [],
    }
    goals = [
        {"name": "Health & contingency reserve", "horizon_years": 3, "target": 500000, "saved_so_far": 200000},
    ]
    return {"profile": profile, "transactions": txns, "goals": goals, "external": external}


def gen_meera(rng: random.Random) -> dict[str, Any]:
    txns: list[dict[str, Any]] = []
    for y, m in MONTHS:
        for i in range(rng.randint(1, 4)):
            txns.append(_txn(y, m, rng.randint(2, 26), rng.randint(40000, 350000), "credit", "business_income",
                             f"Client payment - invoice #{m:02d}{i}", "ca"))
        txns.append(_txn(y, m, 3, 45000, "debit", "rent", "Office rent payment", "ca"))
        txns.append(_txn(y, m, 6, 25000, "debit", "investment", "SIP - Balanced Fund", "sa"))
        txns.append(_txn(y, m, 8, rng.randint(3000, 5500), "debit", "utilities", "Electricity bill", "ca"))
        txns.append(_txn(y, m, 10, 599, "debit", "utilities", "Broadband bill", "ca"))
        for _ in range(rng.randint(3, 5)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(2000, 15000), "debit", "shopping", _pick(rng, SHOPPING), "cc"))
        for _ in range(rng.randint(5, 8)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(300, 1500), "debit", "food", _pick(rng, FOOD), "cc"))
        for _ in range(rng.randint(1, 3)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(2000, 25000), "debit", "travel", _pick(rng, TRAVEL), "cc"))
        if rng.random() < 0.5:
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(1000, 6000), "debit", "healthcare", _pick(rng, HEALTHCARE), "sa"))
        if m == 3:
            txns.append(_txn(y, m, 31, rng.randint(8000, 18000), "debit", "shopping", "Reliance Retail store - Eid shopping", "cc"))
        txns.append(_txn(y, m, rng.randint(12, 24), rng.randint(10000, 20000), "debit", "cash_withdrawal", "ATM cash withdrawal", "ca"))
    profile = {
        "id": "meera", "name": "Meera Patel", "age": 45, "city": "Ahmedabad", "city_tier": "urban_t1",
        "segment": "affluent", "language": "gu", "risk_tolerance": "growth",
        "employment": "business", "occupation": "Textile Trading Business Owner", "dependents": 2,
        "idle_balance": 800000, "avatar": "business_woman_midage",
        "story": (
            "Meera runs a growing textile trading business out of Ahmedabad, so her income arrives in large, "
            "irregular client payments rather than a monthly salary. She's sitting on a healthy cash surplus and "
            "wants to put it to work in equity, but the products are complex enough that she'd rather talk to a "
            "person about the details."
        ),
    }
    external = {
        "aa_available": True,
        "connected": False,
        "holdings": [
            {"type": "MF", "institution": "Axis MF", "amount": 1200000, "rate": None},
            {"type": "FD", "institution": "Kotak Bank", "amount": 500000, "rate": 6.9},
        ],
        "liabilities": [],
    }
    goals = [
        {"name": "Children's higher education", "horizon_years": 8, "target": 6000000, "saved_so_far": 1700000},
    ]
    return {"profile": profile, "transactions": txns, "goals": goals, "external": external}


def gen_arjun(rng: random.Random) -> dict[str, Any]:
    txns: list[dict[str, Any]] = []
    for y, m in MONTHS:
        txns.append(_txn(y, m, 2, 200000, "credit", "transfer_in", "NRE inward remittance", "sa"))
        txns.append(_txn(y, m, 4, 60000, "debit", "other", "Family maintenance transfer", "sa"))
        txns.append(_txn(y, m, 6, 20000, "debit", "investment", "SIP - Index Fund", "sa"))
        txns.append(_txn(y, m, 8, rng.randint(1500, 2500), "debit", "utilities", "Broadband bill", "sa"))
        for _ in range(rng.randint(2, 4)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(500, 4000), "debit", "shopping", _pick(rng, SHOPPING), "cc"))
        for _ in range(rng.randint(2, 3)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(400, 1800), "debit", "food", _pick(rng, FOOD), "cc"))
        if rng.random() < 0.4:
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(8000, 40000), "debit", "travel", "IndiGo airlines ticket", "cc"))
        if m == 3:
            txns.append(_txn(y, m, 31, rng.randint(3000, 7000), "debit", "shopping", "Amazon purchase - Eid gifts for family", "cc"))
    profile = {
        "id": "arjun", "name": "Arjun Nair", "age": 35, "city": "Dubai", "city_tier": "nri",
        "segment": "nri", "language": "en", "risk_tolerance": "moderate",
        "employment": "salaried", "occupation": "Senior Software Engineer (Dubai)", "dependents": 2,
        "idle_balance": 500000, "avatar": "nri_professional_male",
        "story": (
            "Arjun is a 35-year-old NRI software professional based in Dubai who sends money home every month for "
            "family expenses while building an India-based investment corpus for his eventual return."
        ),
    }
    external = {
        "aa_available": True,
        "connected": False,
        "holdings": [
            {"type": "FD", "institution": "ICICI NRE", "amount": 700000, "rate": 7.0},
            {"type": "NPS", "institution": "NSDL", "amount": 150000, "rate": None},
            {"type": "MF", "institution": "SBI MF", "amount": 400000, "rate": None},
        ],
        "liabilities": [],
    }
    goals = [
        {"name": "Return-to-India retirement home", "horizon_years": 10, "target": 15000000, "saved_so_far": 1250000},
    ]
    return {"profile": profile, "transactions": txns, "goals": goals, "external": external}


def gen_vikram(rng: random.Random) -> dict[str, Any]:
    txns: list[dict[str, Any]] = []
    for y, m in MONTHS:
        txns.append(_txn(y, m, 1, 55000, "credit", "salary", "Salary credit - Tech Mahindra", "sa"))
        txns.append(_txn(y, m, 5, 16000, "debit", "emi", "Home loan EMI", "sa"))
        txns.append(_txn(y, m, 7, 8000, "debit", "emi", "Consumer loan EMI installment", "sa"))
        txns.append(_txn(y, m, 9, rng.randint(1200, 1800), "debit", "utilities", "Electricity bill", "sa"))
        txns.append(_txn(y, m, 10, 399, "debit", "utilities", "Mobile recharge", "sa"))
        if m in (2, 5):
            txns.append(_txn(y, m, 28, rng.randint(300, 500), "debit", "other", "Overdraft interest charge", "sa"))
        for _ in range(rng.randint(4, 6)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(200, 800), "debit", "food", _pick(rng, FOOD), "sa"))
        for _ in range(rng.randint(1, 2)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(500, 2500), "debit", "shopping", _pick(rng, SHOPPING), "cc"))
        for _ in range(rng.randint(1, 3)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(150, 900), "debit", "travel", _pick(rng, TRAVEL), "sa"))
        txns.append(_txn(y, m, rng.randint(12, 24), rng.randint(2000, 5000), "debit", "cash_withdrawal", "ATM cash withdrawal", "sa"))
    profile = {
        "id": "vikram", "name": "Vikram Yadav", "age": 32, "city": "Indore", "city_tier": "urban_t2",
        "segment": "mass_retail_salaried", "language": "en", "risk_tolerance": "moderate",
        "employment": "salaried", "occupation": "Sales Executive", "dependents": 2, "idle_balance": 6000,
        "avatar": "stressed_employee_male",
        "story": (
            "Vikram is a 32-year-old sales executive in Indore juggling a home loan and a high-interest personal "
            "loan; his EMIs eat deep into his salary and he could use help easing the pressure rather than "
            "another product pitch."
        ),
    }
    external = {
        "aa_available": True,
        "connected": False,
        "holdings": [],
        "liabilities": [
            {"type": "personal_loan", "lender": "BigFin NBFC", "principal": 320000, "rate": 14.0, "emi": 11000},
        ],
    }
    goals = [
        {"name": "Debt-free emergency buffer", "horizon_years": 2, "target": 200000, "saved_so_far": 6000},
    ]
    return {"profile": profile, "transactions": txns, "goals": goals, "external": external}


def gen_devika(rng: random.Random) -> dict[str, Any]:
    txns: list[dict[str, Any]] = []
    business_credit_desc = [
        "Business receipt - export consignment",
        "Client payment - overseas buyer invoice",
        "Professional fees - consulting retainer",
    ]
    local_cabs = ["Uber ride", "Ola cab"]
    for y, m in MONTHS:
        for _ in range(rng.randint(1, 2)):
            txns.append(_txn(y, m, rng.randint(3, 25), rng.randint(350000, 1400000), "credit", "business_income",
                             _pick(rng, business_credit_desc), "ca"))
        txns.append(_txn(y, m, 3, 150000, "debit", "rent", "Office rent payment - showroom", "ca"))
        txns.append(_txn(y, m, 5, 100000, "debit", "investment", "SIP - Equity Fund top-up", "sa"))
        if m in (1, 4):
            txns.append(_txn(y, m, 7, 500000, "debit", "investment", "FD booking - fresh deposit", "sa"))
        txns.append(_txn(y, m, 8, rng.randint(9000, 15000), "debit", "utilities", "Electricity bill", "ca"))
        txns.append(_txn(y, m, 10, 1499, "debit", "utilities", "Broadband bill", "ca"))
        txns.append(_txn(y, m, 1, 60000, "debit", "other", "Domestic staff wages payout", "sa"))
        for _ in range(rng.randint(2, 3)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(15000, 80000), "debit", "shopping", _pick(rng, SHOPPING), "cc"))
        for _ in range(rng.randint(3, 5)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(2000, 8000), "debit", "food", _pick(rng, FOOD), "cc"))
        txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(45000, 150000), "debit", "travel", "IndiGo airlines business ticket", "cc"))
        for _ in range(rng.randint(3, 5)):
            txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(300, 1200), "debit", "travel", _pick(rng, local_cabs), "cc"))
        txns.append(_txn(y, m, rng.randint(2, 28), rng.randint(3000, 15000), "debit", "healthcare", _pick(rng, HEALTHCARE), "sa"))
        txns.append(_txn(y, m, 5, 649, "debit", "entertainment", "Netflix subscription", "cc"))
        txns.append(_txn(y, m, rng.randint(14, 24), rng.randint(20000, 50000), "debit", "cash_withdrawal", "ATM cash withdrawal", "sa"))
        txns.append(_txn(y, m, 6, 65000, "debit", "emi", "Business loan EMI installment", "ca"))
        if m == 3:
            txns.append(_txn(y, m, 4, rng.randint(20000, 40000), "debit", "shopping", "Lifestyle store - Holi shopping", "cc"))
            txns.append(_txn(y, m, 31, rng.randint(15000, 30000), "debit", "shopping", "Amazon purchase - Eid gifts", "cc"))
    profile = {
        "id": "devika", "name": "Devika Malhotra", "age": 52, "city": "Delhi", "city_tier": "urban_t1",
        "segment": "hni", "language": "en", "risk_tolerance": "growth",
        "employment": "business", "occupation": "Import-Export Business Owner", "dependents": 1,
        "idle_balance": 2500000, "avatar": "hni_business_woman",
        "story": (
            "Devika, 52, built a successful import-export business in Delhi and now sits on a diversified "
            "crore-plus portfolio across FDs, mutual funds, and equity. She's exploring structured products and "
            "PMS for her next allocation, which is exactly the territory that calls for a human relationship "
            "manager."
        ),
    }
    external = {
        "aa_available": True,
        "connected": False,
        "holdings": [
            {"type": "FD", "institution": "HDFC Bank", "amount": 6000000, "rate": 7.1},
            {"type": "FD", "institution": "Axis Bank", "amount": 4000000, "rate": 7.0},
            {"type": "MF", "institution": "ICICI Prudential MF", "amount": 9000000, "rate": None},
            {"type": "equity", "institution": "Zerodha Demat", "amount": 5000000, "rate": None},
            {"type": "NPS", "institution": "NSDL", "amount": 800000, "rate": None},
            {"type": "insurance", "institution": "LIC Endowment", "amount": 1200000, "rate": None},
        ],
        "liabilities": [
            {"type": "business_loan", "lender": "IDBI Bank Working Capital", "principal": 3000000, "rate": 9.5, "emi": 65000},
        ],
    }
    goals = [
        {"name": "Family legacy & philanthropy corpus", "horizon_years": 8, "target": 50000000, "saved_so_far": 26000000},
    ]
    return {"profile": profile, "transactions": txns, "goals": goals, "external": external}


def gen_priya(rng: random.Random) -> dict[str, Any]:
    txns: list[dict[str, Any]] = []
    priya_food = ["Grocery store", "Local restaurant bill", "Swiggy order", "Zomato dinner"]
    for y, m in MONTHS:
        for _ in range(rng.randint(3, 5)):
            txns.append(_txn(y, m, rng.randint(1, 28), rng.randint(1500, 4200), "credit", "business_income",
                             "Delivery gig earnings - invoice settlement", "sa"))
        for _ in range(rng.randint(0, 2)):
            txns.append(_txn(y, m, rng.randint(1, 28), rng.randint(3000, 12000), "credit", "business_income",
                             "Freelance design professional fees", "sa"))
        txns.append(_txn(y, m, rng.randint(1, 5), rng.randint(4000, 5000), "debit", "rent", "House rent payment - shared room", "sa"))
        txns.append(_txn(y, m, rng.randint(8, 12), rng.randint(149, 299), "debit", "utilities", "Mobile recharge prepaid", "sa"))
        for _ in range(rng.randint(5, 8)):
            txns.append(_txn(y, m, rng.randint(1, 28), rng.randint(60, 300), "debit", "food", _pick(rng, priya_food), "sa"))
        for _ in range(rng.randint(6, 9)):
            txns.append(_txn(y, m, rng.randint(1, 28), rng.randint(100, 350), "debit", "travel", "Petrol fuel", "sa"))
        if rng.random() < 0.4:
            txns.append(_txn(y, m, rng.randint(1, 28), rng.randint(100, 600), "debit", "healthcare", "MedPlus pharmacy", "sa"))
        txns.append(_txn(y, m, rng.randint(10, 20), rng.randint(500, 1500), "debit", "cash_withdrawal", "ATM cash withdrawal", "sa"))
        if m == 3:
            txns.append(_txn(y, m, 4, rng.randint(300, 600), "debit", "food", "Local restaurant bill - Holi treat", "sa"))
    profile = {
        "id": "priya", "name": "Priya Meena", "age": 26, "city": "Jaipur", "city_tier": "urban_t2",
        "segment": "mass_retail_gig", "language": "hi", "risk_tolerance": "conservative",
        "employment": "gig_worker", "occupation": "Gig Worker - Delivery & Freelance Design", "dependents": 0,
        "idle_balance": 3200, "avatar": "gig_worker_young_woman",
        "story": (
            "Priya is a 26-year-old gig worker in Jaipur who earns through food-delivery shifts and freelance "
            "design projects, so her income arrives in irregular weekly bursts rather than a fixed salary. She's "
            "never linked any investment accounts and just wants a simple way to build a small emergency cushion."
        ),
    }
    external = {
        "aa_available": False,
        "connected": False,
        "holdings": [],
        "liabilities": [],
    }
    goals = [
        {"name": "Emergency fund", "horizon_years": 1, "target": 20000, "saved_so_far": 3200},
    ]
    return {"profile": profile, "transactions": txns, "goals": goals, "external": external}


def _finalize(persona_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    txns = sorted(payload["transactions"], key=lambda t: t["date"])
    payload["transactions"] = [
        {"id": f"txn-{persona_id}-{i:04d}", **t} for i, t in enumerate(txns, start=1)
    ]
    external = payload["external"]
    external["holdings"] = [
        {"id": f"hold-{persona_id}-{i}", **h} for i, h in enumerate(external["holdings"], start=1)
    ]
    external["liabilities"] = [
        {"id": f"liab-{persona_id}-{i}", **l} for i, l in enumerate(external["liabilities"], start=1)
    ]
    return payload


def build() -> dict[str, dict[str, Any]]:
    rng = random.Random(SEED)
    generators = {
        "ravi": gen_ravi,
        "shanta": gen_shanta,
        "meera": gen_meera,
        "arjun": gen_arjun,
        "vikram": gen_vikram,
        "devika": gen_devika,
        "priya": gen_priya,
    }
    return {pid: _finalize(pid, gen_fn(rng)) for pid, gen_fn in generators.items()}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    existing = {p.name for p in OUT.glob("*.json")}
    produced = set()
    for persona_id, payload in build().items():
        path = OUT / f"{persona_id}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        produced.add(path.name)
        print(f"wrote {path} ({len(payload['transactions'])} txns)")
    for stale in existing - produced:
        (OUT / stale).unlink()
        print(f"removed stale {stale}")


if __name__ == "__main__":
    main()
