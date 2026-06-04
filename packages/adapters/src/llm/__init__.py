"""LLM adapter factory."""

from __future__ import annotations

from typing import Optional

from packages.contracts.src.llm_provider import LLMClient
from packages.shared.src.config import resolve_llm_config

from .litellm_client import LiteLLMClient


def get_llm_client(
    *,
    provider_override: Optional[str] = None,
    model_override: Optional[str] = None,
) -> LLMClient:
    """Build an LLM client from resolved project config."""
    resolved = resolve_llm_config(provider_override=provider_override)
    model = model_override or resolved.model
    return LiteLLMClient(
        model=model,
        default_options=resolved.options,
        api_key=resolved.api_key,
        base_url=resolved.base_url,
    )


__all__ = ["LiteLLMClient", "get_llm_client"]
