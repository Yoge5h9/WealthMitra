"""A deterministic, low-friction cold-start profile journey.

New customers have no account history, so the demo asks four useful questions
before offering the safe next step. It deliberately does not manufacture a
credit or investment recommendation from incomplete data.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.core import audit
from app.core.spaces import Space
from app.domain.models import (
    AuditEntry,
    ExternalHolding,
    Goal,
    PersonaData,
    PersonaExternal,
    PersonaProfile,
    Transaction,
)

_RISK_TOLERANCE_BY_PREFERENCE = {
    "Safety first": "conservative",
    "Balanced": "moderate",
    "Growth": "growth",
}

# Surplus-band answer -> a monthly-amount tier. Every figure below is fixed
# (no randomness) so the synthetic ledger is stable across runs for the same
# answers.
_SURPLUS_TIER_BY_BAND = {
    "Under ₹5,000": "low",
    "₹5,000–₹25,000": "mid",
    "Above ₹25,000": "high",
}
_DEFAULT_TIER = "mid"

# income (credit) description + category per income-type answer. Description
# text is what `categorize()` actually reads (see app.analytics.categorize) —
# the `category` field here is informational only.
_INCOME_BY_TYPE: dict[str, tuple[str, str]] = {
    "Salaried": ("Salary credit - Infosys Ltd", "salary"),
    "Retired": ("Pension credit - EPFO", "pension"),
    "Business or freelance": ("Client payment - consulting fee", "business_income"),
}
_DEFAULT_INCOME_TYPE = "Salaried"

# One fixed monthly debit basket, sized per tier below. (key, description, category)
_DEBIT_TEMPLATE: tuple[tuple[str, str, str], ...] = (
    ("rent", "Rent payment - monthly", "rent"),
    ("groceries", "Bigbasket grocery order", "food"),
    ("utilities", "Electricity bill payment", "utilities"),
    ("transport", "Ola cab rides", "travel"),
    ("shopping", "Amazon shopping order", "shopping"),
    ("dining", "Zomato food order", "food"),
)

# income + per-debit-key monthly amounts, tuned so income - Σdebits lands
# inside the stated surplus band: low ~₹4k, mid ~₹17.5k, high ~₹40k.
_TIER_AMOUNTS: dict[str, dict[str, float]] = {
    "low": {
        "income": 25000.0, "rent": 9000.0, "groceries": 4000.0, "utilities": 2200.0,
        "transport": 1800.0, "shopping": 2500.0, "dining": 1500.0,
    },
    "mid": {
        "income": 55000.0, "rent": 16000.0, "groceries": 7000.0, "utilities": 3200.0,
        "transport": 3000.0, "shopping": 5000.0, "dining": 3300.0,
    },
    "high": {
        "income": 92000.0, "rent": 22000.0, "groceries": 9000.0, "utilities": 4000.0,
        "transport": 4500.0, "shopping": 8000.0, "dining": 4500.0,
    },
}

# Two modest AA-linkable external holdings per tier, mirroring the shape of
# data/synthetic/ravi.json's holdings (an out-of-bank MF + an FD).
_HOLDINGS_BY_TIER: dict[str, tuple[tuple[str, str, float, float], ...]] = {
    "low": (
        ("mutual_fund", "ICICI Prudential AMC", 15000.0, 11.0),
        ("FD", "Axis Bank", 20000.0, 6.8),
    ),
    "mid": (
        ("mutual_fund", "ICICI Prudential AMC", 40000.0, 11.0),
        ("FD", "Axis Bank", 60000.0, 6.8),
    ),
    "high": (
        ("mutual_fund", "ICICI Prudential AMC", 90000.0, 11.0),
        ("FD", "Axis Bank", 150000.0, 6.8),
    ),
}

# priority answer -> (goal name, horizon_years, target, saved_so_far)
_GOAL_BY_PRIORITY: dict[str, tuple[str, int, float, float]] = {
    "Save safely": ("Emergency fund", 1, 150000.0, 30000.0),
    "Start investing": ("Wealth building", 5, 500000.0, 25000.0),
    "Protect my family": ("Family protection fund", 3, 300000.0, 20000.0),
    "Manage my EMIs": ("Debt payoff", 2, 200000.0, 40000.0),
}
_DEFAULT_PRIORITY = "Save safely"

_MONTHS: tuple[int, ...] = (1, 2, 3, 4, 5, 6)  # 2026-01 .. 2026-06, fixed calendar window

_QUESTIONS = (
    ("priority", "What would you like help with first?", ["Save safely", "Start investing", "Manage my EMIs", "Protect my family"]),
    ("income", "Which best describes your income?", ["Salaried", "Business or freelance", "Retired"]),
    ("surplus", "How much could you usually set aside each month?", ["Under ₹5,000", "₹5,000–₹25,000", "Above ₹25,000"]),
    ("preference", "Which approach feels right today?", ["Safety first", "Balanced", "Growth"]),
)


def _audit(space: Space, session_id: str, name: str, inputs: dict, outputs: dict) -> str:
    entry_id = f"aud_onboarding_{session_id[-8:]}_{name}"
    audit.record(
        space,
        AuditEntry(
            id=entry_id,
            session_id=session_id,
            ts=datetime.now(timezone.utc),
            kind="guardrail",
            name=name,
            inputs=inputs,
            outputs_summary=outputs,
            refs=["onboarding:v1"],
        ),
    )
    return entry_id


def _build_transactions(tier: str, income_description: str, income_category: str) -> list[Transaction]:
    """One income credit + a fixed 6-item debit basket per month, for the
    fixed 2026-01..2026-06 window. Same amounts every month by design — that
    consistency is what makes the primary-income stream read as regular
    (`salary_regularity` ~1.0) rather than irregular.
    """
    amounts = _TIER_AMOUNTS[tier]
    txns: list[Transaction] = []
    seq = 1
    for month in _MONTHS:
        txns.append(
            Transaction(
                id=f"txn-newidbi-{seq:04d}",
                date=date(2026, month, 1),
                amount=amounts["income"],
                type="credit",
                category=income_category,
                description=income_description,
                account="sa",
            )
        )
        seq += 1
        for offset, (key, description, category) in enumerate(_DEBIT_TEMPLATE):
            txns.append(
                Transaction(
                    id=f"txn-newidbi-{seq:04d}",
                    date=date(2026, month, 5 + offset * 3),
                    amount=amounts[key],
                    type="debit",
                    category=category,
                    description=description,
                    account="sa",
                )
            )
            seq += 1
    return txns


def _build_holdings(tier: str) -> list[ExternalHolding]:
    return [
        ExternalHolding(id=f"hold-newidbi-{i + 1}", type=holding_type, institution=institution, amount=amount, rate=rate)
        for i, (holding_type, institution, amount, rate) in enumerate(_HOLDINGS_BY_TIER[tier])
    ]


def _build_goal(priority: str) -> Goal:
    name, horizon_years, target, saved_so_far = _GOAL_BY_PRIORITY.get(priority, _GOAL_BY_PRIORITY[_DEFAULT_PRIORITY])
    return Goal(name=name, horizon_years=horizon_years, target=target, saved_so_far=saved_so_far)


def _build_synthetic_persona(answers: dict, language: str) -> PersonaData:
    """Turn the four onboarding answers into a full `PersonaData` so a
    completed cold-start customer flows through the same orchestrator
    (metrics, routing, RM handoff) as every seeded persona — with a modest,
    deterministic IDBI transaction history and two AA-linkable external
    holdings adapted from those answers, instead of an empty portfolio.
    """
    profile = PersonaProfile(
        id="new_to_idbi",
        name="New to IDBI",
        city="",
        avatar="",
        story="New customer — profile self-declared during onboarding, no account history linked yet.",
        language=language,
        risk_tolerance=_RISK_TOLERANCE_BY_PREFERENCE.get(answers.get("preference", ""), "moderate"),
        occupation=answers.get("income", "Salaried"),
        age=65 if answers.get("income") == "Retired" else 32,
        dependents=1 if answers.get("priority") == "Protect my family" else 0,
        segment="mass_retail_salaried",
    )

    tier = _SURPLUS_TIER_BY_BAND.get(answers.get("surplus", ""), _DEFAULT_TIER)
    income_description, income_category = _INCOME_BY_TYPE.get(
        answers.get("income", ""), _INCOME_BY_TYPE[_DEFAULT_INCOME_TYPE]
    )

    return PersonaData(
        profile=profile,
        transactions=_build_transactions(tier, income_description, income_category),
        goals=[_build_goal(answers.get("priority", ""))],
        external=PersonaExternal(
            aa_available=True, connected=False, holdings=_build_holdings(tier), liabilities=[]
        ),
    )


def greeting(space: Space, session_id: str) -> list[dict]:
    state = space.sessions[session_id]
    if space.new_customer_profile:
        state["onboarding"] = {"step": len(_QUESTIONS), "answers": dict(space.new_customer_profile), "completed": True}
        space.personas["new_to_idbi"] = _build_synthetic_persona(space.new_customer_profile, state["language"])
        ref = _audit(space, session_id, "onboarding_resumed", {}, {"profile_fields": sorted(space.new_customer_profile)})
        return [
            {"type": "avatar", "state": "speaking"},
            {"type": "token", "text": "Welcome back. I remember the starting profile you shared, and I’ll keep using it in this conversation."},
            {"type": "card", "card": _summary_card(space.new_customer_profile)},
            {"type": "card", "card": _aa_connect_card()},
            {"type": "done", "audit_ref": ref},
        ]
    state["onboarding"] = {"step": 0, "answers": {}}
    question = _QUESTIONS[0]
    ref = _audit(space, session_id, "onboarding_started", {}, {"question": question[0]})
    return [
        {"type": "avatar", "state": "speaking"},
        {"type": "token", "text": "Welcome to WealthMitra. I’ll ask four quick questions to understand where to start."},
        {"type": "card", "card": _question_card(0)},
        {"type": "done", "audit_ref": ref},
    ]


def advance(space: Space, session_id: str, answer: str) -> list[dict]:
    state = space.sessions[session_id]
    journey = state["onboarding"]
    if journey.get("completed"):
        remembered = ", ".join(f"{key.replace('_', ' ')}: {value}" for key, value in journey["answers"].items())
        text = f"I remember your starting profile — {remembered}. Link an account when you’re ready so I can make future guidance more specific."
        ref = _audit(space, session_id, "onboarding_memory_recalled", {}, {"profile_fields": sorted(journey["answers"])})
        return [
            {"type": "avatar", "state": "speaking"},
            {"type": "token", "text": text},
            {"type": "card", "card": _summary_card(journey["answers"])},
            {"type": "done", "audit_ref": ref},
        ]
    step = int(journey["step"])
    question_id, _question, options = _QUESTIONS[step]
    selected = next((option for option in options if option.lower() == answer.strip().lower()), answer.strip())
    journey["answers"][question_id] = selected
    journey["step"] = step + 1

    if step + 1 < len(_QUESTIONS):
        next_question = _QUESTIONS[step + 1]
        ref = _audit(space, session_id, "onboarding_answered", {question_id: selected}, {"next_question": next_question[0]})
        return [
            {"type": "avatar", "state": "speaking"},
            {"type": "token", "text": "Thanks — that helps me keep the next step relevant."},
            {"type": "card", "card": _question_card(step + 1)},
            {"type": "done", "audit_ref": ref},
        ]

    journey["completed"] = True
    space.new_customer_profile = dict(journey["answers"])
    space.personas["new_to_idbi"] = _build_synthetic_persona(journey["answers"], state["language"])
    ref = _audit(space, session_id, "onboarding_completed", dict(journey["answers"]), {"personalised_offer": False})
    return [
        {"type": "avatar", "state": "speaking"},
        {"type": "token", "text": "Your starter profile is ready. If you choose to connect external accounts, WealthMitra can bring your wider financial picture into one place."},
        {"type": "card", "card": _summary_card(journey["answers"])},
        {"type": "card", "card": _aa_connect_card()},
        {"type": "done", "audit_ref": ref},
    ]


def _question_card(step: int) -> dict:
    key, question, options = _QUESTIONS[step]
    return {"card_type": "profile_question", "step": step + 1, "total_steps": len(_QUESTIONS), "key": key, "question": question, "options": options}


def _summary_card(answers: dict) -> dict:
    return {"card_type": "profile_summary", "answers": dict(answers), "missing_data": ["Account history", "Goals and existing cover", "Eligibility checks"], "next_step": "Link an account for personalised insights, or ask an RM to discuss loans, cards or insurance."}


def _aa_connect_card() -> dict:
    return {
        "card_type": "aa_connect",
        "headline": "Bring your financial picture together",
        "body": "With your permission, Account Aggregator can connect eligible external accounts so WealthMitra can help you view savings, investments and protection in one place. You control two separate, revocable permissions.",
    }
