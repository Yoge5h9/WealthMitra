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
from app.catalogue import eligible_shelf, evaluate_eligibility, offer_payload, recommendations_for, resolve_offer
from app.core import audit, events
from app.core.spaces import Space
from app.domain.models import AuditEntry, LeadPacket, Metric, PersonaProfile, Product
from app.gateway.contract import LLMRequest, LLMResponse, Message, TaskClass
from app.routing import build_lead_packet, classify_intent, decide, is_generic_card_phrase

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
_AFFIRMATIVE = re.compile(r"^\s*(?:yes|yes please|please do|go ahead|sure|haan|ha|हाँ|હા)\s*[.!]*\s*$", re.IGNORECASE)
_NEGATIVE = re.compile(r"^\s*(?:no|not now|no thanks|nah|nahi|नहीं|ना|ના)\s*[.!]*\s*$", re.IGNORECASE)


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

        # Credit-card discovery is a deliberately small state machine. A
        # generic "I want a card" must not manufacture an RM lead from an
        # LLM sentence: first understand the use case, run the catalogued
        # pre-eligibility check, then accept an explicit RM hand-off.
        pending_credit = state.get("pending_credit")
        if pending_credit:
            stage = pending_credit.get("stage")
            if stage == "need":
                if _NEGATIVE.match(message):
                    yield from self._credit_cancelled_turn(space, session_id, state, message)
                else:
                    yield from self._credit_shortlist_turn(space, session_id, state, profile, message, metrics)
                return
            if stage == "rm_confirmation":
                if _AFFIRMATIVE.match(message) or "apply" in message.lower():
                    yield from self._credit_rm_confirmation_turn(
                        space, session_id, state, persona_id, profile, message, metrics, segment, band, surplus
                    )
                elif _NEGATIVE.match(message):
                    yield from self._credit_cancelled_turn(space, session_id, state, message)
                else:
                    yield from self._credit_rm_clarify_turn(space, session_id, state, message)
                return

        intent = classify_intent(message, lang)
        named_offer = resolve_offer(message)
        if named_offer is not None and intent == "credit_product_info":
            yield from self._credit_product_turn(space, session_id, state, profile, message, named_offer, metrics)
            return
        if intent == "loan_card_query" and named_offer is None and is_generic_card_phrase(message):
            yield from self._credit_need_turn(space, session_id, state, message)
            return

        product_ctx = self._representative_product(intent, segment, band, surplus)
        route = decide(intent, flags, product_ctx)
        mode = route.path
        self._audit_routing(space, session_id, intent, flags, route)

        yield {"type": "avatar", "state": "thinking"}

        ctx = ToolContext(space, persona_id, session_id, mode, engine=self.engine, now=self.now)
        ctx._metrics = metrics

        if mode == "rm_lead":
            family = route.lead_family or "investment_insurance"
            offer_recommendations = recommendations_for(
                profile, {key: metric.value for key, metric in metrics.items()}, family=family, message=message
            ) if family == "loans_cards" or "insurance" in message.lower() else []
            if family == "loans_cards" and not offer_recommendations:
                yield from self._credit_not_eligible_turn(space, session_id, state, profile, message, named_offer, metrics)
                return
            ctx.built_lead = self._build_lead(
                space, session_id, persona_id, message, family, metrics, segment, band, surplus, offer_recommendations
            )

        # classify_intent already ran deterministically above the routing gate;
        # a literacy/definition question always lands in info_only (it is
        # neither a buy-intent nor a regulated/distress signal — see
        # routing.engine.decide) so this never touches the compliance modes.
        is_literacy = intent == "literacy" and mode == "info_only"
        task_class = "literacy" if is_literacy else _TASK_CLASS[mode]
        messages = self._build_messages(profile, segment, lang, mode, state, message, literacy=is_literacy)
        toolspecs = tools.literacy_toolspecs() if is_literacy else tools.tools_for_mode(mode)
        final_text = self._tool_loop(space, session_id, ctx, messages, toolspecs, task_class)

        final_text, audit_ref = self._guard(
            space, session_id, ctx, messages, task_class, final_text, metrics, lang
        )

        self._append_history(state, message, final_text)

        yield {"type": "avatar", "state": _AVATAR_END[mode]}
        for chunk in _chunks(final_text):
            yield {"type": "token", "text": chunk}
        for card in self._cards(ctx, mode, metrics, segment, band, surplus):
            yield {"type": "card", "card": card}
        yield {"type": "done", "audit_ref": audit_ref}


    # -- pipeline internals ------------------------------------------------

    def _metrics(self, space: Space, persona_id: str) -> dict[str, Metric]:
        return {m.id: m for m in self.engine.compute(space, persona_id, now=self.now())}

    def _representative_product(self, intent: str, segment: str, band: str, surplus: float) -> Product | None:
        """A stand-in vanilla product so routing can decide auto_execute BEFORE
        the LLM picks anything. None if the customer has no eligible vanilla
        product for this intent (then routing falls through to info_only).
        """
        if intent not in _VANILLA_INTENTS:
            return None
        category = "deposit" if intent == "fd_query" else None
        try:
            shelf = eligible_shelf(
                segment, band, category, monthly_surplus=surplus, is_affluent_or_hni=segment in _AFFLUENT_SEGMENTS
            )
        except ValueError:
            return None
        return next((p for p in shelf if p.tag == "vanilla"), None)

    def _build_messages(self, profile, segment, lang, mode, state, message, *, literacy: bool) -> list[Message]:
        if literacy:
            system_content = prompts.literacy_system_prompt(profile, segment, lang)
            window = LITERACY_HISTORY_WINDOW
        else:
            system_content = prompts.system_prompt(profile, segment, lang, mode)
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

    def _guard(self, space, session_id, ctx, messages, task_class, final_text, metrics, lang) -> tuple[str, str]:
        extra = [m.value for m in metrics.values()]
        amounts, percents = guardrails.build_allowed(ctx.tool_results, extra)
        verdict = guardrails.audit_numbers(final_text, amounts, percents)
        ref = self._audit_guardrail(space, session_id, "number_audit", verdict, regenerated=False, fell_back=False)
        if verdict.ok:
            return final_text, ref

        instruction = guardrails.stricter_instruction(verdict, amounts, percents)
        regen_messages = [*messages, Message(role="system", content=instruction)]
        req = LLMRequest(messages=regen_messages, tools=None, tool_choice="none",
                         task_class=task_class, temperature=0.0, max_tokens=1024)
        resp = self.gateway.complete(req)
        self._audit_llm(space, session_id, resp, task_class)
        regen_text = resp.text or ""
        verdict2 = guardrails.audit_numbers(regen_text, amounts, percents)
        ref = self._audit_guardrail(space, session_id, "number_audit", verdict2, regenerated=True, fell_back=False)
        if verdict2.ok:
            return regen_text, ref

        figures = {
            "monthly_surplus": float(metrics["monthly_surplus"].value),
            "idle_balance": float(metrics["idle_balance"].value),
        }
        safe = guardrails.safe_template(figures, lang)
        ref = self._audit_guardrail(space, session_id, "number_audit", verdict2, regenerated=True, fell_back=True)
        return safe, ref

    # -- lead construction -------------------------------------------------

    def _build_lead(self, space, session_id, persona_id, message, family, metrics, segment, band, surplus, offer_recommendations) -> LeadPacket:
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
            profile, lead_metrics, shelf, message, family, seq=len(space.leads) + 1, now=self.now()
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

    def _credit_not_eligible_turn(self, space, session_id, state, profile, message, offer, metrics):
        if offer is not None:
            eligibility = evaluate_eligibility(profile, {key: metric.value for key, metric in metrics.items()}, offer)
            payload = offer_payload(offer, eligibility)
            text = f"I can explain {offer.name}, but I won't send it to an RM yet. {eligibility['reasons'][0]}"
            card = {"card_type": "credit_product_detail", "product": payload}
        else:
            text = "I need a little more verified profile information before I can shortlist a credit product or involve an RM."
            card = {"card_type": "credit_eligibility_result", "status": "needs_more_data", "message": text}
        ref = self._audit_static_credit(space, session_id, "credit_preeligibility_stopped", offer, card.get("product", {}).get("eligibility", {}))
        self._append_history(state, message, text)
        yield {"type": "avatar", "state": "speaking"}
        for chunk in _chunks(text):
            yield {"type": "token", "text": chunk}
        yield {"type": "card", "card": card}
        yield {"type": "done", "audit_ref": ref}

    def _credit_need_turn(self, space, session_id, state, message):
        state["pending_credit"] = {"stage": "need", "initial_message": message}
        text = (
            "I can shortlist an IDBI credit card for you. What matters most: everyday rewards, travel, "
            "or a large purchase? I’ll use your recorded profile for a preliminary eligibility check before "
            "asking an RM to review anything."
        )
        ref = self._audit_static_credit(space, session_id, "credit_need_discovery", None, {})
        self._append_history(state, message, text)
        yield {"type": "avatar", "state": "speaking"}
        for chunk in _chunks(text):
            yield {"type": "token", "text": chunk}
        yield {"type": "done", "audit_ref": ref}

    def _credit_shortlist_turn(self, space, session_id, state, profile, message, metrics):
        pending = state.get("pending_credit", {})
        initial_message = str(pending.get("initial_message", "credit card"))
        offer_recommendations = recommendations_for(
            profile,
            {key: metric.value for key, metric in metrics.items()},
            family="loans_cards",
            message=f"{initial_message} {message}",
        )
        if not offer_recommendations:
            state.pop("pending_credit", None)
            yield from self._credit_not_eligible_turn(space, session_id, state, profile, message, None, metrics)
            return

        product = offer_recommendations[0]
        state["pending_credit"] = {
            "stage": "rm_confirmation",
            "initial_message": initial_message,
            "need": message,
            "recommendations": offer_recommendations,
        }
        text = (
            f"Based on your recorded profile and your focus on {message}, {product['name']} is a preliminary match. "
            f"{product['eligibility']['reasons'][0]} This is not an approval. Would you like me to send this "
            "shortlist to an IDBI RM for a document and final eligibility review?"
        )
        ref = self._audit_static_credit(space, session_id, "credit_preeligibility_shortlist", None, product["eligibility"])
        self._append_history(state, message, text)
        yield {"type": "avatar", "state": "speaking"}
        for chunk in _chunks(text):
            yield {"type": "token", "text": chunk}
        yield {"type": "card", "card": {"card_type": "credit_product_detail", "product": product}}
        yield {"type": "done", "audit_ref": ref}

    def _credit_rm_confirmation_turn(self, space, session_id, state, persona_id, profile, message, metrics, segment, band, surplus):
        pending = state.pop("pending_credit", {})
        offer_recommendations = list(pending.get("recommendations", []))
        trigger = f"{pending.get('initial_message', 'Credit card request')} — need: {pending.get('need', 'not stated')}"
        lead = self._build_lead(
            space, session_id, persona_id, trigger, "loans_cards", metrics, segment, band, surplus, offer_recommendations
        )
        text = (
            "Done — your preliminary shortlist and recorded profile details are now in an RM lead packet. "
            "An IDBI Relationship Manager will review documents, final eligibility, and the card terms with you."
        )
        ref = self._audit_static_credit(space, session_id, "credit_rm_handoff_confirmed", None, {"status": "preeligible"})
        self._append_history(state, message, text)
        yield {"type": "avatar", "state": "speaking"}
        for chunk in _chunks(text):
            yield {"type": "token", "text": chunk}
        yield {"type": "card", "card": self._rm_lead_card(lead)}
        yield {"type": "done", "audit_ref": ref}

    def _credit_rm_clarify_turn(self, space, session_id, state, message):
        text = "I have the preliminary shortlist ready. Reply Yes to ask an IDBI RM to review it, or No to keep exploring on your own."
        ref = self._audit_static_credit(space, session_id, "credit_rm_confirmation_clarified", None, {})
        self._append_history(state, message, text)
        yield {"type": "avatar", "state": "speaking"}
        for chunk in _chunks(text):
            yield {"type": "token", "text": chunk}
        yield {"type": "done", "audit_ref": ref}

    def _credit_cancelled_turn(self, space, session_id, state, message):
        state.pop("pending_credit", None)
        text = "No problem — I have not sent an RM lead. You can ask about a card whenever you are ready."
        ref = self._audit_static_credit(space, session_id, "credit_rm_handoff_declined", None, {})
        self._append_history(state, message, text)
        yield {"type": "avatar", "state": "speaking"}
        for chunk in _chunks(text):
            yield {"type": "token", "text": chunk}
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

    def _cards(self, ctx, mode, metrics, segment, band, surplus) -> list[dict]:
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
            rec = self._recommendation_card(metrics, segment, band, surplus)
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
                f"Matched to the '{segment}' / '{band}' shelf by the suitability matrix.",
                "On your eligible shelf — nothing outside it is ever shown.",
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
