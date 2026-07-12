"""Agent Orchestrator — the compliance-gate-first LLM tool loop.

Turn pipeline (order is the whole design):
  1. classify_intent (deterministic).
  2. compute behaviour flags + segment/risk from analytics.
  3. routing gate `decide(...)` fixes the turn's MODE before any LLM call.
     The mode decides the system prompt, the tool list, and the card.
  4. LLM tool-loop (<=6 rounds), temperature 0.2, over the mode's tools.
  5. number-audit guardrail on the final reply → accept / one regeneration /
     deterministic safe template. Every verdict is audited.

Compliance invariants are enforced in code, not the prompt: regulated products
route to rm_lead and are never auto-executed; distress suppresses all product
tools; the RM lead is built deterministically (the LLM only narrates it); every
figure in the reply must trace to a tool result.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Iterator
from datetime import datetime, timezone

from app.analytics import AnalyticsEngine
from app.catalogue import (
    card_metrics_from_external,
    eligible_shelf,
    evaluate_card_eligibility,
    evaluate_eligibility,
    offer_payload,
    recommendations_for,
    resolve_offer,
)
from app.core import audit, events
from app.core.spaces import Space
from app.domain.models import AuditEntry, LeadPacket, Metric, PersonaExternal, PersonaProfile, Product
from app.gateway.contract import LLMRequest, LLMResponse, Message, TaskClass
from app.routing import Route, build_lead_packet, classify_intent, decide, detect_product_category
from app.routing.leads import tag_for_card_verdict

from . import guardrails, prompts, tools
from .tools import ComplianceError, ToolContext

MAX_TOOL_ROUNDS = 6
# Messages retained/offered for an ordinary conversational turn (8 turns of
# user+assistant pairs) — a sliding window, not a growing transcript.
HISTORY_LIMIT = 16
# A literacy/definition turn ("what is SIP?") needs far less continuity: the
# last exchange or two, not the whole conversation.
LITERACY_HISTORY_WINDOW = 4

_AFFLUENT_SEGMENTS = frozenset({"affluent", "hni"})
_VANILLA_INTENTS = frozenset({"invest_surplus", "fd_query"})
_TASK_CLASS: dict[str, TaskClass] = {
    "rm_lead": "lead_narrative",
    "distress_suppress": "conversational",
    "auto_execute": "conversational",
    "info_only": "conversational",
}
_AVATAR_END = {
    "rm_lead": "speaking",
    "distress_suppress": "concerned",
    "auto_execute": "celebrating",
    "info_only": "speaking",
}
_NEGATIVE = re.compile(r"^\s*(?:no|not now|no thanks|nah|nahi|नहीं|ना|ના)\s*[.!]*\s*$", re.IGNORECASE)

# Intents that mean the customer has clearly moved to a different topic — an
# open card conversation does NOT continue into one of these, it hands off to
# whatever route that intent normally resolves to. Everything else (a bare
# yes/no, "for everyday spend", "pick one for me", or any intent classify_intent
# can't pin down as a fresh topic) is treated as still talking about the card.
_CARD_CONTINUATION_BREAK_INTENTS = frozenset({
    "distress_signal", "rm_handoff", "regulated_query", "credit_product_info",
    "fd_query", "goal_set", "invest_surplus", "aa_connect", "literacy", "greeting",
})


def _default_now() -> datetime:
    return datetime.now(timezone.utc)


def _chunks(text: str) -> list[str]:
    if not text:
        return []
    return re.findall(r"\S+\s*|\s+", text) or [text]


def spend_card(metrics) -> dict:
    return {
        "card_type": "spend_summary",
        "monthly_income": metrics["monthly_income"].value,
        "spend_by_category": dict(metrics["spend_by_category"].value),
        "savings_rate": metrics["savings_rate"].value,
    }


class Orchestrator:
    def __init__(
        self,
        gateway,
        *,
        engine: AnalyticsEngine | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.gateway = gateway
        self.engine = engine or AnalyticsEngine()
        self.now = now or _default_now

    # -- public API --------------------------------------------------------

    def run_turn(
        self, space: Space, session_id: str, message: str, language: str | None = None
    ) -> Iterator[dict]:
        state = space.sessions[session_id]
        if language:
            state["language"] = language
        lang = state["language"]
        persona_id = state["persona_id"]
        persona = space.personas[persona_id]
        profile = persona.profile

        metrics = self._metrics(space, persona_id)
        flags = list(metrics["behaviour_flags"].value.get("flags", []))
        segment = str(metrics["suitability_segment"].value)
        band = str(metrics["risk_band"].value)
        surplus = float(metrics["monthly_surplus"].value)

        intent = classify_intent(message, lang)
        requested_category = detect_product_category(message)
        named_offer = resolve_offer(message)
        if named_offer is not None and intent == "credit_product_info":
            yield from self._credit_product_turn(space, session_id, state, profile, message, named_offer, metrics)
            return

        card_mode_was_open = bool(state.get("card_mode_open"))
        product_ctx = self._representative_product(intent, segment, band, surplus)
        route = decide(intent, flags, product_ctx, card_conversation_open=card_mode_was_open)

        # A follow-up to a card conversation that ended last turn without a
        # lead (a clarifying question still open, or the empathy flow awaiting
        # consent) is not something `classify_intent` can see in isolation —
        # "for everyday spend" classifies as `spend_query`, "go ahead pick
        # yourself" as `other`. Anything that isn't a clear switch to a
        # different topic (see `_CARD_CONTINUATION_BREAK_INTENTS`) stays in the
        # SAME deterministic gate result, never a second scripted flow:
        # distress always still wins, and the flag is consumed (popped)
        # whether or not it ends up being used this turn.
        state.pop("card_mode_open", None)
        continuing_card = card_mode_was_open and intent not in _CARD_CONTINUATION_BREAK_INTENTS
        if continuing_card and route.path != "distress_suppress":
            route = Route(
                path="rm_lead", lead_family="loans_cards",
                reasons=["card_conversation_continuation", f"original_intent:{intent}"],
            )
        # A bare decline of the open card conversation must deterministically
        # block a lead this turn — never left to the model's judgement (see
        # tools.create_rm_lead's ctx.lead_blocked check).
        declined = continuing_card and bool(_NEGATIVE.match(message.strip()))

        mode = route.path
        self._audit_routing(space, session_id, intent, flags, route)

        yield {"type": "avatar", "state": "thinking"}

        ctx = ToolContext(space, persona_id, session_id, mode, engine=self.engine, now=self.now)
        ctx._metrics = metrics
        ctx.lead_blocked = declined

        card_context = None
        if mode == "rm_lead":
            family = route.lead_family or "investment_insurance"
            ctx.lead_family = family
            if family == "loans_cards":
                card_context = self._card_context(profile, persona.external)
                ctx.card_lead_builder = self._make_card_lead_builder(
                    space, session_id, persona_id, metrics, segment, band, surplus
                )
            else:
                existing_lead = self._existing_open_lead(space, state, family)
                if existing_lead is not None:
                    ctx.built_lead = existing_lead
                    ctx.lead_already_shared = True
                else:
                    offer_recommendations = (
                        recommendations_for(profile, {key: metric.value for key, metric in metrics.items()},
                                            family=family, message=message)
                        if "insurance" in message.lower() else []
                    )
                    lead = self._build_lead(
                        space, session_id, persona_id, message, family, metrics, segment, band, surplus, offer_recommendations
                    )
                    ctx.built_lead = lead
                    state.setdefault("rm_leads", {})[family] = lead.lead_id

        # classify_intent already ran deterministically above the routing gate;
        # a literacy/definition question always lands in info_only (it is
        # neither a buy-intent nor a regulated/distress signal — see
        # routing.engine.decide) so this never touches the compliance modes.
        is_literacy = intent == "literacy" and mode == "info_only"
        task_class = "literacy" if is_literacy else _TASK_CLASS[mode]
        prompt_shelf = self._shelf_for_prompt(mode, route.lead_family, segment, band, surplus)
        messages = self._build_messages(
            profile, segment, lang, mode, state, message, literacy=is_literacy,
            lead_family=route.lead_family, card_context=card_context,
            shelf=prompt_shelf, net_worth=metrics["net_worth"].value,
            aa_available=persona.external.aa_available,
            requested_category=requested_category, lead_already_shared=ctx.lead_already_shared,
        )
        toolspecs = tools.literacy_toolspecs() if is_literacy else tools.tools_for_mode(mode, family=route.lead_family)
        final_text = self._tool_loop(space, session_id, ctx, messages, toolspecs, task_class)

        if mode == "auto_execute" and product_ctx is not None:
            final_text = self._ensure_auto_execute_offer(ctx, product_ctx, surplus, lang, final_text)

        final_text, audit_ref = self._guard(
            space, session_id, ctx, messages, task_class, final_text, metrics, lang, message, shelf=prompt_shelf
        )

        self._append_history(state, message, final_text)

        if mode == "rm_lead" and route.lead_family == "loans_cards":
            state["card_mode_open"] = ctx.built_lead is None and not declined

        yield {"type": "avatar", "state": _AVATAR_END[mode]}
        for chunk in _chunks(final_text):
            yield {"type": "token", "text": chunk}
        for card in self._cards(ctx, mode, metrics, segment, band, surplus, product_ctx=product_ctx):
            yield {"type": "card", "card": card}
        yield {"type": "done", "audit_ref": audit_ref}


    # -- pipeline internals ------------------------------------------------

    def _metrics(self, space: Space, persona_id: str) -> dict[str, Metric]:
        return {m.id: m for m in self.engine.compute(space, persona_id, now=self.now())}

    def _representative_product(self, intent: str, segment: str, band: str, surplus: float) -> Product | None:
        """A stand-in vanilla product so routing can decide auto_execute BEFORE
        the LLM picks anything. None if the customer has no eligible vanilla
        product for this intent (then routing falls through to info_only).

        A fixed/recurring deposit is looked up against the CONSERVATIVE band
        regardless of the customer's own risk band: an FD is the most vanilla,
        capital-safe product there is, and a growth-band customer explicitly
        asking to "open an FD" must never dead-end just because their own band
        cell happens to hold only equity-flavoured products.
        """
        if intent not in _VANILLA_INTENTS:
            return None
        category, lookup_band = ("deposit", "conservative") if intent == "fd_query" else (None, band)
        try:
            shelf = eligible_shelf(
                segment, lookup_band, category, monthly_surplus=surplus,
                is_affluent_or_hni=segment in _AFFLUENT_SEGMENTS,
            )
        except ValueError:
            return None
        # Prefer a vanilla product (so a mixed shelf still routes auto_execute).
        # A shelf that is ENTIRELY regulated (e.g. HNI's moderate band) must
        # still attach its first regulated product rather than None — decide()
        # only recognises "this needs an RM" from an attached regulated
        # product; returning None here made an all-regulated shelf look
        # indistinguishable from "no eligible product at all" and silently
        # fell through to info_only instead of the RM hand-off.
        return next((p for p in shelf if p.tag == "vanilla"), next(iter(shelf), None))

    def _shelf_for_prompt(
        self, mode: str, lead_family: str | None, segment: str, band: str | None, surplus: float | None
    ) -> list[Product] | None:
        """The customer's eligible shelf, injected into the system prompt so the
        model never has to gamble on remembering to call `get_eligible_products`
        to learn it has real options — see prompts.shelf_context_block. Not
        computed for distress (no selling) or the loans_cards card conversation
        (that gets the card catalogue via a dedicated tool, never the investment
        shelf, per the compliance boundary between the two product families).

        Always unioned with the segment's CONSERVATIVE-band shelf (deposits/govt
        schemes) even when the customer's own band is different: those products
        are appropriate for anyone regardless of growth appetite, and folding
        them in guarantees a plain FD/RD/govt-scheme option is always groundable
        for an "open an FD" type ask, never only whatever the customer's own
        growth/moderate band happens to contain.
        """
        if mode == "distress_suppress" or (mode == "rm_lead" and lead_family == "loans_cards") or band is None:
            return None
        is_affluent_or_hni = segment in _AFFLUENT_SEGMENTS
        try:
            shelf = eligible_shelf(segment, band, monthly_surplus=surplus, is_affluent_or_hni=is_affluent_or_hni)
        except ValueError:
            return None
        if band != "conservative":
            try:
                conservative = eligible_shelf(
                    segment, "conservative", monthly_surplus=surplus, is_affluent_or_hni=is_affluent_or_hni
                )
            except ValueError:
                conservative = []
            seen = {p.id for p in shelf}
            shelf = shelf + [p for p in conservative if p.id not in seen]
        return shelf

    def _card_context(self, profile: PersonaProfile, external: PersonaExternal) -> dict:
        """The known-facts checklist handed to the loans_cards prompt each
        turn. `fd_visible` mirrors the SAME connected-holdings gate as
        `evaluate_card_eligibility` itself — it only ever reflects a
        currently-visible/consented deposit, never an un-connected one.
        """
        card_metrics = card_metrics_from_external(external)
        verdicts = evaluate_card_eligibility(profile, card_metrics)
        imperium = next((v for v in verdicts if v["card_id"] == "idbi_imperium_platinum"), None)
        return {
            "residency": "NRI" if profile.segment == "nri" else "India resident",
            "age": profile.age,
            "fd_visible": bool(imperium and imperium["status"] == "eligible"),
        }

    def _make_card_lead_builder(self, space, session_id, persona_id, metrics, segment, band, surplus):
        """A closure bound for exactly this turn's loans_cards conversation;
        `create_rm_lead`'s card branch calls it with the customer's chosen
        card_id, a trigger utterance, and the verdict it already looked up —
        this is where the exploratory tag gets decided, deterministically,
        from that verdict's status alone.
        """
        def build(card_id: str, trigger_utterance: str, verdict: dict) -> LeadPacket:
            tag = tag_for_card_verdict(verdict["status"])
            return self._build_lead(
                space, session_id, persona_id, trigger_utterance, "loans_cards",
                metrics, segment, band, surplus, offer_recommendations=[verdict],
                tag=tag,
                eligibility_context={"card_id": card_id, "status": verdict["status"], "reason": verdict.get("reason")},
            )
        return build

    def _build_messages(
        self, profile, segment, lang, mode, state, message, *, literacy: bool,
        lead_family: str | None = None, card_context: dict | None = None,
        shelf: list[Product] | None = None,
        net_worth: dict | None = None, aa_available: bool = False,
        requested_category: tuple[str, str] | None = None, lead_already_shared: bool = False,
    ) -> list[Message]:
        if literacy:
            system_content = prompts.literacy_system_prompt(profile, segment, lang)
            window = LITERACY_HISTORY_WINDOW
        else:
            system_content = prompts.system_prompt(
                profile, segment, lang, mode, lead_family=lead_family, card_context=card_context,
                shelf=shelf, net_worth=net_worth, aa_available=aa_available,
                requested_category=requested_category, lead_already_shared=lead_already_shared,
            )
            window = HISTORY_LIMIT
        msgs = [Message(role="system", content=system_content)]
        for h in state.get("history", [])[-window:]:
            msgs.append(Message(role=h["role"], content=h["content"]))
        msgs.append(Message(role="user", content=message))
        return msgs

    def _tool_loop(self, space, session_id, ctx, messages, toolspecs, task_class) -> str:
        resp: LLMResponse | None = None
        for _ in range(MAX_TOOL_ROUNDS):
            req = LLMRequest(
                messages=messages,
                tools=toolspecs,
                tool_choice="auto",
                task_class=task_class,
                temperature=0.2,
                max_tokens=1024,
            )
            resp = self.gateway.complete(req)
            self._audit_llm(space, session_id, resp, task_class)
            if not resp.tool_calls:
                return resp.text or ""
            messages.append(Message(role="assistant", content=resp.text, tool_calls=resp.tool_calls))
            for call in resp.tool_calls:
                content = self._run_tool(space, session_id, ctx, call)
                messages.append(Message(role="tool", tool_call_id=call.id, content=content))
        return (resp.text if resp else "") or ""

    def _run_tool(self, space, session_id, ctx, call) -> str:
        import json

        try:
            result = tools.dispatch(ctx, call.name, call.arguments)
            return json.dumps(result, ensure_ascii=False)
        except ComplianceError as e:
            self._audit_guardrail(space, session_id, f"tool_refused:{call.name}",
                                  guardrails.Verdict(ok=False), regenerated=False, fell_back=False, note=str(e))
            return json.dumps({"error": str(e), "note": "This action is not permitted here."}, ensure_ascii=False)

    def _ensure_auto_execute_offer(
        self, ctx: ToolContext, product: Product, surplus: float, lang: str, model_text: str
    ) -> str:
        """Guarantee the auto_execute reply always names the deterministically
        routed vanilla product with a real rate/minimum and a confirm
        affordance — regardless of whether the model's own narration this turn
        is clean, harmony-garbled, or a soft dead-end ("I'm not seeing that
        load"). `product` was already resolved deterministically before any
        LLM call (see `_representative_product`), so this never depends on the
        model correctly calling `request_execution` itself.

        If the model DID call `request_execution` (the normal, working path)
        for the SAME product `product_ctx` already routed, its chosen
        amount/confirm card is left untouched — this only fills the gap when
        that call never happened.

        If the model instead confirmed a DIFFERENT vanilla product (its own
        tool call named some product other than `product_ctx`), the routed
        product is authoritative: the confirm is re-issued for it (keeping
        the model's own amount) so the confirm card, the recommendation card
        (also `product_ctx`, see `_cards`), and the narration below can never
        disagree about which product this turn is about. The model's own
        narration is dropped in that case too — it was talking about the
        wrong product, so it must not be prepended to a reply now anchored
        on a different one.
        """
        mismatched = ctx.confirm is not None and ctx.confirm["product_id"] != product.id
        if ctx.confirm is None or mismatched:
            amount = (
                ctx.confirm["amount"] if mismatched
                else int(round(surplus)) if surplus >= product.min_amount else product.min_amount
            )
            tools.request_execution(ctx, product_id=product.id, amount=amount)
        offer = prompts.auto_execute_offer_line(product, ctx.confirm["amount"], lang)
        if mismatched:
            return offer
        lead_in = guardrails.sanitize_output(model_text, lang) or ""
        if lead_in and len(lead_in) <= 240:
            return f"{lead_in} {offer}"
        return offer

    def _guard(
        self, space, session_id, ctx, messages, task_class, final_text, metrics, lang, message,
        *, shelf: list[Product] | None = None,
    ) -> tuple[str, str]:
        # Universal safety net (every mode): strip any harmony-format tool-call
        # leakage or foreign-script spam BEFORE the number audit even looks at
        # the text — a broken/garbled reply must never reach the customer, see
        # guardrails.sanitize_output. `_ensure_auto_execute_offer` already
        # anchors auto_execute in a clean, deterministic line, so this is a
        # defense-in-depth pass there, not the primary fix.
        sanitized = guardrails.sanitize_output(final_text, lang)
        if sanitized is None:
            figures = {
                "monthly_surplus": float(metrics["monthly_surplus"].value),
                "idle_balance": float(metrics["idle_balance"].value),
            }
            safe = guardrails.safe_template(figures, lang)
            ref = self._audit_guardrail(
                space, session_id, "output_sanitizer", guardrails.Verdict(ok=False),
                regenerated=False, fell_back=True, note="reply discarded: unrecoverable after sanitization",
            )
            return safe, ref
        # Invariant #6 (never expose internal terms) is prompt-only otherwise;
        # this is the code-level backstop so a model slip can't leak internal
        # segmentation/catalogue/dev-process vocabulary — see
        # guardrails.strip_internal_jargon.
        final_text = guardrails.strip_internal_jargon(sanitized)

        # The eligible shelf is deterministic, catalogue-sourced data we already
        # put in the system prompt (see `_shelf_for_prompt`) so the model can
        # name a real product's min/return without first calling
        # get_eligible_products — the guardrail's allowed figures must include
        # the same data it was told about, or a well-grounded reply would be
        # wrongly flagged as hallucinated.
        extra = [m.value for m in metrics.values()] + [p.model_dump() for p in (shelf or [])]
        amounts, percents = guardrails.build_allowed(ctx.tool_results, extra)
        guarantee_requested = guardrails.is_guarantee_request(message)
        verdict = guardrails.audit_numbers(final_text, amounts, percents)
        ref = self._audit_guardrail(space, session_id, "number_audit", verdict, regenerated=False, fell_back=False)
        if verdict.ok:
            return final_text, ref

        instruction = guardrails.stricter_instruction(verdict, amounts, percents)
        if guarantee_requested:
            instruction += guardrails.GUARANTEE_REGEN_ADDENDUM
        regen_messages = [*messages, Message(role="system", content=instruction)]
        req = LLMRequest(messages=regen_messages, tools=None, tool_choice="none",
                         task_class=task_class, temperature=0.0, max_tokens=1024)
        resp = self.gateway.complete(req)
        self._audit_llm(space, session_id, resp, task_class)
        regen_text = guardrails.strip_internal_jargon(guardrails.sanitize_output(resp.text, lang) or "")
        verdict2 = guardrails.audit_numbers(regen_text, amounts, percents)
        ref = self._audit_guardrail(space, session_id, "number_audit", verdict2, regenerated=True, fell_back=False)
        if regen_text and verdict2.ok:
            return regen_text, ref

        figures = {
            "monthly_surplus": float(metrics["monthly_surplus"].value),
            "idle_balance": float(metrics["idle_balance"].value),
        }
        # A guarantee-request turn must never fall back to the generic,
        # non-committal facts template — that reads as an evasive dodge (it
        # neither confirms nor denies a guarantee), which is the exact
        # compliance gap this branch closes.
        safe = (
            guardrails.guarantee_refusal_template(figures, lang)
            if guarantee_requested
            else guardrails.safe_template(figures, lang)
        )
        ref = self._audit_guardrail(space, session_id, "number_audit", verdict2, regenerated=True, fell_back=True)
        return safe, ref

    # -- lead construction -------------------------------------------------

    @staticmethod
    def _existing_open_lead(space: Space, state: dict, family: str) -> LeadPacket | None:
        """At most one RM lead per (session, lead_family): a second regulated/
        premium turn in the SAME session and family (e.g. an informational
        "what premium options do I have" followed later by an explicit "go
        ahead with rm") must reuse the lead already created, never create a
        duplicate. `state["rm_leads"]` is this session's own record of which
        lead it already opened per family — see where it is set in `run_turn`.
        A lead the RM console has already marked `converted` no longer counts
        as open, so a genuinely new request afterward can still open one.
        """
        lead_id = state.get("rm_leads", {}).get(family)
        if lead_id is None:
            return None
        lead = next((l for l in space.leads if l.lead_id == lead_id), None)
        if lead is None or lead.status == "converted":
            return None
        return lead

    def _build_lead(
        self, space, session_id, persona_id, message, family, metrics, segment, band, surplus, offer_recommendations,
        *, tag: str = "standard", eligibility_context: dict | None = None,
    ) -> LeadPacket:
        persona = space.personas[persona_id]
        profile: PersonaProfile = persona.profile
        ext = persona.external
        lead_metrics = {
            "monthly_income": metrics["monthly_income"].value,
            "monthly_surplus": metrics["monthly_surplus"].value,
            "idle_balance": metrics["idle_balance"].value,
            "external_holdings": [h.model_dump(mode="json") for h in ext.holdings] if ext.connected else [],
            "liabilities": [l.model_dump(mode="json") for l in ext.liabilities] if ext.connected else [],
            "capacity_score": metrics["capacity_score"].value,
            "tolerance_score": metrics["tolerance_score"].value,
            "risk_band": metrics["risk_band"].value,
            "goals": metrics["goal_progress"].value.get("goals", []),
        }
        shelf = eligible_shelf(segment, band, monthly_surplus=surplus, is_affluent_or_hni=segment in _AFFLUENT_SEGMENTS)
        lead = build_lead_packet(
            profile, lead_metrics, shelf, message, family, seq=len(space.leads) + 1, now=self.now(),
            tag=tag, eligibility_context=eligibility_context,
        )
        # Lead consent must reflect the session's live AA-consent state (as
        # captured by POST /api/aa/consent), not build_lead_packet's static
        # {None, False} placeholder.
        lead = lead.model_copy(update={"consent": self._consent_snapshot(space, session_id)})
        if offer_recommendations:
            next_best_action = (
                f"RM to review {offer_recommendations[0]['name']} eligibility and terms with {profile.name}."
                if family == "loans_cards"
                else f"RM to review {offer_recommendations[0]['name']} suitability and coverage with {profile.name}."
            )
            lead = lead.model_copy(update={"suitability": {
                **lead.suitability,
                "recommended_shelf": [offer["name"] for offer in offer_recommendations],
                "offer_recommendations": offer_recommendations,
                "reasons": ["Offers are ranked from the stated need and profile facts.", "Every offer remains RM-review only."],
            }, "next_best_action": next_best_action})
        space.leads.append(lead)
        audit.record(
            space,
            AuditEntry(
                id=f"aud_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                ts=self.now(),
                kind="routing",
                name="lead_created",
                inputs={"family": family, "trigger": message},
                outputs_summary={"lead_id": lead.lead_id, "priority_score": lead.priority_score},
                refs=[lead.lead_id],
            ),
        )
        events.publish(space.id, {"type": "lead.created", "payload": lead.model_dump(mode="json")})
        return lead

    def _credit_product_turn(self, space, session_id, state, profile, message, offer, metrics):
        eligibility = evaluate_eligibility(profile, {key: metric.value for key, metric in metrics.items()}, offer)
        payload = offer_payload(offer, eligibility)
        text = (
            f"Here are the stored details for {offer.name}. "
            f"{eligibility['reasons'][0]} {offer.display_disclaimer}"
        )
        ref = self._audit_static_credit(space, session_id, "credit_product_information", offer, eligibility)
        self._append_history(state, message, text)
        yield {"type": "avatar", "state": "speaking"}
        for chunk in _chunks(text):
            yield {"type": "token", "text": chunk}
        yield {"type": "card", "card": {"card_type": "credit_product_detail", "product": payload}}
        yield {"type": "done", "audit_ref": ref}

    @staticmethod
    def _consent_snapshot(space: Space, session_id: str) -> dict:
        """Read the AA-consent state `app.api.aa` maintains on this session
        (see its module docstring) and shape it into `LeadPacket.consent`.
        Absent any consent activity, this reproduces build_lead_packet's own
        default of `{"aa_consent_id": None, "advice_consent": False}`.
        """
        consent = space.sessions.get(session_id, {}).get("aa_consent")
        if not consent:
            return {"aa_consent_id": None, "advice_consent": False}
        return {
            "aa_consent_id": consent.get("consent_id") if consent.get("transfer_granted") else None,
            "advice_consent": bool(consent.get("processing_granted")),
        }

    # -- cards -------------------------------------------------------------

    def _cards(self, ctx, mode, metrics, segment, band, surplus, *, product_ctx: Product | None = None) -> list[dict]:
        if mode == "rm_lead" and ctx.built_lead is not None:
            return [self._rm_lead_card(ctx.built_lead)]
        if mode == "distress_suppress":
            return [{
                "card_type": "distress_support",
                "message": "Money stress is hard, and you're not alone. Let's look at your cash-flow together and "
                           "find breathing room — there's no product to buy here.",
                "options": ["Review my spending", "Understand my EMIs", "Talk to support"],
            }]
        if mode == "auto_execute":
            cards: list[dict] = []
            # `product_ctx` is the SAME deterministic product routing already
            # decided this turn on (see `_representative_product`) — reusing it
            # here, rather than independently re-deriving "the" vanilla product
            # from the customer's own segment/band, is what keeps the
            # recommendation card honest for an explicit ask like "open an FD":
            # ravi's own moderate band has no deposit product at all, so a
            # fresh re-derivation would silently surface an Index Fund SIP
            # instead of the FD routing actually auto-executed.
            rec = self._product_card(product_ctx) if product_ctx is not None else self._recommendation_card(metrics, segment, band, surplus)
            if rec:
                cards.append(rec)
            if ctx.confirm:
                cards.append(ctx.confirm)
            return cards
        # info_only
        if "get_spend_summary" in ctx.called:
            return [self._spend_card(metrics)]
        if "get_eligible_products" in ctx.called:
            rec = self._recommendation_card(metrics, segment, band, surplus)
            return [rec] if rec else []
        return []

    @staticmethod
    def _rm_lead_card(lead: LeadPacket) -> dict:
        return {
            "card_type": "routed_to_rm",
            "lead_id": lead.lead_id,
            "family": lead.family,
            "tag": lead.tag,
            "priority_score": lead.priority_score,
            "next_best_action": lead.next_best_action,
            "recommendations": lead.suitability.get("offer_recommendations", []),
            "what_happens_next": "A qualified IDBI Relationship Manager has been briefed and will reach out. "
                                 "Your details were shared securely, only with your consent.",
        }

    def _recommendation_card(self, metrics, segment, band, surplus) -> dict | None:
        try:
            shelf = eligible_shelf(
                segment, band, monthly_surplus=surplus, is_affluent_or_hni=segment in _AFFLUENT_SEGMENTS
            )
        except ValueError:
            return None
        product = next((p for p in shelf if p.tag == "vanilla"), shelf[0] if shelf else None)
        if product is None:
            return None
        return self._product_card(product)

    @staticmethod
    def _product_card(product: Product) -> dict:
        return {
            "card_type": "recommendation",
            "product": {
                "id": product.id,
                "name": product.name,
                "tag": product.tag,
                "category": product.category,
                "min_amount": product.min_amount,
                "expected_return": product.expected_return,
            },
            "why": [
                "Matched to your profile and risk comfort.",
                "Only products you qualify for are ever shown here.",
            ],
        }

    def _spend_card(self, metrics) -> dict:
        return spend_card(metrics)

    # -- audit helpers -----------------------------------------------------

    def _audit_static_credit(self, space, session_id, name, offer, eligibility) -> str:
        entry_id = f"aud_{uuid.uuid4().hex[:12]}"
        audit.record(
            space,
            AuditEntry(
                id=entry_id,
                session_id=session_id,
                ts=self.now(),
                kind="routing",
                name=name,
                inputs={"offer_id": offer.id if offer is not None else None},
                outputs_summary={"eligibility": eligibility},
                refs=[offer.source_url] if offer is not None else ["credit_catalogue:v1"],
            ),
        )
        return entry_id

    def _audit_routing(self, space, session_id, intent, flags, route) -> None:
        audit.record(
            space,
            AuditEntry(
                id=f"aud_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                ts=self.now(),
                kind="routing",
                name=intent,
                inputs={"intent": intent, "behaviour_flags": flags},
                outputs_summary={"path": route.path, "lead_family": route.lead_family, "reasons": route.reasons},
                refs=[],
            ),
        )

    def _audit_llm(self, space, session_id, resp: LLMResponse, task_class) -> None:
        audit.record(
            space,
            AuditEntry(
                id=f"aud_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                ts=self.now(),
                kind="llm_call",
                name=f"{task_class}:{resp.model_used}",
                inputs={"task_class": task_class},
                outputs_summary={
                    "input_tokens": resp.input_tokens,
                    "output_tokens": resp.output_tokens,
                    "latency_ms": resp.latency_ms,
                    "cost_estimate_usd": resp.cost_estimate_usd,
                    "tool_calls": len(resp.tool_calls),
                },
                refs=[],
            ),
        )

    def _audit_guardrail(self, space, session_id, name, verdict, *, regenerated, fell_back, note=None) -> str:
        entry_id = f"aud_{uuid.uuid4().hex[:12]}"
        summary = verdict.summary()
        summary.update({"regenerated": regenerated, "fell_back": fell_back})
        if note:
            summary["note"] = note
        audit.record(
            space,
            AuditEntry(
                id=entry_id,
                session_id=session_id,
                ts=self.now(),
                kind="guardrail",
                name=name,
                inputs={},
                outputs_summary=summary,
                refs=[],
            ),
        )
        return entry_id

    def _append_history(self, state, user_message, reply) -> None:
        history = state.setdefault("history", [])
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        del history[:-HISTORY_LIMIT]
