"""LLM provider contract for FlySwarm (CLAUDE.md section 4): a vendor-neutral interface
every agent calls instead of a provider SDK. The shape is OpenAI-style so it maps 1:1
onto LiteLLM (which normalizes OpenAI / Anthropic / Google / Ollama). Implementations
live in ``packages/adapters``; agents and the harness depend only on ``LLMClient``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

# OpenAI-style chat message, e.g. {"role": "user", "content": "..."} or a
# tool/assistant message with "tool_calls". Kept as a plain dict for direct
# LiteLLM compatibility.
Message = dict[str, Any]

# OpenAI-style tool schema (function-calling JSON), as built by harness tools.
ToolSchema = dict[str, Any]


@dataclass
class ToolCall:
    """A single tool/function call requested by the assistant.

    ``arguments`` is the raw JSON-encoded string exactly as the model emitted it
    (OpenAI convention); callers ``json.loads`` it before dispatch.
    """

    id: str
    name: str
    arguments: str
    type: str = "function"


@dataclass
class AssistantMessage:
    """The assistant turn returned by the provider.

    Either ``content`` (a final/textual answer) or ``tool_calls`` (one or more
    requested tool invocations) — or both — may be present.
    """

    content: Optional[str] = None
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class Usage:
    """Token accounting for a single completion."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class CompletionResult:
    """Normalized result of one completion call."""

    message: AssistantMessage
    usage: Usage
    model: Optional[str] = None
    # Provider-native response object, for adapters that expose extras
    # (e.g. cost via litellm.completion_cost). Optional and non-portable.
    raw: Any = None


@runtime_checkable
class LLMClient(Protocol):
    """Vendor-neutral chat-completion client with tool calling.

    Implementations must accept OpenAI-style ``messages`` and ``tools`` and
    return a :class:`CompletionResult`.
    """

    def complete(
        self,
        messages: list[Message],
        tools: Optional[list[ToolSchema]] = None,
        tool_choice: str = "auto",
    ) -> CompletionResult:
        ...
