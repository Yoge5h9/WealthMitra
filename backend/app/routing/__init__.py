"""Deterministic routing: intent classification, the compliance-gate decision
tree, and Lead Packet construction. No LLM involvement anywhere in this
package — see engine.py for the rationale.
"""

from app.routing.engine import LeadFamily, Route, RoutePath, decide, priority_score, wants_to_buy
from app.routing.intents import Intent, classify_intent, is_generic_card_phrase
from app.routing.leads import age_band, build_lead_packet, city_tier

__all__ = [
    "Intent",
    "classify_intent",
    "is_generic_card_phrase",
    "Route",
    "RoutePath",
    "LeadFamily",
    "decide",
    "priority_score",
    "wants_to_buy",
    "build_lead_packet",
    "age_band",
    "city_tier",
]
