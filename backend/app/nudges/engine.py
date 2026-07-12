"""Nudge engine (Task 13): deterministic trigger detection -> quota/ordering
policy -> LLM copy with a guardrail-checked, deterministic-template fallback.

"Compute the numbers, generate the words" applies here exactly as it does in
`app.agent.orchestrator`: every trigger in `triggers.py` computes facts from
already-audited `Metric`s (or, for `overspend_vs_baseline`, straight from the
ledger); this module never lets the LLM add a figure that wasn't already in
those facts — `nudge_copy` phrasing is checked by the same number-audit
guardrail the chat turn uses, and falls back to the deterministic i18n
template (`templates.py`) on any violation or malformed response.

Structural policy — enforced here in code, not by trigger cooperation:
  * distress (emi_stressed/overdraft) -> ONLY protective functional nudges
    survive; every opportunity/contextual/motivational functional candidate
    is dropped outright. Relational nudges are never selling, so they're
    unaffected.
  * functional nudges are capped at `FUNCTIONAL_CAP` per feed, ordered
    protective-first then opportunity by amount desc.
  * the feed never carries more functional nudges than relational ones —
    the weakest functional candidates are dropped (never the reverse) until
    that holds.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.agent import guardrails
from app.analytics import AnalyticsEngine
from app.core.spaces import Space
from app.domain.models import Nudge

from . import templates, triggers
from .triggers import Candidate

FUNCTIONAL_CAP = 3
_DISTRESS_FLAGS = frozenset({"emi_stressed", "overdraft"})
_INTENT_PRIORITY = {"protective": 0, "opportunity": 1, "motivational": 2, "contextual": 3}

_gateway_singleton: Any = None


def _default_gateway() -> Any:
    global _gateway_singleton
    if _gateway_singleton is None:
        from app.gateway import Gateway

        _gateway_singleton = Gateway()
    return _gateway_singleton


def set_gateway(gateway: Any | None) -> None:
    """Override the lazily-built default Gateway — the seam tests (and any
    embedding caller) use to inject a fake, mirroring `app.agent.set_orchestrator`.
    Pass None to restore lazy construction of the real Gateway.
    """
    global _gateway_singleton
    _gateway_singleton = gateway


def _collect_functional(metrics, persona, now: datetime) -> list[Candidate]:
    out: list[Candidate] = []
    for maybe in (
        triggers.idle_balance_high(metrics),
        triggers.salary_credit_moment(metrics),
        triggers.tax_window(now),
        triggers.external_refinance(metrics, persona),
        triggers.overspend_vs_baseline(persona),
        triggers.emi_stress_protective(metrics),
    ):
        if maybe is not None:
            out.append(maybe)
    out.extend(triggers.goal_drift(metrics))
    out.extend(triggers.fd_maturity(persona))
    return out


def _collect_relational(metrics, persona, now: datetime) -> list[Candidate]:
    out: list[Candidate] = []
    story = triggers.monthly_money_story(metrics)
    if story is not None:
        out.append(story)
    out.append(triggers.literacy_micro_lesson(now))
    out.extend(triggers.goal_celebration(metrics))
    tip = triggers.festival_tip(now)
    if tip is not None:
        out.append(tip)
    return out


def _order_functional(candidates: list[Candidate]) -> list[Candidate]:
    return sorted(candidates, key=lambda c: (_INTENT_PRIORITY.get(c.intent, 9), -c.amount))


def _interleave(functional: list[Candidate], relational: list[Candidate]) -> list[Candidate]:
    result: list[Candidate] = []
    for i, f in enumerate(functional):
        result.append(f)
        if i < len(relational):
            result.append(relational[i])
    result.extend(relational[len(functional):])
    return result


def _apply_policy(functional: list[Candidate], relational: list[Candidate], distressed: bool) -> list[Candidate]:
    if distressed:
        functional = [c for c in functional if c.intent == "protective"]

    functional = _order_functional(functional)[:FUNCTIONAL_CAP]
    while len(functional) > len(relational):
        functional.pop()  # drop the weakest (lowest-priority / smallest-amount) candidate first

    return _interleave(functional, relational)


_TITLE_RE = re.compile(r"TITLE:\s*(.+)", re.IGNORECASE)
_BODY_RE = re.compile(r"BODY:\s*(.+)", re.IGNORECASE | re.DOTALL)


def _parse_copy(text: str | None) -> tuple[str, str] | None:
    if not text:
        return None
    title_match = _TITLE_RE.search(text)
    body_match = _BODY_RE.search(text)
    if not title_match or not body_match:
        return None
    title = title_match.group(1).strip().splitlines()[0].strip()
    body = body_match.group(1).strip()
    if not title or not body:
        return None
    return title, body


_INTENT_VOICE = {
    "protective": "Warm and reassuring — this is support, never a sales pitch.",
    "opportunity": "Encouraging but not pushy — this is information, not a hard sell.",
    "motivational": "Encouraging and specific.",
    "contextual": "Matter-of-fact and helpful.",
    "literacy": "Simple, plain-language teaching tone.",
    "celebration": "Warm and genuinely celebratory.",
}
_LANGUAGE_NAME = {"en": "English", "hi": "Hindi (हिंदी)", "gu": "Gujarati (ગુજરાતી)"}


def _copy_prompt(language: str, intent: str, det_title: str, det_body: str) -> str:
    lang_name = _LANGUAGE_NAME.get(language, "English")
    voice = _INTENT_VOICE.get(intent, "Warm and clear.")
    return (
        "You are rewriting a mobile-banking push notification for WealthMitra, a financial "
        "companion app. Rephrase the notification below to sound more natural and warm, in "
        f"{lang_name}. VOICE: {voice}\n\n"
        f"Reference notification:\nTITLE: {det_title}\nBODY: {det_body}\n\n"
        "HARD RULES: Do not add, change, or invent any number, amount, or percentage that is "
        "not already in the reference notification above. Keep the title under 8 words and the "
        "body under 30 words. Reply in EXACTLY this format and nothing else:\n"
        "TITLE: <your title>\nBODY: <your body>"
    )


def _llm_copy(gateway: Any, candidate: Candidate, language: str, det_title: str, det_body: str) -> tuple[str, str]:
    from app.gateway.contract import LLMRequest, Message

    req = LLMRequest(
        messages=[Message(role="system", content=_copy_prompt(language, candidate.intent, det_title, det_body))],
        tool_choice="none",
        task_class="nudge_copy",
        temperature=0.4,
        max_tokens=200,
    )
    try:
        resp = gateway.complete(req)
    except Exception:  # noqa: BLE001 — a copy-phrasing failure must never break the feed
        return det_title, det_body

    parsed = _parse_copy(resp.text)
    if parsed is None:
        return det_title, det_body
    title, body = parsed

    amounts, percents = guardrails.build_allowed([candidate.facts])
    if guardrails.audit_numbers(title, amounts, percents).ok and guardrails.audit_numbers(body, amounts, percents).ok:
        return title, body
    return det_title, det_body


def _stable_id(persona_id: str, candidate: Candidate, day) -> str:
    suffix = f"_{candidate.nonce}" if candidate.nonce else ""
    return f"ndg_{persona_id}_{candidate.template_id}{suffix}_{day.isoformat()}"


def _build_nudge(
    candidate: Candidate, persona_id: str, language: str, now: datetime, *, use_llm: bool, gateway: Any | None,
) -> Nudge:
    det_title, det_body = templates.render(candidate.template_id, language, candidate.facts)
    title, body = (det_title, det_body)
    if use_llm:
        title, body = _llm_copy(gateway or _default_gateway(), candidate, language, det_title, det_body)

    return Nudge(
        id=_stable_id(persona_id, candidate, now.date()),
        persona_id=persona_id,
        kind=candidate.kind,
        intent=candidate.intent,
        title=title,
        body=body,
        language=language,
        source_metric_ids=list(candidate.source_metric_ids),
        created_at=now,
    )


def generate_nudges(
    space: Space,
    persona_id: str,
    *,
    now: datetime,
    use_llm: bool = True,
    gateway: Any | None = None,
) -> list[Nudge]:
    """Deterministic trigger detection -> quota/distress policy -> copy.

    `gateway` is an optional injection point (mirrors `Orchestrator`'s own
    constructor pattern) so tests can supply a fake; production callers can
    omit it and a lazily-built default `Gateway()` is used whenever
    `use_llm=True`.
    """
    persona = space.personas[persona_id]
    metrics = {m.id: m for m in AnalyticsEngine().compute(space, persona_id, now=now)}
    flags = set(metrics["behaviour_flags"].value.get("flags", []))
    distressed = bool(_DISTRESS_FLAGS & flags)
    language = persona.profile.language

    functional = _collect_functional(metrics, persona, now)
    relational = _collect_relational(metrics, persona, now)
    ordered = _apply_policy(functional, relational, distressed)

    return [
        _build_nudge(c, persona_id, language, now, use_llm=use_llm, gateway=gateway)
        for c in ordered
    ]


__all__ = ["generate_nudges", "set_gateway", "FUNCTIONAL_CAP"]
