"""Route insight policy — summarize price history + lessons into one line.

Pure and vendor-neutral: callers fetch the data (history, lessons) from the
repository and pass it in. Used by the interface agent to give data-informed
guidance when a user sets up monitoring (the read side of the self-improving loop).
"""

from __future__ import annotations

from typing import Optional, Sequence

from packages.domain.src.entities.learning import Learning
from packages.domain.src.entities.price_observation import PriceObservation


def route_insight_text(
    history: Sequence[PriceObservation],
    lessons: Sequence[Learning] = (),
    *,
    target_price: Optional[float] = None,
) -> Optional[str]:
    """One-line insight for a route, or None if there's nothing useful to say yet."""
    parts: list[str] = []
    prices = [h.price.amount for h in history]

    if prices:
        currency = history[0].price.currency
        low, high = min(prices), max(prices)
        avg = sum(prices) / len(prices)
        parts.append(
            f"{len(prices)} prices seen for this route: "
            f"low {low:.0f}, avg {avg:.0f}, high {high:.0f} {currency}."
        )
        if target_price is not None and target_price < low:
            parts.append(
                f"Note: a target of {target_price:.0f} is below the lowest price ever "
                f"seen ({low:.0f} {currency}); it may rarely trigger."
            )

    for lesson in list(lessons)[:3]:
        parts.append(f"Past lesson: {lesson.text}")

    return " ".join(parts) if parts else None


__all__ = ["route_insight_text"]
