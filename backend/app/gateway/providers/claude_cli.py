"""claude_cli provider — the dev/test workhorse.

Drives the local `claude` binary as a subprocess. The Claude Code CLI has no
native tool-calling wire format, so we impose one: the prompt embeds the
system+message transcript plus the tool JSON-schemas and demands a strict JSON
envelope reply. The envelope is parsed defensively, with one corrective retry
on malformed output before the call is failed.
"""

import json
import re
import shutil
import subprocess
import time
import uuid
from collections.abc import Callable, Iterator

from app.gateway.contract import (
    AuthError,
    GatewayError,
    LLMRequest,
    LLMResponse,
    MalformedResponseError,
    ProviderTimeoutError,
    StreamEvent,
    ToolCall,
)
from app.gateway.providers.base import Pricing

_ENVELOPE_RULES = (
    "You MUST reply with ONE JSON object and nothing else — no prose, no markdown "
    'fences. Schema: {"reply": <string or null>, "tool_calls": [{"name": <string>, '
    '"arguments": <object>}]}. Put any natural-language answer in "reply". To call a '
    'tool, add an entry to "tool_calls" whose "arguments" match that tool\'s '
    'input_schema. When you have no tool to call, use an empty list for "tool_calls".'
)
_CORRECTIVE_SUFFIX = (
    "\n\nYour previous reply was not valid. Respond again with ONLY the JSON envelope "
    "described above — a single object, no fences, no commentary."
)
_ANY_RULE = 'Because a tool call is required, "tool_calls" MUST contain at least one entry.'

_CompletedProcess = subprocess.CompletedProcess


def _default_runner(argv: list[str], timeout: float) -> _CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)


def _sentence_chunks(text: str) -> list[str]:
    """Split text into sentence-ish chunks whose concatenation is EXACTLY the input.

    Whitespace-only fragments are merged into the preceding chunk rather than
    dropped, so ``"".join(chunks) == text`` always holds — the streamed deltas
    must reassemble byte-for-byte into the final response text. Sentence
    delimiters include the Devanagari danda for Hindi copy.
    """
    if not text:
        return []
    parts = [p for p in re.findall(r".*?(?:[.!?।](?=\s|$)|\n+|$)", text, flags=re.DOTALL) if p]
    chunks: list[str] = []
    for p in parts:
        if chunks and not p.strip():
            chunks[-1] += p
        else:
            chunks.append(p)
    return chunks or [text]


class ClaudeCLIProvider:
    name = "claude_cli"

    def __init__(
        self,
        pricing: Pricing,
        *,
        binary: str | None = None,
        runner: Callable[[list[str], float], _CompletedProcess] | None = None,
        timeout: float = 120.0,
    ):
        self._pricing = pricing  # kept for parity; cli cost is always 0 (subscription)
        self._binary = binary or shutil.which("claude") or "claude"
        self._runner = runner or _default_runner
        self._timeout = timeout

    # -- prompt assembly ---------------------------------------------------

    def _build_prompt(self, req: LLMRequest) -> str:
        blocks: list[str] = []
        systems = [m.content for m in req.messages if m.role == "system" and m.content]
        if systems:
            blocks.append("SYSTEM:\n" + "\n\n".join(systems))
        if req.tools:
            tool_json = json.dumps(
                [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in req.tools],
                ensure_ascii=False,
            )
            blocks.append("AVAILABLE TOOLS (JSON):\n" + tool_json)

        transcript: list[str] = []
        for m in req.messages:
            if m.role == "system":
                continue
            if m.role == "assistant" and m.tool_calls:
                calls = json.dumps([{"name": c.name, "arguments": c.arguments} for c in m.tool_calls], ensure_ascii=False)
                transcript.append(f"ASSISTANT (tool calls): {calls}")
            elif m.role == "tool":
                transcript.append(f"TOOL RESULT [{m.tool_call_id or ''}]: {m.content or ''}")
            else:
                transcript.append(f"{m.role.upper()}: {m.content or ''}")
        if transcript:
            blocks.append("CONVERSATION:\n" + "\n".join(transcript))

        rules = _ENVELOPE_RULES
        if req.tool_choice == "any":
            rules += " " + _ANY_RULE
        elif req.tool_choice == "none":
            rules += ' Do not call any tools; leave "tool_calls" empty.'
        blocks.append(rules)
        return "\n\n".join(blocks)

    # -- subprocess + parsing ---------------------------------------------

    def _run(self, prompt: str, model: str) -> dict:
        argv = [self._binary, "-p", prompt, "--model", model, "--output-format", "json", "--max-turns", "1"]
        try:
            proc = self._runner(argv, self._timeout)
        except subprocess.TimeoutExpired as e:  # noqa: PERF203
            raise ProviderTimeoutError(self.name, "claude CLI timed out", e) from e
        except FileNotFoundError as e:
            raise GatewayError(self.name, f"claude binary not found at '{self._binary}'", e) from e
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            if "auth" in stderr.lower() or "logged in" in stderr.lower() or "api key" in stderr.lower():
                raise AuthError(self.name, "the claude CLI is not authenticated — run `claude` and sign in", None)
            raise GatewayError(self.name, f"claude CLI exited {proc.returncode}: {stderr[:400]}", None)
        try:
            return json.loads(proc.stdout)
        except (json.JSONDecodeError, TypeError) as e:
            raise GatewayError(self.name, "claude CLI did not return JSON on stdout", e) from e

    @staticmethod
    def _extract_envelope(result_text: str) -> dict:
        # Prefer a fenced ```json block when present; if its content is
        # unusable, fall back to the outermost braces of the full text —
        # avoids wasting the corrective retry on prose that contains braces.
        t = (result_text or "").strip()
        candidates: list[str] = []
        fenced = re.search(r"```(?:json)?\s*(.*?)```", t, flags=re.DOTALL)
        if fenced:
            candidates.append(fenced.group(1).strip())
        candidates.append(t)
        for c in candidates:
            start, end = c.find("{"), c.rfind("}")
            if start == -1 or end <= start:
                continue
            try:
                return json.loads(c[start : end + 1])
            except json.JSONDecodeError:
                continue
        raise ValueError("no JSON object in reply")

    def _parse(self, data: dict, req: LLMRequest) -> tuple[str | None, list[ToolCall]] | None:
        """Return (reply, tool_calls) or None if the envelope is unusable."""
        try:
            env = self._extract_envelope(data.get("result", ""))
        except (ValueError, json.JSONDecodeError):
            return None
        if not isinstance(env, dict):
            return None
        reply = env.get("reply")
        if reply is not None and not isinstance(reply, str):
            reply = json.dumps(reply)
        raw_calls = env.get("tool_calls") or []
        if not isinstance(raw_calls, list):
            return None
        tool_calls: list[ToolCall] = []
        for c in raw_calls:
            if not isinstance(c, dict) or "name" not in c:
                return None
            args = c.get("arguments") or {}
            if not isinstance(args, dict):
                return None
            tool_calls.append(ToolCall(id=f"call_{uuid.uuid4().hex[:12]}", name=c["name"], arguments=args))
        if req.tool_choice == "any" and not tool_calls:
            return None
        return reply, tool_calls

    def _tokens(self, data: dict, prompt: str, reply: str | None, tool_calls: list[ToolCall]) -> tuple[int, int]:
        usage = data.get("usage") or {}
        in_tok = usage.get("input_tokens")
        out_tok = usage.get("output_tokens")
        if isinstance(in_tok, int):
            in_tok += int(usage.get("cache_read_input_tokens", 0) or 0)
            in_tok += int(usage.get("cache_creation_input_tokens", 0) or 0)
        else:
            in_tok = len(prompt) // 4
        if not isinstance(out_tok, int):
            produced = (reply or "") + json.dumps([c.arguments for c in tool_calls])
            out_tok = len(produced) // 4
        return in_tok, out_tok

    @staticmethod
    def _model_used(data: dict, model: str) -> str:
        mu = data.get("modelUsage") or {}
        for k in mu:
            return k
        return model

    # -- contract ----------------------------------------------------------

    def complete(self, req: LLMRequest, model: str) -> LLMResponse:
        prompt = self._build_prompt(req)
        t0 = time.perf_counter()
        data = self._run(prompt, model)
        parsed = self._parse(data, req)
        if parsed is None:
            data = self._run(prompt + _CORRECTIVE_SUFFIX, model)
            parsed = self._parse(data, req)
            if parsed is None:
                raise MalformedResponseError(
                    self.name,
                    "model did not return a valid tool/JSON envelope after one corrective retry",
                    None,
                )
        reply, tool_calls = parsed
        latency_ms = int((time.perf_counter() - t0) * 1000)
        in_tok, out_tok = self._tokens(data, prompt, reply, tool_calls)
        return LLMResponse(
            text=reply,
            tool_calls=tool_calls,
            model_used=self._model_used(data, model),
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=latency_ms,
            cost_estimate_usd=0.0,
        )

    def stream(self, req: LLMRequest, model: str) -> Iterator[StreamEvent]:
        # Pseudo-streaming: the CLI is one-shot, so complete first, then chunk.
        resp = self.complete(req, model)
        for chunk in _sentence_chunks(resp.text or ""):
            yield StreamEvent(type="delta", delta=chunk)
        yield StreamEvent(type="final", response=resp)
