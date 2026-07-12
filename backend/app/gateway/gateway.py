"""Gateway — routing, retry, and audit around a single LLMProvider.

The gateway owns three responsibilities the providers must not:
  * routing: task_class -> model, from config/models.yaml;
  * retry: 429 / timeout retried twice with exponential backoff, everything
    else (auth, validation, malformed) raised immediately;
  * audit: every complete() and every stream-final invokes an optional
    on_response callback with {model_used, provider, task_class, tokens,
    latency_ms, cost_estimate_usd}.
"""

import time
from collections.abc import Callable, Iterator
from pathlib import Path

import yaml

from app.gateway.contract import (
    GatewayError,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    RateLimitError,
    ProviderTimeoutError,
    StreamEvent,
    TaskClass,
)

_DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "models.yaml"


def _load_config(path: Path | None) -> dict:
    with open(path or _DEFAULT_CONFIG) as f:
        return yaml.safe_load(f)


class Gateway:
    """app.gateway.gateway.Gateway — the seam every service crosses for an LLM."""

    def __init__(
        self,
        *,
        config_path: str | Path | None = None,
        provider: LLMProvider | None = None,
        provider_name: str | None = None,
        routing: dict[str, str] | None = None,
        on_response: Callable[[dict], None] | None = None,
        retry_base_delay: float = 0.5,
        max_retries: int = 2,
    ):
        self._on_response = on_response
        self._retry_base_delay = retry_base_delay
        self._max_retries = max_retries

        if provider is not None:
            self._provider = provider
            self._provider_name = provider_name or provider.name
            self._routing = routing or self._routing_from_config(self._provider_name, config_path)
        else:
            cfg = _load_config(Path(config_path) if config_path else None)
            name = self._active_provider_name(cfg)
            pcfg = cfg["providers"][name]
            self._provider_name = name
            self._routing = pcfg["routing"]
            self._provider = self._build_provider(name, pcfg)

    # -- construction helpers ---------------------------------------------

    @staticmethod
    def _active_provider_name(cfg: dict) -> str:
        try:
            from app.core.config import settings

            override = getattr(settings, "llm_provider", None)
        except Exception:  # noqa: BLE001 — config optional at import time
            override = None
        return override or cfg["active_provider"]

    @staticmethod
    def _routing_from_config(name: str, config_path: str | Path | None) -> dict[str, str]:
        cfg = _load_config(Path(config_path) if config_path else None)
        return cfg["providers"][name]["routing"]

    @staticmethod
    def _build_provider(name: str, pcfg: dict) -> LLMProvider:
        pricing = pcfg.get("pricing", {})
        if name == "claude_cli":
            from app.gateway.providers.claude_cli import ClaudeCLIProvider

            return ClaudeCLIProvider(pricing=pricing)
        if name == "gemini":
            from google import genai

            from app.core.config import settings
            from app.gateway.providers.gemini import GeminiProvider

            return GeminiProvider(client=genai.Client(api_key=settings.gemini_api_key), pricing=pricing)
        if name == "anthropic":
            import anthropic

            from app.core.config import settings
            from app.gateway.providers.anthropic import AnthropicProvider

            return AnthropicProvider(client=anthropic.Anthropic(api_key=settings.anthropic_api_key), pricing=pricing)
        raise GatewayError(name, f"unknown provider '{name}' — check config/models.yaml active_provider", None)

    # -- routing -----------------------------------------------------------

    def _route(self, task_class: TaskClass) -> str:
        try:
            return self._routing[task_class]
        except KeyError as e:
            raise GatewayError(
                self._provider_name, f"no model mapped for task_class '{task_class}' in routing table", e
            ) from e

    # -- audit -------------------------------------------------------------

    def _emit(self, resp: LLMResponse, req: LLMRequest) -> None:
        if self._on_response is None:
            return
        self._on_response(
            {
                "model_used": resp.model_used,
                "provider": self._provider_name,
                "task_class": req.task_class,
                "tokens": {"input": resp.input_tokens, "output": resp.output_tokens},
                "latency_ms": resp.latency_ms,
                "cost_estimate_usd": resp.cost_estimate_usd,
            }
        )

    # -- contract ----------------------------------------------------------

    def complete(self, req: LLMRequest) -> LLMResponse:
        model = self._route(req.task_class)
        attempt = 0
        while True:
            try:
                resp = self._provider.complete(req, model)
                break
            except (RateLimitError, ProviderTimeoutError):
                if attempt >= self._max_retries:
                    raise
                time.sleep(self._retry_base_delay * (2**attempt))
                attempt += 1
        self._emit(resp, req)
        return resp

    def stream(self, req: LLMRequest) -> Iterator[StreamEvent]:
        model = self._route(req.task_class)

        def _gen() -> Iterator[StreamEvent]:
            attempt = 0
            while True:
                started = False
                try:
                    for ev in self._provider.stream(req, model):
                        started = True
                        if ev.type == "final" and ev.response is not None:
                            self._emit(ev.response, req)
                        yield ev
                    return
                except (RateLimitError, ProviderTimeoutError):
                    if started or attempt >= self._max_retries:
                        raise
                    time.sleep(self._retry_base_delay * (2**attempt))
                    attempt += 1

        return _gen()

    # -- introspection (handy for tests / diagnostics) ---------------------

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def model_for(self, task_class: TaskClass) -> str:
        return self._route(task_class)
