"""Ordered-keyword transaction categorizer — 16 categories, first-match-wins.

Ported byte-identical from the old MVP (`git show 54e7080:backend/app/analytics.py`);
the rule table lives in `constants.CATEGORY_RULES` so it stays the single
source of truth for both this function and the generator's labels.
"""

from __future__ import annotations

from .constants import CATEGORY_RULES


def categorize(description: str) -> str:
    text = description.lower()
    for category, keywords in CATEGORY_RULES:
        if any(keyword in text for keyword in keywords):
            return category
    return "other"
