"""Deal judgment — the runtime implementation of the judge-deal skill.

A cheap deterministic gate decides whether an offer is even a candidate (target
met, or a new low vs prior history); only candidates go to the LLM for a nuanced
score and a one-line, user-facing reason. See
``.claude/skills/judge-deal/SKILL.md`` for the contract this implements.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional, Sequence

from packages.adapters.src.llm import get_llm_client
from packages.domain.src import FlightOffer, PriceObservation

JUDGE_SYSTEM_PROMPT = """You are FlySwarm's deal-quality analyst. Given a flight \
offer, the prior price history for that route, and the user's optional target \
price, decide whether this is a genuinely good deal worth notifying the user about.

Be skeptical: a price only marginally below the average is NOT a strong deal. A \
clear new low, or a price comfortably under the user's target, IS. Weight your \
confidence by how much history exists (sparse history -> lower confidence).

Respond with VALID JSON ONLY:
{"is_deal": true or false, "score": 0.0 to 1.0, "reason": "one concise sentence for the user"}
"score" is your confidence this is a good deal (0 = poor, 1 = excellent). Keep \
"reason" to a single plain sentence with no jargon."""


@dataclass
class DealVerdict:
    """The judgment for one offer."""

    is_deal: bool
    score: float
    reason: str
    target_met: bool = False
    is_new_best: bool = False


def _stats(history: Sequence[PriceObservation]) -> tuple[Optional[float], Optional[float], int]:
    prices = [h.price.amount for h in history]
    if not prices:
        return None, None, 0
    return min(prices), sum(prices) / len(prices), len(prices)


def _llm_judge(
    offer: FlightOffer,
    prior_min: Optional[float],
    prior_avg: Optional[float],
    count: int,
    target_price: Optional[float],
    client,
) -> tuple[bool, float, str]:
    facts = {
        "price": offer.price.amount,
        "currency": offer.price.currency,
        "route": f"{offer.origin}->{offer.destination}",
        "airline": offer.airline,
        "prior_min": prior_min,
        "prior_avg": round(prior_avg, 2) if prior_avg is not None else None,
        "history_points": count,
        "target_price": target_price,
    }
    result = client.complete(
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(facts)},
        ]
    )
    raw = (result.message.content or "").strip()
    try:
        data = json.loads(raw)
        return bool(data["is_deal"]), float(data["score"]), str(data["reason"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        # Fall back to a deterministic verdict if the model misbehaves.
        return True, 0.6, "Price looks favorable versus recent history."


def judge_deal(
    offer: FlightOffer,
    prior_history: Sequence[PriceObservation],
    target_price: Optional[float],
    *,
    use_llm: bool = True,
    client=None,
) -> DealVerdict:
    """Judge whether ``offer`` is alert-worthy. ``prior_history`` must EXCLUDE the
    current observation (read history before recording the new price)."""
    prior_min, prior_avg, count = _stats(prior_history)
    price = offer.price.amount

    target_met = target_price is not None and price <= target_price
    is_new_best = prior_min is not None and price < prior_min
    candidate = target_met or is_new_best

    if not candidate:
        return DealVerdict(
            is_deal=False,
            score=0.0,
            reason="Not below the user's target and not a new low.",
            target_met=target_met,
            is_new_best=is_new_best,
        )

    if not use_llm:
        if target_met:
            reason = f"At {price:.0f} {offer.price.currency}, it's at or below the target."
        else:
            reason = f"New low for this route at {price:.0f} {offer.price.currency} (was {prior_min:.0f})."
        return DealVerdict(
            is_deal=True,
            score=0.9 if target_met else 0.7,
            reason=reason,
            target_met=target_met,
            is_new_best=is_new_best,
        )

    is_deal, score, reason = _llm_judge(
        offer, prior_min, prior_avg, count, target_price, client or get_llm_client()
    )
    # A met target is the user's own bar — always a deal regardless of LLM nuance.
    if target_met:
        is_deal = True
        score = max(score, 0.85)
    return DealVerdict(
        is_deal=is_deal,
        score=score,
        reason=reason,
        target_met=target_met,
        is_new_best=is_new_best,
    )


__all__ = ["DealVerdict", "judge_deal", "JUDGE_SYSTEM_PROMPT"]
