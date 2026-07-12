"""A deterministic, low-friction cold-start profile journey.

New customers have no account history, so the demo asks four useful questions
before offering the safe next step. It deliberately does not manufacture a
credit or investment recommendation from incomplete data.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core import audit
from app.core.spaces import Space
from app.domain.models import AuditEntry

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


def greeting(space: Space, session_id: str) -> list[dict]:
    state = space.sessions[session_id]
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

    ref = _audit(space, session_id, "onboarding_completed", dict(journey["answers"]), {"personalised_offer": False})
    return [
        {"type": "avatar", "state": "speaking"},
        {"type": "token", "text": "Your starter profile is ready. Link an account when you’re comfortable, and we can make future guidance more specific."},
        {"type": "card", "card": {"card_type": "profile_summary", "answers": dict(journey["answers"]), "missing_data": ["Account history", "Goals and existing cover", "Eligibility checks"], "next_step": "Link an account for personalised insights, or ask an RM to discuss loans, cards or insurance."}},
        {"type": "done", "audit_ref": ref},
    ]


def _question_card(step: int) -> dict:
    key, question, options = _QUESTIONS[step]
    return {"card_type": "profile_question", "step": step + 1, "total_steps": len(_QUESTIONS), "key": key, "question": question, "options": options}
