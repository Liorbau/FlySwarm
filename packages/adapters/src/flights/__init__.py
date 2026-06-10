"""Flight source factory (mirrors ``get_llm_client``).

Selecting/swapping a source is config-only: ``config/sources.yaml`` +
``.env``. Adding the next source = one adapter file + one ``sources.yaml`` entry
+ one ``.env.example`` placeholder + a branch here.
"""

from __future__ import annotations

from typing import Optional

from packages.contracts.src.flight_source import FlightSource
from packages.shared.src.config import resolve_source_config

from .travelpayouts_source import SOURCE_NAME as TRAVELPAYOUTS, TravelpayoutsFlightSource


def get_flight_source(*, source_override: Optional[str] = None) -> FlightSource:
    """Build a flight source client from resolved project config."""
    resolved = resolve_source_config(source_override=source_override)

    if resolved.source == TRAVELPAYOUTS:
        return TravelpayoutsFlightSource(
            base_url=resolved.base_url,
            currency=resolved.currency,
            api_key=resolved.api_key,
            marker=resolved.marker,
            options=resolved.options,
        )

    raise ValueError(
        f"Unknown flight source '{resolved.source}'. "
        f"Supported: {TRAVELPAYOUTS}."
    )


__all__ = ["get_flight_source", "TravelpayoutsFlightSource"]
