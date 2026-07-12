"""anthropic provider — native Messages API tool-use + true streaming.

Maps the C.5 shapes to/from the Anthropic Messages API. The SDK client is
injected, so the full mapping is exercised against a fake transport with no
key and no network.
"""

import time
from collections.abc import Iterator
from typing import Any

from app.gateway.contract import (
    LLMRequest,
    LLMResponse,
    StreamEvent,
    ToolCall,
    classify,
)
from app.gateway.providers.base import Pricing, cost_usd

_TOOL_CHOICE = {"auto": {"type": "auto"}, "any": {"type": "any"}, "none": {"type": "none"}}


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, client: Any, pricing: Pricing):
        self._client = client
        self._pricing = pricing

    # -- request mapping ---------------------------------------------------

    def _params(self, req: LLMRequest, model: str) -> dict:
        system = "\n\n".join(m.content for m in req.messages if m.role == "system" and m.content)
        messages: list[dict] = []
        for m in req.messages:
            if m.role == "system":
                continue
            if m.role == "tool":
                messages.append(
                    {"role": "user", "content": [{"type": "tool_result", "tool_use_id": m.tool_call_id or "", "content": m.content or ""}]}
                )
            elif m.role == "assistant" and m.tool_calls:
                blocks: list[dict] = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for c in m.tool_calls:
                    blocks.append({"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments})
                messages.append({"role": "assistant", "content": blocks})
            else:
                messages.append({"role": m.role, "content": m.content or ""})

        params: dict[str, Any] = {
            "model": model,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "messages": messages,
        }
        if system:
            params["system"] = system
        if req.tools:
            params["tools"] = [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in req.tools]
            params["tool_choice"] = _TOOL_CHOICE[req.tool_choice]
        return params

    # -- response mapping --------------------------------------------------

    def _response(self, msg: Any, model: str, latency_ms: int) -> LLMResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in getattr(msg, "content", None) or []:
            btype = getattr(block, "type", None)
            if btype == "text":
                text_parts.append(getattr(block, "text", "") or "")
            elif btype == "tool_use":
                tool_calls.append(
                    ToolCall(id=getattr(block, "id", ""), name=getattr(block, "name", ""), arguments=getattr(block, "input", {}) or {})
                )
        usage = getattr(msg, "usage", None)
        in_tok = int(getattr(usage, "input_tokens", 0) or 0)
        out_tok = int(getattr(usage, "output_tokens", 0) or 0)
        return LLMResponse(
            text="".join(text_parts) or None,
            tool_calls=tool_calls,
            model_used=getattr(msg, "model", None) or model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=latency_ms,
            cost_estimate_usd=cost_usd(self._pricing, model, in_tok, out_tok),
        )

    # -- contract ----------------------------------------------------------

    def complete(self, req: LLMRequest, model: str) -> LLMResponse:
        t0 = time.perf_counter()
        try:
            msg = self._client.messages.create(**self._params(req, model))
        except Exception as e:  # noqa: BLE001 — translated below, re-raised if unrecognised
            ge = classify(self.name, e)
            if ge:
                raise ge from e
            raise
        return self._response(msg, model, int((time.perf_counter() - t0) * 1000))

    def stream(self, req: LLMRequest, model: str) -> Iterator[StreamEvent]:
        t0 = time.perf_counter()
        params = self._params(req, model)
        try:
            with self._client.messages.stream(**params) as s:
                for text in s.text_stream:
                    if text:
                        yield StreamEvent(type="delta", delta=text)
                final_msg = s.get_final_message()
        except Exception as e:  # noqa: BLE001
            ge = classify(self.name, e)
            if ge:
                raise ge from e
            raise
        resp = self._response(final_msg, model, int((time.perf_counter() - t0) * 1000))
        yield StreamEvent(type="final", response=resp)
