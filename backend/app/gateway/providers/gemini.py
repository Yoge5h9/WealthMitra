"""gemini provider — native google-genai function-calling + true streaming.

Maps the C.5 shapes to/from the google-genai `types.*` request/response
objects. The SDK client is injected, so tests exercise the full mapping
against a fake transport with no key and no network.
"""

import base64
import time
import uuid
from collections.abc import Iterator
from typing import Any

from google.genai import types

from app.gateway.contract import (
    AuthError,
    LLMRequest,
    LLMResponse,
    RateLimitError,
    StreamEvent,
    ToolCall,
    classify,
)
from app.gateway.providers.base import Pricing, cost_usd

_MODE = {
    "auto": types.FunctionCallingConfigMode.AUTO,
    "any": types.FunctionCallingConfigMode.ANY,
    "none": types.FunctionCallingConfigMode.NONE,
}


class GeminiProvider:
    name = "gemini"

    def __init__(self, client: Any, pricing: Pricing, fallback_clients: tuple[Any, ...] = ()):
        self._clients = [client, *fallback_clients]
        self._active = 0
        self._pricing = pricing

    @property
    def _client(self) -> Any:
        return self._clients[self._active]

    def _failover(self, err: Exception) -> bool:
        """Rotate to the next API key on quota/auth exhaustion.

        The switch is sticky: once a key is burned, every later request starts
        from the surviving key. Returns False when no keys remain.
        """
        if not isinstance(err, (RateLimitError, AuthError)) or self._active + 1 >= len(self._clients):
            return False
        self._active += 1
        return True

    # -- request mapping ---------------------------------------------------

    def _config(self, req: LLMRequest) -> types.GenerateContentConfig:
        systems = [m.content for m in req.messages if m.role == "system" and m.content]
        tools = None
        tool_config = None
        if req.tools:
            tools = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(name=t.name, description=t.description, parameters=t.input_schema)
                        for t in req.tools
                    ]
                )
            ]
            tool_config = types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode=_MODE[req.tool_choice])
            )
        return types.GenerateContentConfig(
            system_instruction="\n\n".join(systems) or None,
            tools=tools,
            tool_config=tool_config,
            temperature=req.temperature,
            max_output_tokens=req.max_tokens,
        )

    def _contents(self, req: LLMRequest) -> list[types.Content]:
        contents: list[types.Content] = []
        for m in req.messages:
            if m.role == "system":
                continue
            if m.role == "tool":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_function_response(name=m.tool_call_id or "tool", response={"result": m.content or ""})],
                    )
                )
            elif m.role == "assistant" and m.tool_calls:
                parts = []
                if m.content:
                    parts.append(types.Part.from_text(text=m.content))
                for c in m.tool_calls:
                    parts.append(
                        types.Part(
                            function_call=types.FunctionCall(name=c.name, args=c.arguments),
                            thought_signature=base64.b64decode(c.thought_signature) if c.thought_signature else None,
                        )
                    )
                contents.append(types.Content(role="model", parts=parts))
            else:
                role = "model" if m.role == "assistant" else "user"
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m.content or "")]))
        return contents

    # -- response mapping --------------------------------------------------

    @staticmethod
    def _tool_call(part: Any) -> ToolCall:
        fc = part.function_call
        args = fc.args
        if args is not None and not isinstance(args, dict):
            args = dict(args)
        sig = getattr(part, "thought_signature", None)
        return ToolCall(
            id=f"call_{uuid.uuid4().hex[:12]}",
            name=fc.name,
            arguments=args or {},
            thought_signature=base64.b64encode(sig).decode() if sig else None,
        )

    def _response(self, raw: Any, model: str, latency_ms: int) -> LLMResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for cand in getattr(raw, "candidates", None) or []:
            content = getattr(cand, "content", None)
            for part in (getattr(content, "parts", None) or []):
                if getattr(part, "text", None):
                    text_parts.append(part.text)
                if getattr(part, "function_call", None) is not None:
                    tool_calls.append(self._tool_call(part))
        usage = getattr(raw, "usage_metadata", None)
        in_tok = int(getattr(usage, "prompt_token_count", 0) or 0)
        out_tok = int(getattr(usage, "candidates_token_count", 0) or 0)
        text = "".join(text_parts) or None
        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            model_used=getattr(raw, "model_version", None) or model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=latency_ms,
            cost_estimate_usd=cost_usd(self._pricing, model, in_tok, out_tok),
        )

    # -- contract ----------------------------------------------------------

    def complete(self, req: LLMRequest, model: str) -> LLMResponse:
        t0 = time.perf_counter()
        while True:
            try:
                raw = self._client.models.generate_content(model=model, contents=self._contents(req), config=self._config(req))
                break
            except Exception as e:  # noqa: BLE001 — translated below, re-raised if unrecognised
                ge = classify(self.name, e)
                if ge and self._failover(ge):
                    continue
                if ge:
                    raise ge from e
                raise
        return self._response(raw, model, int((time.perf_counter() - t0) * 1000))

    def stream(self, req: LLMRequest, model: str) -> Iterator[StreamEvent]:
        t0 = time.perf_counter()
        while True:
            text_parts: list[str] = []
            tool_calls: list[ToolCall] = []
            in_tok = out_tok = 0
            model_used = model
            emitted = False
            try:
                chunks = self._client.models.generate_content_stream(
                    model=model, contents=self._contents(req), config=self._config(req)
                )
                for chunk in chunks:
                    delta = getattr(chunk, "text", None)
                    if delta:
                        text_parts.append(delta)
                        emitted = True
                        yield StreamEvent(type="delta", delta=delta)
                    for cand in getattr(chunk, "candidates", None) or []:
                        content = getattr(cand, "content", None)
                        for part in (getattr(content, "parts", None) or []):
                            if getattr(part, "function_call", None) is not None:
                                tool_calls.append(self._tool_call(part))
                    usage = getattr(chunk, "usage_metadata", None)
                    if usage is not None:
                        in_tok = int(getattr(usage, "prompt_token_count", 0) or 0)
                        out_tok = int(getattr(usage, "candidates_token_count", 0) or 0)
                    model_used = getattr(chunk, "model_version", None) or model_used
                break
            except Exception as e:  # noqa: BLE001
                ge = classify(self.name, e)
                if ge and not emitted and self._failover(ge):
                    continue
                if ge:
                    raise ge from e
                raise

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
