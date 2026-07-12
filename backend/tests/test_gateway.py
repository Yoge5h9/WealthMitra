"""Contract suite for the Model Gateway.

One parametrized suite exercises all three providers through the Gateway via
fake transports — claude_cli faked at the subprocess boundary, gemini and
anthropic faked at the injected SDK client. No test needs a key or network.
"""

import json
from types import SimpleNamespace

import pytest

from app.gateway import (
    AuthError,
    Gateway,
    LLMRequest,
    MalformedResponseError,
    Message,
    ToolSpec,
)
from app.gateway.providers.anthropic import AnthropicProvider
from app.gateway.providers.claude_cli import ClaudeCLIProvider
from app.gateway.providers.gemini import GeminiProvider

# --- routing / pricing tables (mirror config/models.yaml) -----------------

CLI_ROUTING = {"intent_assist": "haiku", "nudge_copy": "haiku", "conversational": "sonnet",
               "lead_narrative": "sonnet", "literacy": "sonnet"}
CLI_PRICING = {"haiku": {"input_per_mtok": 0.0, "output_per_mtok": 0.0},
               "sonnet": {"input_per_mtok": 0.0, "output_per_mtok": 0.0}}

GEM_ROUTING = {"intent_assist": "gemini-2.5-flash", "nudge_copy": "gemini-2.5-flash",
               "conversational": "gemini-2.5-pro", "lead_narrative": "gemini-2.5-pro",
               "literacy": "gemini-2.5-pro"}
GEM_PRICING = {"gemini-2.5-flash": {"input_per_mtok": 0.30, "output_per_mtok": 2.50},
               "gemini-2.5-pro": {"input_per_mtok": 1.25, "output_per_mtok": 10.00}}

ANTH_ROUTING = {"intent_assist": "claude-haiku-4-5", "nudge_copy": "claude-haiku-4-5",
                "conversational": "claude-sonnet-5", "lead_narrative": "claude-sonnet-5",
                "literacy": "claude-sonnet-5"}
ANTH_PRICING = {"claude-haiku-4-5": {"input_per_mtok": 1.00, "output_per_mtok": 5.00},
                "claude-sonnet-5": {"input_per_mtok": 3.00, "output_per_mtok": 15.00}}

_TOOL = ("get_quote", {"symbol": "IDBI"})


class FakeErr(Exception):
    def __init__(self, status_code=None):
        self.status_code = status_code
        self.code = status_code
        super().__init__(f"fake status={status_code}")


# --- claude_cli fake (subprocess boundary) --------------------------------

def _cli_ok_stdout(reply, tool_calls):
    return json.dumps(
        {
            "result": json.dumps({"reply": reply, "tool_calls": tool_calls}),
            "usage": {"input_tokens": 12, "output_tokens": 7},
            "modelUsage": {"claude-haiku-4-5-20251001": {}},
        }
    )


_CLI_BAD = json.dumps({"result": "sorry, not json here {oops", "usage": {"input_tokens": 3, "output_tokens": 2}})


class FakeCliRunner:
    def __init__(self, scenario):
        self.scenario = scenario
        self.calls = 0

    def __call__(self, argv, timeout):
        self.calls += 1
        s = self.scenario
        if s == "auth":
            return SimpleNamespace(returncode=1, stdout="", stderr="Invalid API key — not logged in")
        if s == "tool":
            return SimpleNamespace(returncode=0, stdout=_cli_ok_stdout(None, [dict(name=_TOOL[0], arguments=_TOOL[1])]), stderr="")
        if s == "malformed_always":
            return SimpleNamespace(returncode=0, stdout=_CLI_BAD, stderr="")
        if s == "malformed_then_ok":
            if self.calls == 1:
                return SimpleNamespace(returncode=0, stdout=_CLI_BAD, stderr="")
            return SimpleNamespace(returncode=0, stdout=_cli_ok_stdout("Recovered.", []), stderr="")
        return SimpleNamespace(returncode=0, stdout=_cli_ok_stdout("Hello there. How are you?", []), stderr="")


# --- gemini fake (SDK client) ---------------------------------------------

def _gem_resp(text=None, tool=None):
    parts = []
    if text is not None:
        parts.append(SimpleNamespace(text=text, function_call=None))
    if tool is not None:
        parts.append(SimpleNamespace(text=None, function_call=SimpleNamespace(name=tool[0], args=tool[1])))
    cand = SimpleNamespace(content=SimpleNamespace(parts=parts))
    return SimpleNamespace(
        candidates=[cand],
        usage_metadata=SimpleNamespace(prompt_token_count=11, candidates_token_count=6),
        model_version="gemini-2.5-pro-002",
    )


class FakeGemModels:
    def __init__(self, scenario):
        self.scenario = scenario
        self.calls = 0

    def generate_content(self, model, contents, config):
        self.calls += 1
        s = self.scenario
        if s == "auth":
            raise FakeErr(403)
        if s == "ratelimit_then_ok":
            if self.calls == 1:
                raise FakeErr(429)
            return _gem_resp(text="Recovered.")
        if s == "tool":
            return _gem_resp(tool=_TOOL)
        return _gem_resp(text="Hello there. How are you?")

    def generate_content_stream(self, model, contents, config):
        s = self.scenario
        if s == "tool":
            yield SimpleNamespace(
                text=None,
                candidates=[SimpleNamespace(content=SimpleNamespace(parts=[SimpleNamespace(text=None, function_call=SimpleNamespace(name=_TOOL[0], args=_TOOL[1]))]))],
                usage_metadata=None,
                model_version="gemini-2.5-pro-002",
            )
        else:
            for piece in ["Hello there. ", "How are you?"]:
                yield SimpleNamespace(text=piece, candidates=[], usage_metadata=None, model_version="gemini-2.5-pro-002")
        yield SimpleNamespace(text=None, candidates=[], usage_metadata=SimpleNamespace(prompt_token_count=11, candidates_token_count=6), model_version="gemini-2.5-pro-002")


# --- anthropic fake (SDK client) ------------------------------------------

def _anth_msg(text=None, tool=None, model="claude-sonnet-5"):
    content = []
    if text is not None:
        content.append(SimpleNamespace(type="text", text=text))
    if tool is not None:
        content.append(SimpleNamespace(type="tool_use", id="toolu_1", name=tool[0], input=tool[1]))
    return SimpleNamespace(content=content, usage=SimpleNamespace(input_tokens=10, output_tokens=5), model=model)


class _FakeAnthStream:
    def __init__(self, scenario):
        self.scenario = scenario

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    @property
    def text_stream(self):
        if self.scenario == "tool":
            return iter([])
        return iter(["Hello there. ", "How are you?"])

    def get_final_message(self):
        if self.scenario == "tool":
            return _anth_msg(tool=_TOOL)
        return _anth_msg(text="Hello there. How are you?")


class FakeAnthMessages:
    def __init__(self, scenario):
        self.scenario = scenario
        self.calls = 0

    def create(self, **kw):
        self.calls += 1
        s = self.scenario
        if s == "auth":
            raise FakeErr(401)
        if s == "ratelimit_then_ok":
            if self.calls == 1:
                raise FakeErr(429)
            return _anth_msg(text="Recovered.")
        if s == "tool":
            return _anth_msg(tool=_TOOL)
        return _anth_msg(text="Hello there. How are you?")

    def stream(self, **kw):
        return _FakeAnthStream(self.scenario)


# --- gateway builders per provider ----------------------------------------

def build_cli(scenario, on_response=None):
    prov = ClaudeCLIProvider(pricing=CLI_PRICING, binary="claude", runner=FakeCliRunner(scenario))
    return Gateway(provider=prov, provider_name="claude_cli", routing=CLI_ROUTING, on_response=on_response, retry_base_delay=0)


def build_gemini(scenario, on_response=None):
    client = SimpleNamespace(models=FakeGemModels(scenario))
    prov = GeminiProvider(client=client, pricing=GEM_PRICING)
    return Gateway(provider=prov, provider_name="gemini", routing=GEM_ROUTING, on_response=on_response, retry_base_delay=0)


def build_anthropic(scenario, on_response=None):
    client = SimpleNamespace(messages=FakeAnthMessages(scenario))
    prov = AnthropicProvider(client=client, pricing=ANTH_PRICING)
    return Gateway(provider=prov, provider_name="anthropic", routing=ANTH_ROUTING, on_response=on_response, retry_base_delay=0)


PROVIDERS = [("claude_cli", build_cli), ("gemini", build_gemini), ("anthropic", build_anthropic)]


def _text_req():
    return LLMRequest(messages=[Message(role="system", content="You are a coach."), Message(role="user", content="hi")], task_class="conversational")


def _tool_req():
    return LLMRequest(
        messages=[Message(role="user", content="quote IDBI please")],
        tools=[ToolSpec(name="get_quote", description="Get a stock quote by symbol.", input_schema={"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]})],
        tool_choice="any",
        task_class="intent_assist",
    )


_AUDIT_KEYS = {"model_used", "provider", "task_class", "tokens", "latency_ms", "cost_estimate_usd"}


# --- contract suite (all providers) ---------------------------------------

@pytest.mark.parametrize(("pid", "build"), PROVIDERS)
def test_text_completion(pid, build):
    audit = []
    gw = build("text", on_response=audit.append)
    resp = gw.complete(_text_req())
    assert resp.text and "Hello" in resp.text
    assert resp.tool_calls == []
    assert isinstance(resp.model_used, str) and resp.model_used
    assert isinstance(resp.input_tokens, int) and resp.input_tokens >= 0
    assert isinstance(resp.output_tokens, int) and resp.output_tokens >= 0
    assert isinstance(resp.latency_ms, int) and resp.latency_ms >= 0
    assert isinstance(resp.cost_estimate_usd, float) and resp.cost_estimate_usd >= 0.0
    # audit fired once with the exact documented shape
    assert len(audit) == 1
    entry = audit[0]
    assert set(entry) == _AUDIT_KEYS
    assert entry["provider"] == pid
    assert entry["task_class"] == "conversational"
    assert set(entry["tokens"]) == {"input", "output"}
    assert entry["model_used"] == resp.model_used
    assert entry["cost_estimate_usd"] == resp.cost_estimate_usd


@pytest.mark.parametrize(("pid", "build"), PROVIDERS)
def test_forced_tool_call(pid, build):
    gw = build("tool")
    resp = gw.complete(_tool_req())
    assert len(resp.tool_calls) >= 1
    tc = resp.tool_calls[0]
    assert tc.name == "get_quote"
    assert isinstance(tc.arguments, dict)
    assert tc.arguments.get("symbol") == "IDBI"
    assert isinstance(tc.id, str) and tc.id


@pytest.mark.parametrize(("pid", "build"), PROVIDERS)
def test_streaming_delta_ordering_and_final(pid, build):
    audit = []
    gw = build("text", on_response=audit.append)
    events = list(gw.stream(_text_req()))
    assert events[-1].type == "final"
    deltas = [e for e in events if e.type == "delta"]
    finals = [e for e in events if e.type == "final"]
    assert len(finals) == 1
    assert deltas and all(isinstance(e.delta, str) and e.delta for e in deltas)
    final = finals[0].response
    assert final is not None
    assert final.tool_calls == []
    assert "".join(e.delta for e in deltas) == final.text
    assert final.model_used
    # audit fires exactly once, on the final event
    assert len(audit) == 1
    assert audit[0]["model_used"] == final.model_used


@pytest.mark.parametrize(("pid", "build"), PROVIDERS)
def test_auth_error_raised_not_retried(pid, build):
    gw = build("auth")
    with pytest.raises(AuthError) as ei:
        gw.complete(_text_req())
    assert ei.value.provider == pid
    assert ei.value.retryable is False


# --- provider-specific paths ----------------------------------------------

def test_cli_malformed_json_one_retry_recovers():
    runner = FakeCliRunner("malformed_then_ok")
    prov = ClaudeCLIProvider(pricing=CLI_PRICING, binary="claude", runner=runner)
    gw = Gateway(provider=prov, provider_name="claude_cli", routing=CLI_ROUTING, retry_base_delay=0)
    resp = gw.complete(_text_req())
    assert resp.text == "Recovered."
    assert runner.calls == 2  # one bad + one corrective retry


def test_cli_malformed_json_exhausted_raises():
    runner = FakeCliRunner("malformed_always")
    prov = ClaudeCLIProvider(pricing=CLI_PRICING, binary="claude", runner=runner)
    gw = Gateway(provider=prov, provider_name="claude_cli", routing=CLI_ROUTING, retry_base_delay=0)
    with pytest.raises(MalformedResponseError):
        gw.complete(_text_req())
    assert runner.calls == 2  # original + single corrective retry, then give up


def test_cli_tool_choice_any_without_call_triggers_retry():
    # A model that replies with plain text (no tool call) under tool_choice=any
    # must be treated as malformed and corrected once.
    class OnlyText(FakeCliRunner):
        def __call__(self, argv, timeout):
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(returncode=0, stdout=_cli_ok_stdout("no tool", []), stderr="")
            return SimpleNamespace(returncode=0, stdout=_cli_ok_stdout(None, [dict(name=_TOOL[0], arguments=_TOOL[1])]), stderr="")

    runner = OnlyText("x")
    prov = ClaudeCLIProvider(pricing=CLI_PRICING, binary="claude", runner=runner)
    gw = Gateway(provider=prov, provider_name="claude_cli", routing=CLI_ROUTING, retry_base_delay=0)
    resp = gw.complete(_tool_req())
    assert runner.calls == 2
    assert len(resp.tool_calls) == 1


@pytest.mark.parametrize(("build", "reader"), [
    (build_gemini, lambda gw: gw._provider._client.models.calls),
    (build_anthropic, lambda gw: gw._provider._client.messages.calls),
])
def test_rate_limit_retried_then_succeeds(build, reader):
    gw = build("ratelimit_then_ok")
    resp = gw.complete(_text_req())
    assert resp.text == "Recovered."
    assert reader(gw) == 2  # first 429, retry succeeds


# --- config + default construction ----------------------------------------

def test_models_yaml_covers_all_task_classes_and_prices():
    import yaml

    from app.gateway.gateway import _DEFAULT_CONFIG

    cfg = yaml.safe_load(_DEFAULT_CONFIG.read_text())
    assert cfg["active_provider"] == "claude_cli"
    task_classes = {"intent_assist", "conversational", "nudge_copy", "lead_narrative", "literacy"}
    for name in ("claude_cli", "gemini", "anthropic"):
        pcfg = cfg["providers"][name]
        assert set(pcfg["routing"]) == task_classes
        for model in set(pcfg["routing"].values()):
            assert model in pcfg["pricing"], f"{name}:{model} missing price row"


def test_default_gateway_builds_claude_cli_from_yaml():
    gw = Gateway()
    assert gw.provider_name == "claude_cli"
    assert gw.model_for("conversational") == "haiku"
    assert gw.model_for("intent_assist") == "haiku"


def test_unknown_task_class_routing_error():
    from app.gateway import GatewayError

    prov = ClaudeCLIProvider(pricing=CLI_PRICING, binary="claude", runner=FakeCliRunner("text"))
    gw = Gateway(provider=prov, provider_name="claude_cli", routing={"conversational": "sonnet"}, retry_base_delay=0)
    with pytest.raises(GatewayError):
        gw.complete(LLMRequest(messages=[Message(role="user", content="x")], task_class="literacy"))


# --- stream reassembly invariant: "".join(deltas) == final.text ------------

_REASSEMBLY_TEXTS = [
    "Point one.\n\nPoint two.",                       # paragraph break must survive
    "नमस्ते। आप कैसे हैं?\nधन्यवाद।",                    # Hindi danda + newline
    "Trailing newline stays.\n",                      # trailing whitespace kept
    "No terminal punctuation at all",                 # no-delimiter fallback
]


def _build_echo(pid: str, text: str) -> Gateway:
    """A gateway whose fake provider streams exactly `text`."""
    if pid == "claude_cli":
        def runner(argv, timeout):
            return SimpleNamespace(returncode=0, stdout=_cli_ok_stdout(text, []), stderr="")

        prov = ClaudeCLIProvider(pricing=CLI_PRICING, binary="claude", runner=runner)
        return Gateway(provider=prov, provider_name="claude_cli", routing=CLI_ROUTING, retry_base_delay=0)

    mid = max(1, len(text) // 2)
    pieces = [p for p in (text[:mid], text[mid:]) if p]

    if pid == "gemini":
        class EchoModels:
            def generate_content_stream(self, model, contents, config):
                for piece in pieces:
                    yield SimpleNamespace(text=piece, candidates=[], usage_metadata=None, model_version=None)
                yield SimpleNamespace(
                    text=None, candidates=[], model_version=None,
                    usage_metadata=SimpleNamespace(prompt_token_count=1, candidates_token_count=1),
                )

        prov = GeminiProvider(client=SimpleNamespace(models=EchoModels()), pricing=GEM_PRICING)
        return Gateway(provider=prov, provider_name="gemini", routing=GEM_ROUTING, retry_base_delay=0)

    class EchoStream:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        @property
        def text_stream(self):
            return iter(pieces)

        def get_final_message(self):
            return _anth_msg(text=text)

    class EchoMessages:
        def stream(self, **kw):
            return EchoStream()

    prov = AnthropicProvider(client=SimpleNamespace(messages=EchoMessages()), pricing=ANTH_PRICING)
    return Gateway(provider=prov, provider_name="anthropic", routing=ANTH_ROUTING, retry_base_delay=0)


@pytest.mark.parametrize("text", _REASSEMBLY_TEXTS)
@pytest.mark.parametrize("pid", ["claude_cli", "gemini", "anthropic"])
def test_stream_deltas_concatenate_exactly_to_final_text(pid, text):
    gw = _build_echo(pid, text)
    events = list(gw.stream(_text_req()))
    deltas = [e.delta for e in events if e.type == "delta"]
    final = events[-1].response
    assert final is not None
    assert deltas and all(d for d in deltas)  # no empty/None deltas
    assert "".join(deltas) == final.text == text
