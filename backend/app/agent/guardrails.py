"""Number-audit guardrail — "compute the numbers, generate the words".

Every ₹/numeric claim the LLM makes in a reply must be traceable to a figure
that this turn's deterministic tools actually returned. This module extracts
numeric claims from free text (Indian formats, Devanagari/Gujarati digits,
lakh/crore scales, percentages) and checks each against the turn's allowed
figures with a formatting-tolerant match. It never trusts the model to do
arithmetic — it only lets through numbers the data already contains.

The orchestrator uses the verdict to decide whether to accept a reply, force
one stricter regeneration, or fall back to a deterministic template.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

# Devanagari (Hindi) and Gujarati digit ranges → ASCII, so "१२३४" / "૧૨૩૪"
# parse identically to "1234".
_DIGIT_MAP = {ord(c): str(i) for i, c in enumerate("०१२३४५६७८९")}
_DIGIT_MAP.update({ord(c): str(i) for i, c in enumerate("૦૧૨૩૪૫૬૭૮૯")})

# Scale words across en / hi / gu (and common romanizations). Value multiplier.
_SCALES: dict[str, float] = {
    "thousand": 1e3, "k": 1e3, "hazaar": 1e3, "hazar": 1e3,
    "हज़ार": 1e3, "हजार": 1e3, "હજાર": 1e3,
    "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5,
    "लाख": 1e5, "લાખ": 1e5,
    "crore": 1e7, "crores": 1e7, "cr": 1e7,
    "करोड़": 1e7, "करोड": 1e7, "करोड़": 1e7, "કરોડ": 1e7,
}

# Spelled-out numbers that, when paired with a scale word, form a financial
# claim ("two crore", "पाँच लाख", "અઢી લાખ"). Bounded on purpose: a word-number
# WITHOUT a scale word ("give me fifty") is out of scope — it is far more often
# a count/idiom than a rupee claim, and the false-positive cost outweighs it.
_WORD_NUMBERS: dict[str, float] = {
    # en 1–20, tens, half
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "half": 0.5,
    # hi core set + common fractional forms
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "पांच": 5, "छह": 6, "छः": 6,
    "सात": 7, "आठ": 8, "नौ": 9, "दस": 10, "बीस": 20, "पचास": 50,
    "आधा": 0.5, "डेढ़": 1.5, "डेढ": 1.5, "ढाई": 2.5,
    # gu core set + common fractional forms
    "એક": 1, "બે": 2, "ત્રણ": 3, "ચાર": 4, "પાંચ": 5, "છ": 6, "સાત": 7, "આઠ": 8,
    "નવ": 9, "દસ": 10, "વીસ": 20, "પચાસ": 50, "અડધો": 0.5, "દોઢ": 1.5, "અઢી": 2.5,
}
# ASCII scale tokens need a trailing \b so "cr" never matches inside a word
# like "credited"; Indic scale words must NOT require one, because Hindi and
# Gujarati attach case suffixes directly ("करोड़ों", "કરોડનું").
_ASCII_SCALES = sorted((s for s in _SCALES if s.isascii()), key=len, reverse=True)
_INDIC_SCALES = sorted((s for s in _SCALES if not s.isascii()), key=len, reverse=True)
_SCALE_ALTERNATION = (
    "|".join(_INDIC_SCALES) + "|" + "|".join(rf"{s}\b" for s in _ASCII_SCALES)
)

# One pass: optional currency marker, the number (with Indian grouping), an
# optional scale word, an optional percent. Ordering of the scale/percent
# groups is deliberate so "1.2 lakh" and "7.4%" both parse in a single match.
_NUMBER_RE = re.compile(
    r"(?P<cur>₹|rs\.?|inr)?\s*"
    r"(?P<num>\d[\d,]*(?:\.\d+)?)"
    r"\s*(?P<scale>" + _SCALE_ALTERNATION + r")?"
    r"\s*(?P<pct>%|percent|per\s*cent)?",
    re.IGNORECASE,
)

# Spelled-number + scale-word forms ("two crore", "पाँच लाख"). The scale word is
# mandatory here — see the _WORD_NUMBERS scope note. No trailing \b on the word:
# Indic dependent vowel signs (e.g. ી in "અઢી") are combining marks, not word
# chars, so \b fails after them — the mandatory \s+ already ends the word.
_WORD_ALTERNATION = "|".join(sorted(_WORD_NUMBERS, key=len, reverse=True))
_WORD_NUMBER_RE = re.compile(
    r"\b(?P<word>" + _WORD_ALTERNATION + r")\s+(?P<scale>" + _SCALE_ALTERNATION + r")",
    re.IGNORECASE,
)

# Bare integers in this window are treated as non-financial (years) and skipped.
_YEAR_LO, _YEAR_HI = 1900, 2100
# Bare integers with magnitude at/below this are treated as counts/ages/months.
_SMALL_INT_MAX = 100
# "24x7" / "24/7" style tokens are formatting, never financial claims.
_NON_FINANCIAL_TOKENS = re.compile(r"\b\d+\s*[x/]\s*\d+\b", re.IGNORECASE)


@dataclass(frozen=True)
class NumberClaim:
    value: float
    kind: str  # "currency" | "pct" | "plain"
    raw: str


@dataclass
class Verdict:
    ok: bool
    violations: list[NumberClaim] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "ok": self.ok,
            "violation_count": len(self.violations),
            "violations": [{"value": v.value, "kind": v.kind, "raw": v.raw} for v in self.violations],
        }


def _normalize_digits(text: str) -> str:
    return text.translate(_DIGIT_MAP)


def extract_numbers(text: str) -> list[NumberClaim]:
    """Extract every numeric claim from `text` as canonical floats.

    lakh/crore scales are applied (so "1.2 lakh" → 120000.0); percentages keep
    their face value ("7.4%" → 7.4). Devanagari/Gujarati digits are mapped to
    ASCII first. Tokens like "24x7" are excluded — they are formatting, not
    financial claims.
    """
    if not text:
        return []
    normalized = _normalize_digits(text)
    # Blank out non-financial formatting tokens so their digits aren't harvested.
    scrubbed = _NON_FINANCIAL_TOKENS.sub(" ", normalized)

    claims: list[NumberClaim] = []
    for m in _NUMBER_RE.finditer(scrubbed):
        num = m.group("num")
        if num is None:
            continue
        try:
            value = float(num.replace(",", ""))
        except ValueError:
            continue
        scale = m.group("scale")
        if scale:
            value *= _SCALES[scale.lower()]
        if m.group("pct"):
            kind = "pct"
        elif m.group("cur") or scale:
            kind = "currency"
        else:
            kind = "plain"
        claims.append(NumberClaim(value=value, kind=kind, raw=m.group(0).strip()))

    for m in _WORD_NUMBER_RE.finditer(scrubbed):
        word_value = _WORD_NUMBERS[m.group("word").lower()]
        multiplier = _SCALES[m.group("scale").lower()]
        claims.append(
            NumberClaim(value=word_value * multiplier, kind="currency", raw=m.group(0).strip())
        )
    return claims


def _collect_allowed(obj: object, amounts: set[float], percents: set[float]) -> None:
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        v = float(obj)
        amounts.add(v)
        if 0 < v < 1:
            percents.add(round(v * 100, 4))  # ratio → percent (savings_rate etc.)
        if 0 < v < 100:
            percents.add(v)  # a stored rate like 6.5 should match "6.5%"
        return
    if isinstance(obj, str):
        for c in extract_numbers(obj):
            if c.kind == "pct":
                percents.add(c.value)
            else:
                amounts.add(c.value)
        return
    if isinstance(obj, dict):
        for v in obj.values():
            _collect_allowed(v, amounts, percents)
        return
    if isinstance(obj, (list, tuple)):
        for v in obj:
            _collect_allowed(v, amounts, percents)


def build_allowed(tool_results: list[dict], extra: list[object] | None = None) -> tuple[set[float], set[float]]:
    """Union of every figure this turn's tools returned (plus any extras).

    Returns (allowed_amounts, allowed_percents). Everything is serialized then
    re-extracted so numbers embedded in display strings ("7.4% p.a.") count too.
    """
    amounts: set[float] = set()
    percents: set[float] = set()
    for result in tool_results:
        _collect_allowed(result, amounts, percents)
    for item in extra or []:
        _collect_allowed(item, amounts, percents)
    return amounts, percents


def _matches_amount(value: float, allowed: set[float]) -> bool:
    av = abs(value)
    for a in allowed:
        scale = max(av, abs(a))
        # 2% flat, hard-capped at ₹1,00,000 — a ₹2Cr figure may drift by at
        # most one lakh, never proportionally more.
        tolerance = min(max(1.0, 0.02 * scale), 100000.0)
        if abs(value - a) <= tolerance:
            return True
        if value >= 1000 and a >= 1000 and round(value / 1000) == round(a / 1000):
            return True
    return False


def _matches_percent(value: float, allowed: set[float]) -> bool:
    return any(abs(value - a) <= 0.15 for a in allowed)


def audit_numbers(reply: str | None, allowed_amounts: set[float], allowed_percents: set[float]) -> Verdict:
    """Return a `Verdict`: every claim in `reply` must trace to an allowed figure.

    Whitelisted without a lookup: bare small integers (ages/counts/months),
    bare four-digit years. Currency- and percent-marked numbers are always
    checked, however small.
    """
    if not reply:
        return Verdict(ok=True)
    violations: list[NumberClaim] = []
    for claim in extract_numbers(reply):
        if claim.kind == "plain":
            is_int = claim.value == int(claim.value)
            if is_int and (abs(claim.value) <= _SMALL_INT_MAX or _YEAR_LO <= claim.value <= _YEAR_HI):
                continue
        if claim.kind == "pct":
            ok = _matches_percent(claim.value, allowed_percents)
        else:
            ok = _matches_amount(claim.value, allowed_amounts)
        if not ok:
            violations.append(claim)
    return Verdict(ok=not violations, violations=violations)


def audit_reply(reply: str | None, tool_results: list[dict], extra: list[object] | None = None) -> Verdict:
    """Convenience wrapper: build the allowed set from tool results, then audit."""
    amounts, percents = build_allowed(tool_results, extra)
    return audit_numbers(reply, amounts, percents)


def format_inr(n: float) -> str:
    """Indian digit grouping: 547386 → "5,47,386" (last 3, then pairs)."""
    value = int(round(n))
    s = str(abs(value))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while head:
            groups.append(head[-2:])
            head = head[:-2]
        s = ",".join(reversed(groups)) + "," + tail
    return ("-" if value < 0 else "") + s


def facts_string(figures: dict[str, float], language: str) -> str:
    """A compact, guardrail-safe facts clause built only from computed figures."""
    surplus = format_inr(figures.get("monthly_surplus", 0))
    idle = format_inr(figures.get("idle_balance", 0))
    if language == "hi":
        return f"मासिक बचत ₹{surplus}, और आपके खाते में ₹{idle} पड़े हैं"
    if language == "gu":
        return f"માસિક બચત ₹{surplus}, અને તમારા ખાતામાં ₹{idle} પડ્યા છે"
    return f"a monthly surplus of ₹{surplus} and ₹{idle} sitting idle in your account"


def safe_template(figures: dict[str, float], language: str) -> str:
    """Deterministic fallback reply — uses only computed figures, so it always
    passes the guardrail. Emitted when a regenerated reply still fails audit.
    """
    facts = facts_string(figures, language)
    if language == "hi":
        return (
            f"आपके खातों से मैं यह पक्का बता सकता हूँ: {facts}। "
            "इससे आगे की किसी भी बात के लिए मैं आपको किसी विशेषज्ञ से जोड़ दूँगा।"
        )
    if language == "gu":
        return (
            f"તમારા ખાતાં પરથી હું આટલું ચોક્કસ કહી શકું છું: {facts}. "
            "આનાથી વધુ કંઈપણ માટે હું તમને નિષ્ણાત સાથે જોડી આપીશ."
        )
    return (
        f"Here's what I can confirm from your accounts: {facts}. "
        "For anything beyond these figures, I'll connect you with a specialist who can help."
    )


def stricter_instruction(verdict: Verdict, allowed_amounts: set[float], allowed_percents: set[float]) -> str:
    """A corrective system note for the single regeneration attempt."""
    bad = ", ".join(sorted({c.raw for c in verdict.violations})) or "(unverifiable figures)"
    amt = ", ".join(f"₹{format_inr(a)}" for a in sorted(allowed_amounts) if a >= 1) or "none"
    pct = ", ".join(f"{p:g}%" for p in sorted(allowed_percents)) or "none"
    return (
        "Your previous reply contained figures not present in the customer's data: "
        f"{bad}. Rewrite the reply using ONLY these verified figures and no others. "
        f"Verified amounts: {amt}. Verified rates: {pct}. "
        "If you cannot make a point without an unverified number, omit the number entirely."
    )


def allowed_debug(tool_results: list[dict]) -> str:
    """Small helper for audit payloads / diagnostics."""
    amounts, percents = build_allowed(tool_results)
    return json.dumps({"amounts": sorted(amounts), "percents": sorted(percents)}, ensure_ascii=False)
