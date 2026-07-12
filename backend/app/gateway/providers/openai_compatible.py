"""openai_compatible provider — OpenAI Chat Completions wire format.

Talks the wire format directly over an injected ``httpx.Client`` — no vendor
SDK — so the same adapter drives OpenAI (default ``base_url``) or any other
OpenAI-wire-compatible endpoint (e.g. Groq) reached through a different
``base_url``, with zero downstream code change. The client is injected, so
tests exercise the full mapping against a fake transport with no key and no
network.
"""

import json
import time
import uuid
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

_TOOL_CHOICE = {"auto": "auto", "any": "required", "none": "none"}


class _HTTPStatusError(Exception):
    """Bridges an httpx-style status code into the shared ``classify()`` taxonomy."""

    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.code = status_code
        super().__init__(f"HTTP {status_code}: {body[:400]}")


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(self, client: Any, pricing: Pricing):
        self._client = client
        self._pricing = pricing

    # -- request mapping ---------------------------------------------------

    @staticmethod
    def _messages(req: LLMRequest) -> list[dict]:
        out: list[dict] = []
        for m in req.messages:
            if m.role == "tool":
                out.append({"role": "tool", "tool_call_id": m.tool_call_id or "", "content": m.content or ""})
            elif m.role == "assistant" and m.tool_calls:
                out.append(
                    {
                        "role": "assistant",
                        "content": m.content,
                        "tool_calls": [
                            {
                                "id": c.id,
                                "type": "function",
                                "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
                            }
                            for c in m.tool_calls
                        ],
                    }
                )
            else:
                out.append({"role": m.role, "content": m.content or ""})
        return out

    @staticmethod
    def _tools(req: LLMRequest) -> list[dict] | None:
        if not req.tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in req.tools
        ]

    def _payload(self, req: LLMRequest, model: str, *, stream: bool) -> dict:
        # gpt-5.x only supports the default temperature (1) — any other value
        # 400s — so temperature is omitted; and it requires max_completion_tokens
        # (max_tokens is rejected as unsupported).
        payload: dict[str, Any] = {
            "model": model,
            "messages": self._messages(req),
            "max_completion_tokens": req.max_tokens,
        }
        tools = self._tools(req)
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = _TOOL_CHOICE[req.tool_choice]
        if stream:
            payload["stream"] = True
            payload["stream_options"] = {"include_usage": True}
        return payload

    # -- response mapping ----------------------------------------------------

    @staticmethod
    def _parse_tool_calls(raw_calls: list[dict] | None) -> list[ToolCall]:
        calls: list[ToolCall] = []
        for c in raw_calls or []:
            fn = c.get("function") or {}
            args_raw = fn.get("arguments") or "{}"
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
            except json.JSONDecodeError:
                args = {}
            calls.append(
                ToolCall(id=c.get("id") or f"call_{uuid.uuid4().hex[:12]}", name=fn.get("name", ""), arguments=args)
            )
        return calls

    def _response(self, data: dict, model: str, latency_ms: int) -> LLMResponse:
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        usage = data.get("usage") or {}
        in_tok = int(usage.get("prompt_tokens", 0) or 0)
        out_tok = int(usage.get("completion_tokens", 0) or 0)
        return LLMResponse(
            text=msg.get("content"),
            tool_calls=self._parse_tool_calls(msg.get("tool_calls")),
            model_used=data.get("model") or model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=latency_ms,
            cost_estimate_usd=cost_usd(self._pricing, model, in_tok, out_tok),
        )

    @staticmethod
    def _raise_for_status(resp: Any, provider: str) -> None:
        """Translate a non-2xx response into the shared GatewayError taxonomy.

        Called outside the network try/except below, so a classified error
        (AuthError, RateLimitError, ...) propagates once — it is never
        re-fed through ``classify()`` a second time.
        """
        if resp.status_code < 400:
            return
        err = _HTTPStatusError(resp.status_code, getattr(resp, "text", ""))
        ge = classify(provider, err)
        raise (ge or err) from err

    # -- contract ----------------------------------------------------------

    def complete(self, req: LLMRequest, model: str) -> LLMResponse:
        t0 = time.perf_counter()
        try:
            resp = self._client.post("/chat/completions", json=self._payload(req, model, stream=False))
        except Exception as e:  # noqa: BLE001 — translated below, re-raised if unrecognised
            ge = classify(self.name, e)
            if ge:
                raise ge from e
            raise
        self._raise_for_status(resp, self.name)
        return self._response(resp.json(), model, int((time.perf_counter() - t0) * 1000))

    def stream(self, req: LLMRequest, model: str) -> Iterator[StreamEvent]:
        t0 = time.perf_counter()
        text_parts: list[str] = []
        tool_call_acc: dict[int, dict] = {}
        in_tok = out_tok = 0
        model_used = model
        try:
            cm = self._client.stream("POST", "/chat/completions", json=self._payload(req, model, stream=True))
            resp = cm.__enter__()
        except Exception as e:  # noqa: BLE001
            ge = classify(self.name, e)
            if ge:
                raise ge from e
            raise
        try:
            self._raise_for_status(resp, self.name)
            for line in resp.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[len("data:") :].strip()
                if data_str == "[DONE]":
                    break
                chunk = json.loads(data_str)
                model_used = chunk.get("model") or model_used
                usage = chunk.get("usage")
                if usage:
                    in_tok = int(usage.get("prompt_tokens", 0) or 0)
                    out_tok = int(usage.get("completion_tokens", 0) or 0)
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                if delta.get("content"):
                    text_parts.append(delta["content"])
                    yield StreamEvent(type="delta", delta=delta["content"])
                for tc in delta.get("tool_calls") or []:
                    idx = tc.get("index", 0)
                    acc = tool_call_acc.setdefault(idx, {"id": None, "name": "", "arguments": ""})
                    if tc.get("id"):
                        acc["id"] = tc["id"]
                    fn = tc.get("function") or {}
                    if fn.get("name"):
                        acc["name"] += fn["name"]
                    if fn.get("arguments"):
                        acc["arguments"] += fn["arguments"]
        finally:
            cm.__exit__(None, None, None)

        tool_calls: list[ToolCall] = []
        for acc in tool_call_acc.values():
            try:
                args = json.loads(acc["arguments"]) if acc["arguments"] else {}
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(id=acc["id"] or f"call_{uuid.uuid4().hex[:12]}", name=acc["name"], arguments=args))

        final = LLMResponse(
            text="".join(text_parts) or None,
            tool_calls=tool_calls,
            model_used=model_used,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            cost_estimate_usd=cost_usd(self._pricing, model, in_tok, out_tok),
        )
        yield StreamEvent(type="final", response=final)
