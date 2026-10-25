"""LLM gateway: provider order, Gemini fallback, retry, and SSE parsing.

HTTP is served by httpx.MockTransport, so nothing leaves the machine.
"""
import json
from types import SimpleNamespace

import httpx
import pytest

from app.services.ai.llm_gateway import (
    FallbackGateway,
    LLMError,
    LLMGateway,
    LLMResponse,
    StreamEvent,
    build_gateway,
    resolve_providers,
)


def cfg(**kw):
    base = dict(LLM_PROVIDER="", GROQ_API_KEY=None, GEMINI_API_KEY=None, LLM_MODEL=None, LLM_BASE_URL=None,
                LLM_TIMEOUT_SECONDS=5.0)
    return SimpleNamespace(**{**base, **kw})


# ---------------- provider order ----------------

def test_groq_first_then_gemini_fallback():
    chosen, reason = resolve_providers(cfg(GROQ_API_KEY="g", GEMINI_API_KEY="m"))
    assert [n for n, _ in chosen] == ["groq", "gemini"] and reason is None


def test_llm_provider_picks_the_primary():
    chosen, _ = resolve_providers(cfg(LLM_PROVIDER="gemini", GROQ_API_KEY="g", GEMINI_API_KEY="m"))
    assert [n for n, _ in chosen] == ["gemini", "groq"]


def test_only_providers_with_keys_are_used():
    assert [n for n, _ in resolve_providers(cfg(GEMINI_API_KEY="m"))[0]] == ["gemini"]
    assert resolve_providers(cfg()) == ([], "not_configured")
    assert resolve_providers(cfg(LLM_PROVIDER="none", GROQ_API_KEY="g")) == ([], "disabled_by_env")
    assert resolve_providers(cfg(LLM_PROVIDER="openrouter"))[1] == "unknown_provider:openrouter"


def test_model_override_applies_to_primary_only():
    gw, _ = build_gateway(cfg(GROQ_API_KEY="g", GEMINI_API_KEY="m", LLM_MODEL="custom-model"))
    assert [(g.provider, g.model) for g in gw.gateways] == [("groq", "custom-model"), ("gemini", "gemini-2.5-flash")]


# ---------------- fallback ----------------

class Stub:
    def __init__(self, provider, fail=False, events=None, fail_after=None):
        self.provider, self.model = provider, f"{provider}-model"
        self.fail, self.events, self.fail_after = fail, events or [], fail_after
        self.calls = 0

    def complete(self, *a, **k):
        self.calls += 1
        if self.fail:
            raise LLMError(f"{self.provider} down")
        return LLMResponse(content=f"from {self.provider}")

    def stream(self, *a, **k):
        self.calls += 1
        if self.fail:
            raise LLMError(f"{self.provider} down")
        for i, ev in enumerate(self.events):
            if self.fail_after is not None and i == self.fail_after:
                raise LLMError("dropped mid-stream")
            yield ev


def test_complete_falls_back_to_gemini():
    groq, gemini = Stub("groq", fail=True), Stub("gemini")
    fb = FallbackGateway([groq, gemini])
    assert fb.complete([]).content == "from gemini"
    assert fb.provider == "gemini" and groq.calls == 1


def test_complete_raises_when_all_fail():
    with pytest.raises(LLMError):
        FallbackGateway([Stub("groq", fail=True), Stub("gemini", fail=True)]).complete([])


def test_stream_falls_back_before_any_output():
    fb = FallbackGateway([Stub("groq", fail=True), Stub("gemini", events=[StreamEvent("text", text="hi")])])
    assert [e.text for e in fb.stream([])] == ["hi"]
    assert fb.provider == "gemini"


def test_stream_does_not_mix_providers_mid_answer():
    gemini = Stub("gemini", events=[StreamEvent("text", text="x")])
    groq = Stub("groq", events=[StreamEvent("text", text="a"), StreamEvent("text", text="b")], fail_after=1)
    fb = FallbackGateway([groq, gemini])
    got = []
    with pytest.raises(LLMError):
        for e in fb.stream([]):
            got.append(e.text)
    assert got == ["a"] and gemini.calls == 0


# ---------------- HTTP client ----------------

def _gateway(handler):
    return LLMGateway("groq", "test-key", client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_retries_once_on_503_then_succeeds():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503, text="busy")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}],
                                         "usage": {"prompt_tokens": 3, "completion_tokens": 2}})

    resp = _gateway(handler).complete([{"role": "user", "content": "hi"}], json_mode=True)
    assert resp.content == "ok" and resp.usage.total_tokens == 5 and len(calls) == 2
    body = json.loads(calls[0].content)
    assert body["response_format"] == {"type": "json_object"} and body["model"] == "llama-3.3-70b-versatile"
    assert calls[0].headers["authorization"] == "Bearer test-key"


def test_gives_up_after_one_retry():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(LLMError):
        _gateway(handler).complete([])
    assert len(calls) == 2


def test_client_errors_are_not_retried():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(401, text="bad key")

    with pytest.raises(LLMError, match="401"):
        _gateway(handler).complete([])
    assert len(calls) == 1


def test_stream_parses_text_tool_calls_and_usage():
    chunks = [
        {"choices": [{"delta": {"content": "Let me "}}]},
        {"choices": [{"delta": {"content": "check."}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "c1", "function": {"name": "get_bun", "arguments": ""}}]}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"name": "dles", "arguments": "{\"limit\": 3}"}}]}}]},
        {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14}},
    ]
    sse = "".join(f"data: {json.dumps(c)}\n\n" for c in chunks) + "data: [DONE]\n\n"

    def handler(request):
        return httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})

    events = list(_gateway(handler).stream([{"role": "user", "content": "hi"}], tools=[{"type": "function"}]))
    assert "".join(e.text for e in events if e.kind == "text") == "Let me check."
    calls = next(e for e in events if e.kind == "tool_calls").tool_calls
    assert [(c.id, c.name, c.arguments) for c in calls] == [("c1", "get_bundles", '{"limit": 3}')]
    assert next(e for e in events if e.kind == "usage").usage.total_tokens == 14
