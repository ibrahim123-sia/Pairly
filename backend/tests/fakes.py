"""A scripted stand-in for LLMGateway. Tests never call a real LLM API."""
import json

from app.services.ai.llm_gateway import LLMError, LLMResponse, StreamEvent, ToolCall, Usage


class FakeGateway:
    provider = "fake"
    model = "fake-model"

    def __init__(self, replies=None, rounds=None):
        # replies: list of str (or Exception) returned by complete(), in order
        # rounds: list of rounds for stream(); each round is a str (answer text),
        #         a list of (tool_name, args_dict) tool calls, or an Exception
        self.replies = list(replies or [])
        self.rounds = list(rounds or [])
        self.complete_calls = []
        self.stream_calls = []

    def complete(self, messages, tools=None, json_mode=False, temperature=0.2):
        self.complete_calls.append(json.loads(json.dumps(messages)))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return LLMResponse(content=reply, usage=Usage(100, 50, 150))

    def stream(self, messages, tools=None, temperature=0.2):
        self.stream_calls.append({"messages": json.loads(json.dumps(messages, default=str)), "tools": tools})
        step = self.rounds.pop(0)
        if isinstance(step, Exception):
            raise step
        if isinstance(step, str):
            for word in step.split(" "):
                yield StreamEvent("text", text=word + " ")
        else:
            yield StreamEvent("tool_calls", tool_calls=[
                ToolCall(f"call_{i}", name, json.dumps(args)) for i, (name, args) in enumerate(step)
            ])
        yield StreamEvent("usage", usage=Usage(200, 40, 240))


def llm_down():
    err = LLMError("fake provider is down")
    err.retryable = True
    return err


def insights_json(items):
    return json.dumps({"insights": items})
