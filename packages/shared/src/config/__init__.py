"""LLM provider/model config loading and environment overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv


_PROVIDER_ENV_KEYS: dict[str, dict[str, tuple[str, ...]]] = {
    "openai": {
        "api_key": ("OPENAI_API_KEY",),
        "base_url": ("OPENAI_BASE_URL",),
    },
    "anthropic": {
        "api_key": ("ANTHROPIC_API_KEY",),
        "base_url": ("ANTHROPIC_BASE_URL",),
    },
    "google": {
        "api_key": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "base_url": ("GOOGLE_BASE_URL",),
    },
    "ollama": {
        "api_key": ("OLLAMA_API_KEY",),
        "base_url": ("OLLAMA_BASE_URL",),
    },
}


@dataclass(frozen=True)
class ResolvedLLMConfig:
    """Fully resolved provider configuration used by client factories."""

    provider: str
    model: str
    options: dict[str, Any] = field(default_factory=dict)
    api_key: Optional[str] = None
    base_url: Optional[str] = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _first_env(env_keys: tuple[str, ...]) -> Optional[str]:
    for key in env_keys:
        value = os.getenv(key)
        if value:
            return value
    return None


def _load_models_yaml(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid models config format in {config_path}")
    return raw


def resolve_llm_config(
    config_path: Optional[Path] = None,
    *,
    provider_override: Optional[str] = None,
) -> ResolvedLLMConfig:
    """Resolve provider, model, and client params from config + environment."""
    load_dotenv()

    path = config_path or (_repo_root() / "config" / "models.yaml")
    config = _load_models_yaml(path)

    providers = config.get("providers") or {}
    if not isinstance(providers, dict) or not providers:
        raise ValueError(f"No providers configured in {path}")

    selected_provider = (
        provider_override
        or os.getenv("LLM_PROVIDER")
        or config.get("default_provider")
    )
    if not selected_provider:
        raise ValueError("No LLM provider configured (set default_provider or LLM_PROVIDER)")

    provider_name = str(selected_provider).strip().lower()
    if provider_name not in providers:
        supported = ", ".join(sorted(providers.keys()))
        raise ValueError(f"Unknown provider '{provider_name}'. Supported: {supported}")

    provider_cfg = providers[provider_name] or {}
    model = provider_cfg.get("model")
    if not model:
        raise ValueError(f"Provider '{provider_name}' is missing required 'model'")

    options = dict(provider_cfg.get("options") or {})
    env_keys = _PROVIDER_ENV_KEYS.get(provider_name, {})

    return ResolvedLLMConfig(
        provider=provider_name,
        model=str(model),
        options=options,
        api_key=_first_env(env_keys.get("api_key", ())),
        base_url=_first_env(env_keys.get("base_url", ())),
    )


__all__ = ["ResolvedLLMConfig", "resolve_llm_config"]
