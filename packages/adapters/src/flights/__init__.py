"""Flight source factory (mirrors ``get_llm_client``); selecting/swapping sources is
config-only via ``config/sources.yaml`` + ``.env``. A ``composition`` block (mode
``merge`` | ``failover``) wraps several sources in a ``CompositeFlightSource``; sources
without credentials are skipped. ``FLIGHT_SOURCE`` forces a single source.
"""

from __future__ import annotations

import os
from typing import Optional

from packages.contracts.src.flight_source import FlightSource
from packages.shared.src.config import (
    ResolvedSourceConfig,
    resolve_source_composition,
    resolve_source_config,
)

from .amadeus_source import SOURCE_NAME as AMADEUS, AmadeusFlightSource
from .composite_source import CompositeFlightSource
from .travelpayouts_source import SOURCE_NAME as TRAVELPAYOUTS, TravelpayoutsFlightSource


def _build_single(resolved: ResolvedSourceConfig) -> FlightSource:
    if resolved.source == TRAVELPAYOUTS:
        return TravelpayoutsFlightSource(
            base_url=resolved.base_url,
            currency=resolved.currency,
            api_key=resolved.api_key,
            marker=resolved.marker,
            options=resolved.options,
        )
    if resolved.source == AMADEUS:
        return AmadeusFlightSource(
            base_url=resolved.base_url,
            currency=resolved.currency,
            api_key=resolved.api_key,
            api_secret=resolved.api_secret,
            options=resolved.options,
        )
    raise ValueError(f"Unknown flight source '{resolved.source}'. Supported: {TRAVELPAYOUTS}, {AMADEUS}.")


def _has_credentials(resolved: ResolvedSourceConfig) -> bool:
    if resolved.source == AMADEUS:
        return bool(resolved.api_key and resolved.api_secret)
    if resolved.source == TRAVELPAYOUTS:
        return bool(resolved.api_key)
    return True


def get_flight_source(*, source_override: Optional[str] = None) -> FlightSource:
    """Build a flight source (single or composite) from resolved project config."""
    # An explicit override or the FLIGHT_SOURCE env var forces a single source.
    if source_override or os.getenv("FLIGHT_SOURCE"):
        return _build_single(resolve_source_config(source_override=source_override))

    comp = resolve_source_composition()
    if comp and comp.mode in ("merge", "failover") and comp.sources:
        built: list[FlightSource] = []
        for name in comp.sources:
            resolved = resolve_source_config(source_override=name)
            if _has_credentials(resolved):
                built.append(_build_single(resolved))
            else:
                print(f"[flights] skipping source '{name}' (credentials not set)")
        if not built:
            raise ValueError("No flight source has credentials configured (set API keys in .env).")
        if len(built) == 1:
            return built[0]
        return CompositeFlightSource(built, mode=comp.mode)

    return _build_single(resolve_source_config())


__all__ = [
    "get_flight_source",
    "TravelpayoutsFlightSource",
    "AmadeusFlightSource",
    "CompositeFlightSource",
]
