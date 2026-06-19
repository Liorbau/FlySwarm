"""LiteLLM-backed implementation of the FlySwarm LLMClient contract."""

from __future__ import annotations

from typing import Any, Optional

from litellm import completion, completion_cost

from packages.contracts.src.llm_provider import (
    AssistantMessage,
    CompletionResult,
    LLMClient,
    Message,
    ToolCall,
    ToolSchema,
    Usage,
)


def _read(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class LiteLLMClient(LLMClient):
    """LLM client that calls ``litellm.completion`` with OpenAI-style payloads."""

    def __init__(
        self,
        model: str,
        *,
        default_options: Optional[dict[str, Any]] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.model = model
        self.default_options = dict(default_options or {})
        self.api_key = api_key
        self.base_url = base_url

    def complete(
        self,
        messages: list[Message],
        tools: Optional[list[ToolSchema]] = None,
        tool_choice: str = "auto",
    ) -> CompletionResult:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            **self.default_options,
        }
        if self.api_key:
            payload["api_key"] = self.api_key
        if self.base_url:
            # LiteLLM provider support differs across backends:
            # - OpenAI adapters commonly accept `base_url`
            # - Many non-OpenAI adapters (including Ollama) use `api_base`
            # Setting both keeps provider switching config-only.
            payload["base_url"] = self.base_url
            payload["api_base"] = self.base_url
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        response = completion(**payload)
        choices = _read(response, "choices", []) or []
        choice = choices[0] if isinstance(choices, list) and choices else None
        message_obj = _read(choice, "message", {}) if choice is not None else {}

        tool_calls: list[ToolCall] = []
        for tool_call in _read(message_obj, "tool_calls", []) or []:
            function_payload = _read(tool_call, "function", {})
            tool_calls.append(
                ToolCall(
                    id=str(_read(tool_call, "id", "")),
                    name=str(_read(function_payload, "name", "")),
                    arguments=str(_read(function_payload, "arguments", "{}")),
                    type=str(_read(tool_call, "type", "function")),
                )
            )

        usage_obj = _read(response, "usage", {}) or {}
        usage = Usage(
            prompt_tokens=int(_read(usage_obj, "prompt_tokens", 0) or 0),
            completion_tokens=int(_read(usage_obj, "completion_tokens", 0) or 0),
            total_tokens=int(_read(usage_obj, "total_tokens", 0) or 0),
        )
        return CompletionResult(
            message=AssistantMessage(
                content=_read(message_obj, "content"),
                tool_calls=tool_calls,
            ),
            usage=usage,
            model=_read(response, "model", self.model),
            raw=response,
        )

    @staticmethod
    def get_completion_cost(result: CompletionResult) -> float:
        """Return provider-aware completion cost for a result."""
        if result.raw is None:
            return 0.0
        return float(completion_cost(completion_response=result.raw))
