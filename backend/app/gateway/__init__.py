"""Provider-agnostic Model Gateway.

The single seam every WealthMitra service crosses to reach an LLM. Swap the
provider block in config/models.yaml and nothing downstream changes.
"""

from app.gateway.contract import (
    AuthError,
    GatewayError,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    MalformedResponseError,
    Message,
    ProviderTimeoutError,
    RateLimitError,
    StreamEvent,
    TaskClass,
    ToolCall,
    ToolSpec,
)
from app.gateway.gateway import Gateway

__all__ = [
    "AuthError",
    "Gateway",
    "GatewayError",
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "MalformedResponseError",
    "Message",
    "ProviderTimeoutError",
    "RateLimitError",
    "StreamEvent",
    "TaskClass",
    "ToolCall",
    "ToolSpec",
]
