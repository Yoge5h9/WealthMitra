"""Shared test doubles for the agent tests: a scripted fake Gateway."""

from __future__ import annotations

from collections.abc import Iterator

from app.gateway.contract import LLMRequest, LLMResponse, StreamEvent, ToolCall


def resp(text: str | None = None, tool_calls: list[ToolCall] | None = None) -> LLMResponse:
    return LLMResponse(
        text=text,
        tool_calls=tool_calls or [],
        model_used="fake-model",
        input_tokens=10,
        output_tokens=10,
        latency_ms=1,
        cost_estimate_usd=0.0,
    )


def call(name: str, arguments: dict | None = None, call_id: str = "call_1") -> ToolCall:
    return ToolCall(id=call_id, name=name, arguments=arguments or {})


class FakeGateway:
    """Pops a scripted LLMResponse per complete() call and records every request."""

    provider_name = "fake"

    def __init__(self, script: list[LLMResponse]):
        self.script = list(script)
        self.requests: list[LLMRequest] = []

    def complete(self, req: LLMRequest) -> LLMResponse:
        self.requests.append(req)
        if not self.script:
            return resp(text="I've shared what I can from your data.")
        return self.script.pop(0)

    def stream(self, req: LLMRequest) -> Iterator[StreamEvent]:
        final = self.complete(req)
        if final.text:
            yield StreamEvent(type="delta", delta=final.text)
        yield StreamEvent(type="final", response=final)
