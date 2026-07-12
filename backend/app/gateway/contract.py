"""Model Gateway contract — the canonical provider-agnostic LLM interface.

This is the one deliberate abstraction in the system: the seam every other
service crosses to reach an LLM. The shapes below are the contract; no
provider SDK type is ever allowed to leak through them.
"""

from collections.abc import Iterator
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel

TaskClass = Literal["intent_assist", "conversational", "nudge_copy", "lead_narrative", "literacy"]


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict
    # Gemini 3.x signs function-call parts and rejects a follow-up turn whose
    # history omits the signature — round-tripped opaquely, base64-encoded.
    thought_signature: str | None = None


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class LLMRequest(BaseModel):
    messages: list[Message]
    tools: list[ToolSpec] | None = None
    tool_choice: Literal["auto", "any", "none"] = "auto"
    task_class: TaskClass
    max_tokens: int = 1024
    temperature: float = 0.2
    stream: bool = False


class LLMResponse(BaseModel):
    text: str | None
    tool_calls: list[ToolCall]
    model_used: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_estimate_usd: float


class StreamEvent(BaseModel):
    type: Literal["delta", "final"]
    delta: str | None = None
    response: LLMResponse | None = None


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def complete(self, req: LLMRequest, model: str) -> LLMResponse: ...

    def stream(self, req: LLMRequest, model: str) -> Iterator[StreamEvent]: ...


# --- Error taxonomy -------------------------------------------------------
#
# The gateway retries RateLimitError and ProviderTimeoutError (transient);
# every other GatewayError is raised to the caller immediately. Each error
# names the provider and a remedy so an operator can act without a stack trace.


class GatewayError(Exception):
    """Base class for every gateway failure. Not retried by default."""

    retryable: bool = False

    def __init__(self, provider: str, remedy: str, cause: BaseException | None = None):
        self.provider = provider
        self.remedy = remedy
        self.cause = cause
        super().__init__(f"[{provider}] {remedy}" + (f" ({cause})" if cause else ""))


class AuthError(GatewayError):
    """Missing/invalid credential or insufficient permission. Never retried."""


class RateLimitError(GatewayError):
    """Provider throttled the request (HTTP 429). Retried with backoff."""

    retryable = True


class ProviderTimeoutError(GatewayError):
    """Request timed out reaching the provider. Retried with backoff."""

    retryable = True


class MalformedResponseError(GatewayError):
    """Provider returned output the gateway could not parse after one retry."""


def classify(provider: str, exc: BaseException) -> GatewayError | None:
    """Map a transport-layer exception to a GatewayError, or None to re-raise.

    Recognises real provider SDK exceptions and any fake exposing an HTTP
    ``status_code``/``code`` — so tests can drive the error paths with a fake
    transport, and genuine bugs (AttributeError, KeyError, ...) still surface.
    """
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "code", None)
    name = type(exc).__name__.lower()

    if status in (401, 403) or "authentication" in name or "permissiondenied" in name:
        return AuthError(provider, "authentication failed — check the API key and its permissions", exc)
    if status == 429 or "ratelimit" in name:
        return RateLimitError(provider, "rate limited by the provider", exc)
    if status == 408 or "timeout" in name or isinstance(exc, TimeoutError):
        return ProviderTimeoutError(provider, "request timed out reaching the provider", exc)
    if status is not None or name in ("apierror", "clienterror", "servererror"):
        return GatewayError(provider, f"provider returned an error: {exc}", exc)
    return None
