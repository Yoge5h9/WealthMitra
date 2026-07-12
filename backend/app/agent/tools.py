"""Deterministic tool registry — the agent's only path to data.

Every tool is a thin wrapper that binds the turn's (space, persona_id,
session_id, mode) context, calls into the already-tested deterministic
services (analytics, catalogue, routing), records an audit entry, and returns a
JSON-safe dict. The LLM never touches raw persona state — it only ever sees
these tool results, and the number-audit guardrail later asserts that every
figure in the reply came from one of them.

Two compliance invariants are enforced HERE, in code, not merely in the prompt:
  * `create_rm_lead` only does anything in `rm_lead` mode (and only surfaces a
    lead the orchestrator already built deterministically).
  * `request_execution` refuses any product not tagged `vanilla`, always.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.analytics import AnalyticsEngine
from app.catalogue import CATALOGUE, compare, eligible_shelf, reasons
from app.core import audit
from app.core.spaces import Space
from app.domain.models import AuditEntry, LeadPacket, Metric, Product
from app.gateway.contract import ToolSpec

_AFFLUENT_SEGMENTS = frozenset({"affluent", "hni"})


class ComplianceError(Exception):
    """A tool was invoked in a way a hard compliance invariant forbids."""


@dataclass
class ToolContext:
    """Per-turn binding shared by every tool call."""

    space: Space
    persona_id: str
    session_id: str
    mode: str  # RoutePath: info_only | auto_execute | rm_lead | distress_suppress
    engine: AnalyticsEngine = field(default_factory=AnalyticsEngine)
    now: Callable[[], datetime] = field(default_factory=lambda: (lambda: datetime.now(timezone.utc)))
    built_lead: LeadPacket | None = None
    tool_results: list[dict] = field(default_factory=list)
    called: list[str] = field(default_factory=list)
    confirm: dict | None = None
    _metrics: dict[str, Metric] | None = field(default=None, repr=False)

    def metrics(self) -> dict[str, Metric]:
        if self._metrics is None:
            computed = self.engine.compute(self.space, self.persona_id, now=self.now())
            self._metrics = {m.id: m for m in computed}
        return self._metrics

    @property
    def profile(self):
        return self.space.personas[self.persona_id].profile

    @property
    def external(self):
        return self.space.personas[self.persona_id].external


def _record(ctx: ToolContext, name: str, inputs: dict, outputs_summary: dict, refs: list[str]) -> None:
    audit.record(
        ctx.space,
        AuditEntry(
            id=f"aud_{uuid.uuid4().hex[:12]}",
            session_id=ctx.session_id,
            ts=ctx.now(),
            kind="tool_call",
            name=name,
            inputs=inputs,
            outputs_summary=outputs_summary,
            refs=refs,
        ),
    )


def _mv(ctx: ToolContext, metric_id: str):
    return ctx.metrics()[metric_id].value


def _refs(ctx: ToolContext, *metric_ids: str) -> list[str]:
    out: list[str] = []
    for mid in metric_ids:
        out.extend(ctx.metrics()[mid].source_refs)
    return out


def _product_dict(p: Product) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "tag": p.tag,
        "category": p.category,
        "min_amount": p.min_amount,
        "expected_return": p.expected_return,
        "description": p.description,
    }


def _segment_band_surplus(ctx: ToolContext) -> tuple[str, str, float]:
    return (
        str(_mv(ctx, "suitability_segment")),
        str(_mv(ctx, "risk_band")),
        float(_mv(ctx, "monthly_surplus")),
    )


# --- tool implementations -------------------------------------------------
# Each takes (ctx, **args) and returns a JSON-safe dict.


def get_profile(ctx: ToolContext) -> dict:
    p = ctx.profile
    out = {
        "name": p.name,
        "age": p.age,
        "city": p.city,
        "occupation": p.occupation,
        "dependents": p.dependents,
        "segment": str(_mv(ctx, "suitability_segment")),
        "language": p.language,
    }
    _record(ctx, "get_profile", {}, {"segment": out["segment"]}, [f"profile:{p.id}"])
    return out


def get_spend_summary(ctx: ToolContext, months: int = 3) -> dict:
    spend = dict(_mv(ctx, "spend_by_category"))
    out = {
        "months": months,
        "monthly_income": _mv(ctx, "monthly_income"),
        "spend_by_category": spend,
        "savings_rate": _mv(ctx, "savings_rate"),
    }
    _record(ctx, "get_spend_summary", {"months": months}, {"categories": list(spend)}, _refs(ctx, "spend_by_category"))
    return out


def get_cash_flow(ctx: ToolContext) -> dict:
    out = {
        "monthly_income": _mv(ctx, "monthly_income"),
        "monthly_surplus": _mv(ctx, "monthly_surplus"),
        "idle_balance": _mv(ctx, "idle_balance"),
        "savings_rate": _mv(ctx, "savings_rate"),
        "salary_regularity": _mv(ctx, "salary_regularity"),
        "emi_ratio": _mv(ctx, "emi_ratio"),
    }
    _record(ctx, "get_cash_flow", {}, {"monthly_surplus": out["monthly_surplus"]},
            _refs(ctx, "monthly_income", "monthly_surplus", "idle_balance"))
    return out


def get_net_worth(ctx: ToolContext) -> dict:
    nw = dict(_mv(ctx, "net_worth"))
    out = {"net_worth": nw, "asset_mix": dict(_mv(ctx, "asset_mix"))}
    _record(ctx, "get_net_worth", {}, {"total": nw.get("total")}, _refs(ctx, "net_worth"))
    return out


def get_holdings(ctx: ToolContext) -> dict:
    ext = ctx.external
    connected = ext.connected
    holdings = [h.model_dump(mode="json") for h in ext.holdings] if connected else []
    liabilities = [l.model_dump(mode="json") for l in ext.liabilities] if connected else []
    out = {
        "aa_connected": connected,
        "internal_bank_balance": _mv(ctx, "idle_balance"),
        "external_holdings": holdings,
        "external_liabilities": liabilities,
    }
    refs = _refs(ctx, "idle_balance") + [h.id for h in ext.holdings] if connected else _refs(ctx, "idle_balance")
    _record(ctx, "get_holdings", {}, {"connected": connected, "external_count": len(holdings)}, refs)
    return out


def get_risk_profile(ctx: ToolContext) -> dict:
    out = {
        "capacity_score": _mv(ctx, "capacity_score"),
        "tolerance_score": _mv(ctx, "tolerance_score"),
        "risk_band": _mv(ctx, "risk_band"),
        "suitability_segment": _mv(ctx, "suitability_segment"),
    }
    _record(ctx, "get_risk_profile", {}, {"risk_band": out["risk_band"]}, _refs(ctx, "capacity_score", "tolerance_score"))
    return out


def get_goals(ctx: ToolContext) -> dict:
    out = dict(_mv(ctx, "goal_progress"))
    _record(ctx, "get_goals", {}, {"count": len(out.get("goals", []))}, _refs(ctx, "goal_progress"))
    return out


def get_eligible_products(ctx: ToolContext, category: str | None = None) -> dict:
    """The ONLY product source: matrix-filtered eligible shelf for this customer."""
    segment, band, surplus = _segment_band_surplus(ctx)
    shelf = eligible_shelf(
        segment,
        band,
        category,
        monthly_surplus=surplus,
        is_affluent_or_hni=segment in _AFFLUENT_SEGMENTS,
    )
    products = [_product_dict(p) for p in shelf]
    out = {
        "segment": segment,
        "risk_band": band,
        "category": category,
        "products": products,
    }
    _record(
        ctx,
        "get_eligible_products",
        {"category": category},
        {"segment": segment, "risk_band": band, "count": len(products)},
        [f"matrix:{segment}:{band}"] + [p.id for p in shelf],
    )
    return out


def compare_products(ctx: ToolContext, product_ids: list[str]) -> dict:
    products = [CATALOGUE.products[pid] for pid in product_ids if pid in CATALOGUE.products]
    matrix = compare(products)
    out = {"product_ids": matrix.product_ids, "rows": matrix.rows}
    _record(ctx, "compare_products", {"product_ids": product_ids}, {"compared": matrix.product_ids},
            [f"catalogue:{pid}" for pid in matrix.product_ids])
    return out


def get_literacy(ctx: ToolContext, term: str, language: str = "en") -> dict:
    entry = _GLOSSARY.get(term.strip().lower())
    definition = entry.get(language) or entry.get("en") if entry else (
        f"'{term}' is a financial concept. A specialist can walk you through the details."
    )
    out = {"term": term, "language": language, "definition": definition, "known": entry is not None}
    _record(ctx, "get_literacy", {"term": term, "language": language}, {"known": out["known"]}, [f"glossary:{term.lower()}"])
    return out


def create_rm_lead(ctx: ToolContext, trigger_utterance: str) -> dict:
    """Orchestrator-gated. Surfaces the lead the orchestrator already built in
    rm_lead mode; refuses outright in any other mode.
    """
    if ctx.mode != "rm_lead" or ctx.built_lead is None:
        raise ComplianceError("create_rm_lead is only reachable when routing put the turn in rm_lead mode")
    lead = ctx.built_lead
    out = {
        "lead_id": lead.lead_id,
        "family": lead.family,
        "priority_score": lead.priority_score,
        "status": lead.status,
        "next_best_action": lead.next_best_action,
    }
    _record(ctx, "create_rm_lead", {"trigger_utterance": trigger_utterance},
            {"lead_id": lead.lead_id, "priority_score": lead.priority_score}, [lead.lead_id])
    return out


def request_execution(ctx: ToolContext, product_id: str, amount: int) -> dict:
    """Prepares a confirmation card. NEVER executes. Vanilla products only."""
    if ctx.mode != "auto_execute":
        raise ComplianceError("request_execution is only reachable in auto_execute mode")
    product = CATALOGUE.products.get(product_id)
    if product is None:
        raise ComplianceError(f"unknown product '{product_id}'")
    if product.tag != "vanilla":
        raise ComplianceError(f"request_execution refused: '{product_id}' is tagged '{product.tag}', not vanilla")
    confirm_token = f"cfm_{uuid.uuid4().hex[:16]}"
    payload = {
        "card_type": "execution_confirm",
        "product_id": product.id,
        "product_name": product.name,
        "amount": int(amount),
        "expected_return": product.expected_return,
        "confirm_token": confirm_token,
        "note": "Not executed yet — tap Confirm to proceed.",
    }
    ctx.confirm = payload
    _record(ctx, "request_execution", {"product_id": product_id, "amount": int(amount)},
            {"confirm_token": confirm_token, "executed": False}, [product.id])
    return {"prepared": True, "product_name": product.name, "amount": int(amount), "confirm_token": confirm_token}


def get_nudges(ctx: ToolContext) -> dict:
    """The customer's current nudge feed (Task 13).

    `use_llm=False` here: a chat turn already pays for one live LLM reply,
    and the deterministic i18n template is a fine in-turn substitute for
    LLM-phrased copy — asking the model to phrase every nudge too would add
    a second round-trip to a path that has a tight latency budget. The
    LLM-phrased version of this same feed is what
    `GET /api/customer/{session_id}/nudges` returns.
    """
    from app.nudges import generate_nudges

    nudges = generate_nudges(ctx.space, ctx.persona_id, now=ctx.now(), use_llm=False)
    out = {"nudges": [n.model_dump(mode="json") for n in nudges]}
    _record(ctx, "get_nudges", {}, {"count": len(out["nudges"])}, [])
    return out


def get_aa_status(ctx: ToolContext) -> dict:
    ext = ctx.external
    out = {
        "aa_available": ext.aa_available,
        "connected": ext.connected,
        "external_holdings_count": len(ext.holdings) if ext.connected else 0,
    }
    _record(ctx, "get_aa_status", {}, out, [])
    return out


_GLOSSARY: dict[str, dict[str, str]] = {
    "sip": {
        "en": "A SIP (Systematic Investment Plan) invests a fixed amount at regular intervals, "
              "so you buy more units when prices are low and fewer when high — averaging your cost.",
        "hi": "SIP यानी हर महीने एक तय रकम निवेश करना — जब दाम कम हों तब ज़्यादा यूनिट, दाम ज़्यादा हों तब कम यूनिट मिलती हैं।",
        "gu": "SIP એટલે નિયમિત અંતરે નિશ્ચિત રકમનું રોકાણ — ભાવ ઓછો હોય ત્યારે વધુ યુનિટ મળે.",
    },
    "fd": {
        "en": "A Fixed Deposit locks a lump sum for a fixed term at a fixed interest rate — "
              "capital-safe and predictable.",
        "hi": "फिक्स्ड डिपॉज़िट में एक तय अवधि के लिए तय ब्याज दर पर रकम जमा होती है — पूँजी सुरक्षित रहती है।",
        "gu": "ફિક્સ્ડ ડિપોઝિટમાં નિશ્ચિત મુદત માટે નિશ્ચિત વ્યાજ દરે રકમ જમા થાય છે — મૂડી સલામત.",
    },
    "nps": {
        "en": "The NPS (National Pension System) is a government retirement scheme where your "
              "contributions grow until 60, then part is paid as a lump sum and part as pension.",
        "hi": "एनपीएस एक सरकारी पेंशन योजना है — 60 साल तक आपका योगदान बढ़ता है, फिर कुछ एकमुश्त और कुछ पेंशन के रूप में मिलता है।",
        "gu": "NPS એ સરકારી પેન્શન યોજના છે — 60 વર્ષ સુધી ફાળો વધે, પછી થોડું એકસાથે અને થોડું પેન્શન રૂપે મળે.",
    },
    "mutual fund": {
        "en": "A mutual fund pools money from many investors and a professional manager invests "
              "it across many securities, spreading risk.",
        "hi": "म्यूचुअल फंड कई निवेशकों का पैसा जमा करके पेशेवर प्रबंधक द्वारा कई जगह निवेश करता है, जिससे जोखिम बँटता है।",
        "gu": "મ્યુચ્યુઅલ ફંડ ઘણા રોકાણકારોના પૈસા ભેગા કરી વ્યાવસાયિક રીતે અનેક જગ્યાએ રોકે છે, જોખમ વહેંચાય છે.",
    },
    "risk": {
        "en": "Investment risk is the chance your returns differ from what you expect. We measure "
              "it two ways: your capacity to absorb a loss and your comfort with ups and downs.",
        "hi": "निवेश जोखिम यानी रिटर्न आपकी उम्मीद से अलग होने की संभावना — हम इसे दो तरह से आँकते हैं: नुकसान सहने की क्षमता और उतार-चढ़ाव से सहजता।",
        "gu": "રોકાણ જોખમ એટલે વળતર અપેક્ષા કરતાં અલગ થવાની શક્યતા — અમે તેને બે રીતે માપીએ: નુકસાન સહન કરવાની ક્ષમતા અને વધઘટ સાથે સહજતા.",
    },
}


# --- registry -------------------------------------------------------------

_TOOLSPECS: dict[str, ToolSpec] = {
    "get_profile": ToolSpec(name="get_profile", description="Get the customer's profile and suitability segment.",
                            input_schema={"type": "object", "properties": {}}),
    "get_spend_summary": ToolSpec(name="get_spend_summary",
                                  description="Get spend-by-category, monthly income and savings rate.",
                                  input_schema={"type": "object", "properties": {"months": {"type": "integer", "default": 3}}}),
    "get_cash_flow": ToolSpec(name="get_cash_flow",
                              description="Get monthly income, monthly surplus, idle balance, savings rate and EMI ratio.",
                              input_schema={"type": "object", "properties": {}}),
    "get_net_worth": ToolSpec(name="get_net_worth", description="Get net worth and asset mix.",
                              input_schema={"type": "object", "properties": {}}),
    "get_holdings": ToolSpec(name="get_holdings",
                             description="Get internal balance and any connected out-of-bank holdings/liabilities.",
                             input_schema={"type": "object", "properties": {}}),
    "get_risk_profile": ToolSpec(name="get_risk_profile",
                                 description="Get two-axis risk (capacity, tolerance) and the derived risk band.",
                                 input_schema={"type": "object", "properties": {}}),
    "get_goals": ToolSpec(name="get_goals", description="Get the customer's goals and progress toward them.",
                          input_schema={"type": "object", "properties": {}}),
    "get_eligible_products": ToolSpec(name="get_eligible_products",
                                      description="The ONLY product source: the customer's eligible shelf, optionally filtered by category (deposit, mutual_fund, bond, govt_scheme, etc.).",
                                      input_schema={"type": "object", "properties": {"category": {"type": "string"}}}),
    "compare_products": ToolSpec(name="compare_products",
                                 description="Factual side-by-side comparison of products by id.",
                                 input_schema={"type": "object", "properties": {"product_ids": {"type": "array", "items": {"type": "string"}}}, "required": ["product_ids"]}),
    "get_literacy": ToolSpec(name="get_literacy", description="Get a plain-language definition of a financial term.",
                             input_schema={"type": "object", "properties": {"term": {"type": "string"}, "language": {"type": "string"}}, "required": ["term"]}),
    "create_rm_lead": ToolSpec(name="create_rm_lead",
                               description="Confirm the Relationship-Manager handoff already prepared for this regulated request; returns the lead id.",
                               input_schema={"type": "object", "properties": {"trigger_utterance": {"type": "string"}}, "required": ["trigger_utterance"]}),
    "request_execution": ToolSpec(name="request_execution",
                                  description="Prepare a confirmation for a VANILLA product purchase. Does NOT execute — the customer must confirm.",
                                  input_schema={"type": "object", "properties": {"product_id": {"type": "string"}, "amount": {"type": "integer"}}, "required": ["product_id", "amount"]}),
    "get_nudges": ToolSpec(name="get_nudges", description="Get the customer's pending nudges/notifications.",
                           input_schema={"type": "object", "properties": {}}),
    "get_aa_status": ToolSpec(name="get_aa_status", description="Check Account Aggregator availability and connection status.",
                              input_schema={"type": "object", "properties": {}}),
}

_DISPATCH: dict[str, Callable[..., dict]] = {
    "get_profile": get_profile,
    "get_spend_summary": get_spend_summary,
    "get_cash_flow": get_cash_flow,
    "get_net_worth": get_net_worth,
    "get_holdings": get_holdings,
    "get_risk_profile": get_risk_profile,
    "get_goals": get_goals,
    "get_eligible_products": get_eligible_products,
    "compare_products": compare_products,
    "get_literacy": get_literacy,
    "create_rm_lead": create_rm_lead,
    "request_execution": request_execution,
    "get_nudges": get_nudges,
    "get_aa_status": get_aa_status,
}

# Product-touching tools are removed when the turn is in distress mode.
_PRODUCT_TOOLS = frozenset({"get_eligible_products", "compare_products", "request_execution", "create_rm_lead"})

_READ_ONLY = (
    "get_profile", "get_spend_summary", "get_cash_flow", "get_net_worth",
    "get_holdings", "get_risk_profile", "get_goals", "get_literacy",
    "get_nudges", "get_aa_status",
)


LITERACY_TOOL_NAMES: tuple[str, ...] = ("get_literacy",)


def literacy_toolspecs() -> list[ToolSpec]:
    """The minimal toolset for a literacy/definition turn ("what is SIP?").

    Not `tools_for_mode()`: a definition question needs at most a glossary
    lookup, not the mode's full read/shelf/execute registry — offering all of
    that to the model here would burn tools-block tokens the turn never uses.
    """
    return [_TOOLSPECS[n] for n in LITERACY_TOOL_NAMES]


def tools_for_mode(mode: str) -> list[ToolSpec]:
    """The tool list the LLM is offered for a given routing mode.

    distress_suppress → no product tools at all. rm_lead → read-only + eligible
    shelf + create_rm_lead (no execution). auto_execute → read-only + shelf +
    compare + request_execution. info_only → read-only + shelf + compare.
    """
    if mode == "distress_suppress":
        names = list(_READ_ONLY)
    elif mode == "rm_lead":
        names = [*_READ_ONLY, "get_eligible_products", "compare_products", "create_rm_lead"]
    elif mode == "auto_execute":
        names = [*_READ_ONLY, "get_eligible_products", "compare_products", "request_execution"]
    else:  # info_only
        names = [*_READ_ONLY, "get_eligible_products", "compare_products"]
    return [_TOOLSPECS[n] for n in names]


def dispatch(ctx: ToolContext, name: str, arguments: dict) -> dict:
    """Execute a tool by name, enforcing mode gating, and record its result."""
    if name not in _DISPATCH:
        raise ComplianceError(f"unknown tool '{name}'")
    if ctx.mode == "distress_suppress" and name in _PRODUCT_TOOLS:
        raise ComplianceError(f"tool '{name}' is not available while suppressing selling (distress)")
    result = _DISPATCH[name](ctx, **(arguments or {}))
    ctx.called.append(name)
    ctx.tool_results.append(result)
    return result
