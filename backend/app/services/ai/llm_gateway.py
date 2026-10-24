"""The one place Pairly talks to an LLM.

Speaks the OpenAI-compatible chat completions API, which both Groq and Gemini
offer. The provider is picked from env vars (see config.py):

    LLM_PROVIDER   groq | gemini | none  (empty: first provider with a key)
    GROQ_API_KEY / GEMINI_API_KEY
    LLM_MODEL      optional model override
    LLM_BASE_URL   optional base URL override (any OpenAI-compatible server)

Every call has a timeout and is retried once on timeouts, connection errors,
429 and 5xx. A stream is only retried if nothing has been received yet.
"""
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Iterator, Optional

import httpx

from config import get_config

logger = logging.getLogger("pairly.ai")

PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "key_attr": "GROQ_API_KEY",
        "json_mode": True,
        "stream_usage": True,
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.5-flash",
        "key_attr": "GEMINI_API_KEY",
        "json_mode": False,
        "stream_usage": False,
    },
}

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}


class LLMError(Exception):
    """The provider could not be reached or returned an error."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON string from the model

    def to_message(self):
        return {"id": self.id, "type": "function", "function": {"name": self.name, "arguments": self.arguments}}


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: "Usage"):
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens

    @classmethod
    def from_dict(cls, d):
        d = d or {}
        p, c = int(d.get("prompt_tokens") or 0), int(d.get("completion_tokens") or 0)
        return cls(p, c, int(d.get("total_tokens") or (p + c)))


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: list = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)


@dataclass
class StreamEvent:
    """kind is one of: text, tool_calls, usage."""

    kind: str
    text: str = ""
    tool_calls: list = field(default_factory=list)
    usage: Optional[Usage] = None


class LLMGateway:
    def __init__(self, provider, api_key, model=None, base_url=None, timeout=30.0, client=None):
        spec = PROVIDERS.get(provider, {})
        self.provider = provider
        self.model = model or spec.get("model")
        self.base_url = (base_url or spec.get("base_url") or "").rstrip("/")
        self.json_mode_supported = spec.get("json_mode", False)
        self.stream_usage_supported = spec.get("stream_usage", False)
        self.timeout = timeout
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=httpx.Timeout(timeout, connect=10.0))

    # ---------- public API ----------

    def complete(self, messages, tools=None, json_mode=False, temperature=0.2) -> LLMResponse:
        body = self._body(messages, tools, temperature)
        if json_mode and self.json_mode_supported:
            body["response_format"] = {"type": "json_object"}
        data = self._post_with_retry(body)
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        calls = [
            ToolCall(c.get("id") or _new_id(), c["function"]["name"], c["function"].get("arguments") or "{}")
            for c in (msg.get("tool_calls") or [])
        ]
        return LLMResponse(content=msg.get("content") or "", tool_calls=calls, usage=Usage.from_dict(data.get("usage")))

    def stream(self, messages, tools=None, temperature=0.2) -> Iterator[StreamEvent]:
        body = self._body(messages, tools, temperature)
        body["stream"] = True
        if self.stream_usage_supported:
            body["stream_options"] = {"include_usage": True}

        for attempt in (1, 2):
            received = False
            try:
                for event in self._stream_once(body):
                    received = True
                    yield event
                return
            except LLMError as exc:
                if received or attempt == 2 or not getattr(exc, "retryable", False):
                    raise
                logger.warning("LLM stream failed (%s), retrying once", exc)
                time.sleep(0.5)

    # ---------- internals ----------

    def _body(self, messages, tools, temperature):
        body = {"model": self.model, "messages": messages, "temperature": temperature}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        return body

    def _headers(self):
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    def _post_with_retry(self, body):
        last = None
        for attempt in (1, 2):
            try:
                r = self._client.post(f"{self.base_url}/chat/completions", headers=self._headers(), json=body)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last = _error(f"{self.provider} request failed: {type(exc).__name__}", retryable=True)
            else:
                if r.status_code < 400:
                    return r.json()
                last = _error(f"{self.provider} returned HTTP {r.status_code}: {r.text[:300]}",
                              retryable=r.status_code in RETRYABLE_STATUS)
            if attempt == 1 and last.retryable:
                logger.warning("LLM call failed (%s), retrying once", last)
                time.sleep(0.5)
                continue
            raise last
        raise last

    def _stream_once(self, body):
        calls = {}  # index -> {"id", "name", "arguments"}
        try:
            with self._client.stream("POST", f"{self.base_url}/chat/completions",
                                     headers=self._headers(), json=body) as r:
                if r.status_code >= 400:
                    r.read()
                    raise _error(f"{self.provider} returned HTTP {r.status_code}: {r.text[:300]}",
                                 retryable=r.status_code in RETRYABLE_STATUS)
                for line in r.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    usage = chunk.get("usage") or (chunk.get("x_groq") or {}).get("usage")
                    if usage:
                        yield StreamEvent("usage", usage=Usage.from_dict(usage))
                    for choice in chunk.get("choices") or []:
                        delta = choice.get("delta") or {}
                        if delta.get("content"):
                            yield StreamEvent("text", text=delta["content"])
                        for pos, tc in enumerate(delta.get("tool_calls") or []):
                            idx = tc.get("index", pos)
                            slot = calls.setdefault(idx, {"id": None, "name": "", "arguments": ""})
                            slot["id"] = tc.get("id") or slot["id"]
                            fn = tc.get("function") or {}
                            slot["name"] += fn.get("name") or ""
                            slot["arguments"] += fn.get("arguments") or ""
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise _error(f"{self.provider} stream failed: {type(exc).__name__}", retryable=True) from exc

        if calls:
            yield StreamEvent("tool_calls", tool_calls=[
                ToolCall(c["id"] or _new_id(), c["name"], c["arguments"] or "{}")
                for _, c in sorted(calls.items())
            ])


def _new_id():
    return f"call_{uuid.uuid4().hex[:12]}"


def _error(message, retryable):
    err = LLMError(message)
    err.retryable = retryable
    return err


def resolve_provider(config=None):
    """Return (provider, api_key) or (None, reason)."""
    config = config or get_config()
    wanted = config.LLM_PROVIDER
    if wanted in ("none", "off", "disabled"):
        return None, "disabled_by_env"
    candidates = [wanted] if wanted else list(PROVIDERS)
    for name in candidates:
        spec = PROVIDERS.get(name)
        if spec is None:
            return None, f"unknown_provider:{name}"
        key = getattr(config, spec["key_attr"], None)
        if key:
            return name, key
    return None, "not_configured"


_gateway = None
_gateway_checked = False


def get_gateway() -> Optional[LLMGateway]:
    """The process-wide gateway, or None when no provider is configured.

    Also used as a FastAPI dependency, so tests swap in a mock with
    app.dependency_overrides[get_gateway].
    """
    global _gateway, _gateway_checked
    if not _gateway_checked:
        config = get_config()
        provider, key = resolve_provider(config)
        if provider:
            _gateway = LLMGateway(provider, key, config.LLM_MODEL, config.LLM_BASE_URL, config.LLM_TIMEOUT_SECONDS)
            logger.info("Pairly AI: using %s (%s)", provider, _gateway.model)
        else:
            logger.info("Pairly AI: no LLM provider (%s); using template summaries only", key)
        _gateway_checked = True
    return _gateway
