"""Tool registry tests — C.7 names, JSON-safety, audit trail, and the coded
compliance gates (create_rm_lead / request_execution / distress tool removal).
"""

import json
from datetime import datetime, timezone

import pytest

from app.agent import tools
from app.agent.tools import ComplianceError, ToolContext
from app.catalogue import CATALOGUE
from app.core import audit
from app.core.spaces import get_space_store
from app.domain.models import LeadPacket

C7_NAMES = [
    "get_profile", "get_spend_summary", "get_cash_flow", "get_net_worth",
    "get_holdings", "get_risk_profile", "get_goals", "get_eligible_products",
    "compare_products", "get_literacy", "create_rm_lead", "request_execution",
    "get_nudges", "get_aa_status", "evaluate_card_eligibility",
]

_NOW = datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)


@pytest.fixture
def space():
    store = get_space_store()
    return store.get(store.create_space())


def ctx_for(space, persona_id="ravi", mode="info_only") -> ToolContext:
    return ToolContext(space, persona_id, "sess_test", mode, now=lambda: _NOW)


def test_registry_matches_c7_exactly():
    assert sorted(tools._TOOLSPECS) == sorted(C7_NAMES)
    assert sorted(tools._DISPATCH) == sorted(C7_NAMES)
    for name, spec in tools._TOOLSPECS.items():
        assert spec.name == name


@pytest.mark.parametrize("name", C7_NAMES)
def test_every_tool_returns_json_safe_dict_and_audits(space, name):
    mode = {
        "create_rm_lead": "rm_lead",
        "request_execution": "auto_execute",
        "evaluate_card_eligibility": "rm_lead",
    }.get(name, "info_only")
    ctx = ctx_for(space, mode=mode)
    args: dict = {}
    if name == "evaluate_card_eligibility":
        ctx.lead_family = "loans_cards"
    if name == "create_rm_lead":
        ctx.built_lead = _fake_lead()
        args = {"trigger_utterance": "I want equity"}
    elif name == "request_execution":
        args = {"product_id": "index_fund_sip", "amount": 5000}
    elif name == "compare_products":
        args = {"product_ids": ["fd_ladder", "index_fund_sip"]}
    elif name == "get_literacy":
        args = {"term": "sip", "language": "en"}

    result = tools.dispatch(ctx, name, args)
    assert isinstance(result, dict)
    json.dumps(result)  # JSON-safe or this raises

    entries = audit.for_session(space, "sess_test")
    assert entries, name
    assert entries[-1].kind == "tool_call"
    assert entries[-1].name == name


def _fake_lead() -> LeadPacket:
    return LeadPacket(
        lead_id="LP-2026-000042", family="investment_insurance",
        customer={}, trigger={}, financial_snapshot={}, risk={}, goals=[],
        suitability={}, next_best_action="RM to review.", consent={},
        priority_score=50, created_at=_NOW,
    )


def test_get_eligible_products_composes_segment_and_band(space):
    ctx = ctx_for(space, "ravi")
    result = tools.dispatch(ctx, "get_eligible_products", {})
    assert result["segment"] == "mass_retail_salaried"
    assert result["risk_band"] == "moderate"
    assert result["products"], "ravi must have an eligible shelf"
    for product in result["products"]:
        assert product["id"] in CATALOGUE.products


def test_get_eligible_products_category_filter(space):
    ctx = ctx_for(space, "ravi")
    result = tools.dispatch(ctx, "get_eligible_products", {"category": "deposit"})
    assert all(p["category"] == "deposit" for p in result["products"])


def test_holdings_hidden_until_aa_connected(space):
    ctx = ctx_for(space, "ravi")  # ravi has AA available but NOT connected
    result = tools.dispatch(ctx, "get_holdings", {})
    assert result["aa_connected"] is False
    assert result["external_holdings"] == []

    space.personas["ravi"].external.connected = True
    ctx2 = ctx_for(space, "ravi")
    result2 = tools.dispatch(ctx2, "get_holdings", {})
    assert result2["aa_connected"] is True
    assert len(result2["external_holdings"]) == 2


def test_get_nudges_calls_engine_without_llm(space):
    # ravi has salary_consistent + a large idle balance, so this must be
    # non-empty; use_llm=False keeps chat-turn latency low (see tools.py).
    ctx = ctx_for(space, "ravi")
    result = tools.dispatch(ctx, "get_nudges", {})
    assert result["nudges"], "ravi must produce at least one nudge"
    for nudge in result["nudges"]:
        assert nudge["persona_id"] == "ravi"
        assert nudge["kind"] in ("functional", "relational")
        assert nudge["title"] and nudge["body"]


def test_literacy_falls_back_for_unknown_term(space):
    result = tools.dispatch(ctx_for(space), "get_literacy", {"term": "zebra bonds"})
    assert result["known"] is False
    assert "specialist" in result["definition"]


# --- compliance gates (in code, not prompt) ---------------------------------


@pytest.mark.parametrize("mode", ["info_only", "auto_execute", "distress_suppress"])
def test_create_rm_lead_raises_outside_rm_lead_mode(space, mode):
    ctx = ctx_for(space, mode=mode)
    ctx.built_lead = _fake_lead()
    with pytest.raises(ComplianceError):
        tools.create_rm_lead(ctx, trigger_utterance="x")


def test_create_rm_lead_requires_orchestrator_built_lead(space):
    ctx = ctx_for(space, mode="rm_lead")  # no built_lead attached
    with pytest.raises(ComplianceError):
        tools.create_rm_lead(ctx, trigger_utterance="x")


@pytest.mark.parametrize("regulated_id", ["flexicap_mf", "pms_lite", "aif", "structured_note"])
def test_request_execution_refuses_regulated_products(space, regulated_id):
    ctx = ctx_for(space, mode="auto_execute")
    with pytest.raises(ComplianceError, match="not vanilla|tagged"):
        tools.request_execution(ctx, product_id=regulated_id, amount=100000)


@pytest.mark.parametrize("mode", ["info_only", "rm_lead", "distress_suppress"])
def test_request_execution_raises_outside_auto_execute(space, mode):
    ctx = ctx_for(space, mode=mode)
    with pytest.raises(ComplianceError):
        tools.request_execution(ctx, product_id="index_fund_sip", amount=5000)


def test_request_execution_never_executes(space):
    ctx = ctx_for(space, mode="auto_execute")
    result = tools.dispatch(ctx, "request_execution", {"product_id": "fd_ladder", "amount": 25000})
    assert result["prepared"] is True
    assert result["confirm_token"].startswith("cfm_")
    assert ctx.confirm is not None
    assert ctx.confirm["card_type"] == "execution_confirm"
    entry = audit.for_session(space, "sess_test")[-1]
    assert entry.outputs_summary["executed"] is False


def test_distress_mode_removes_product_tools():
    names = {t.name for t in tools.tools_for_mode("distress_suppress")}
    assert names.isdisjoint({"get_eligible_products", "compare_products", "request_execution", "create_rm_lead"})
    assert "get_cash_flow" in names
    assert "get_literacy" in names


def test_distress_mode_dispatch_refuses_product_tools(space):
    ctx = ctx_for(space, mode="distress_suppress")
    with pytest.raises(ComplianceError):
        tools.dispatch(ctx, "get_eligible_products", {})


def test_tools_for_mode_gating_table():
    by_mode = {mode: {t.name for t in tools.tools_for_mode(mode)} for mode in
               ("info_only", "auto_execute", "rm_lead", "distress_suppress")}
    assert "request_execution" in by_mode["auto_execute"]
    assert "request_execution" not in by_mode["info_only"]
    assert "request_execution" not in by_mode["rm_lead"]
    assert "create_rm_lead" in by_mode["rm_lead"]
    assert "create_rm_lead" not in by_mode["auto_execute"]
    assert "create_rm_lead" not in by_mode["info_only"]


# --- credit-card eligibility tool + consent-gated lead creation -------------


def test_evaluate_card_eligibility_returns_full_verdict_list(space):
    ctx = ctx_for(space, "ravi", mode="rm_lead")
    ctx.lead_family = "loans_cards"
    result = tools.dispatch(ctx, "evaluate_card_eligibility", {})
    assert "cards" in result
    assert result["cards"], "must return a verdict for every credit card"
    for card in result["cards"]:
        assert {"card_id", "name", "status", "reason"} <= card.keys()


@pytest.mark.parametrize("mode,lead_family", [("info_only", None), ("auto_execute", None), ("rm_lead", None), ("rm_lead", "investment_insurance")])
def test_evaluate_card_eligibility_refused_outside_loans_cards_family(space, mode, lead_family):
    ctx = ctx_for(space, "ravi", mode=mode)
    ctx.lead_family = lead_family
    with pytest.raises(ComplianceError):
        tools.dispatch(ctx, "evaluate_card_eligibility", {})


def test_card_mode_toolset_excludes_investment_shelf_includes_card_tools():
    names = {t.name for t in tools.tools_for_mode("rm_lead", family="loans_cards")}
    assert "evaluate_card_eligibility" in names
    assert "create_rm_lead" in names
    assert "get_eligible_products" not in names
    assert "compare_products" not in names
    assert "request_execution" not in names


def test_investment_family_toolset_unchanged_and_excludes_card_tool():
    names = {t.name for t in tools.tools_for_mode("rm_lead", family="investment_insurance")}
    assert "get_eligible_products" in names
    assert "compare_products" in names
    assert "create_rm_lead" in names
    assert "evaluate_card_eligibility" not in names
    # No family passed at all (existing callers) must behave identically.
    assert names == {t.name for t in tools.tools_for_mode("rm_lead")}


def test_distress_mode_excludes_card_eligibility_tool():
    names = {t.name for t in tools.tools_for_mode("distress_suppress")}
    assert "evaluate_card_eligibility" not in names


def test_create_rm_lead_for_card_requires_card_id(space):
    ctx = ctx_for(space, "ravi", mode="rm_lead")
    ctx.lead_family = "loans_cards"
    ctx.card_lead_builder = lambda card_id, trigger, verdict: _fake_lead()
    with pytest.raises(ComplianceError):
        tools.dispatch(ctx, "create_rm_lead", {"trigger_utterance": "yes please"})


def test_create_rm_lead_for_card_requires_a_configured_builder(space):
    ctx = ctx_for(space, "ravi", mode="rm_lead")
    ctx.lead_family = "loans_cards"
    with pytest.raises(ComplianceError):
        tools.dispatch(ctx, "create_rm_lead", {"trigger_utterance": "yes", "card_id": "idbi_aspire_platinum"})


def test_create_rm_lead_for_card_rejects_unknown_card_id(space):
    ctx = ctx_for(space, "ravi", mode="rm_lead")
    ctx.lead_family = "loans_cards"
    ctx.card_lead_builder = lambda card_id, trigger, verdict: _fake_lead()
    with pytest.raises(ComplianceError):
        tools.dispatch(ctx, "create_rm_lead", {"trigger_utterance": "yes", "card_id": "not_a_real_card"})


def test_create_rm_lead_for_card_delegates_to_the_orchestrator_builder_with_the_right_verdict(space):
    ctx = ctx_for(space, "ravi", mode="rm_lead")
    ctx.lead_family = "loans_cards"
    captured: dict = {}

    def builder(card_id, trigger, verdict):
        captured["card_id"] = card_id
        captured["trigger"] = trigger
        captured["verdict"] = verdict
        return _fake_lead()

    ctx.card_lead_builder = builder
    result = tools.dispatch(ctx, "create_rm_lead", {"trigger_utterance": "apply for Aspire", "card_id": "idbi_aspire_platinum"})
    assert captured["card_id"] == "idbi_aspire_platinum"
    assert captured["trigger"] == "apply for Aspire"
    assert captured["verdict"]["card_id"] == "idbi_aspire_platinum"
    assert result["lead_id"] == "LP-2026-000042"
    entry = audit.for_session(space, "sess_test")[-1]
    assert entry.name == "create_rm_lead"


def test_unknown_tool_raises(space):
    with pytest.raises(ComplianceError):
        tools.dispatch(ctx_for(space), "transfer_funds", {})


def test_dispatch_accumulates_results_for_guardrail(space):
    ctx = ctx_for(space)
    tools.dispatch(ctx, "get_cash_flow", {})
    tools.dispatch(ctx, "get_profile", {})
    assert ctx.called == ["get_cash_flow", "get_profile"]
    assert len(ctx.tool_results) == 2
