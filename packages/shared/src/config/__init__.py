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


# Which env vars hold each flight source's secrets (mirror _PROVIDER_ENV_KEYS).
_SOURCE_ENV_KEYS: dict[str, dict[str, tuple[str, ...]]] = {
    "travelpayouts": {
        "api_key": ("TRAVELPAYOUTS_API_KEY", "TRAVELPAYOUTS_TOKEN"),
        "marker": ("TRAVELPAYOUTS_MARKER",),
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


@dataclass(frozen=True)
class ResolvedSourceConfig:
    """Fully resolved flight-source configuration used by the source factory."""

    source: str
    base_url: str
    currency: str = "USD"
    options: dict[str, Any] = field(default_factory=dict)
    api_key: Optional[str] = None
    marker: Optional[str] = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _first_env(env_keys: tuple[str, ...]) -> Optional[str]:
    for key in env_keys:
        value = os.getenv(key)
        if value:
            return value
    return None


def _load_yaml_mapping(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid config format in {config_path}")
    return raw


def _load_models_yaml(config_path: Path) -> dict[str, Any]:
    return _load_yaml_mapping(config_path)


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


def resolve_source_config(
    config_path: Optional[Path] = None,
    *,
    source_override: Optional[str] = None,
) -> ResolvedSourceConfig:
    """Resolve flight source, base URL, and client params from config + env."""
    load_dotenv()

    path = config_path or (_repo_root() / "config" / "sources.yaml")
    config = _load_yaml_mapping(path)

    sources = config.get("sources") or {}
    if not isinstance(sources, dict) or not sources:
        raise ValueError(f"No sources configured in {path}")

    selected_source = (
        source_override
        or os.getenv("FLIGHT_SOURCE")
        or config.get("default_source")
    )
    if not selected_source:
        raise ValueError("No flight source configured (set default_source or FLIGHT_SOURCE)")

    source_name = str(selected_source).strip().lower()
    if source_name not in sources:
        supported = ", ".join(sorted(sources.keys()))
        raise ValueError(f"Unknown source '{source_name}'. Supported: {supported}")

    source_cfg = sources[source_name] or {}
    base_url = source_cfg.get("base_url")
    if not base_url:
        raise ValueError(f"Source '{source_name}' is missing required 'base_url'")

    currency = str(source_cfg.get("currency", "USD")).strip().upper() or "USD"
    options = dict(source_cfg.get("options") or {})
    env_keys = _SOURCE_ENV_KEYS.get(source_name, {})

    return ResolvedSourceConfig(
        source=source_name,
        base_url=str(base_url),
        currency=currency,
        options=options,
        api_key=_first_env(env_keys.get("api_key", ())),
        marker=_first_env(env_keys.get("marker", ())),
    )


__all__ = [
    "ResolvedLLMConfig",
    "ResolvedSourceConfig",
    "resolve_llm_config",
    "resolve_source_config",
]
