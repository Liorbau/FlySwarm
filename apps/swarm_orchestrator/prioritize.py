"""Orchestrator route-prioritizer — the agentic budgeting step.

Spends the per-cycle API budget on which routes to refresh:
1. freshness-skips seed routes observed within ``freshness_hours``;
2. asks an LLM orchestrator to rank stale candidates by corpus value under budget;
3. falls back to deterministic "stalest-first" when the LLM is off or misbehaves.

This is where "optimize API rate limits" is load-bearing: reasoning decides what to
refresh, the schedule stays deterministic.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from packages.adapters.src.llm import get_llm_client
from packages.adapters.src.storage import Storage, get_storage
from packages.domain.src import Route
from packages.domain.src.prices import PricesService

PRIORITIZE_SYSTEM_PROMPT = """You are FlySwarm's orchestrator agent. You may refresh \
at most N routes this cycle (a hard API budget). Given candidate routes — each with how \
many users watch it (``watchers``), how many hours since its last observed price \
(null = never seen), and how many history points it has — choose which to refresh \
to maximize the corpus's value to users.

Prefer routes with more watchers (highly-asked → monitor more often), then routes \
that are stale or never seen and routes with little history, while keeping coverage \
spread across destinations. Respond with VALID JSON ONLY:
{"routes": ["ORIG-DEST", "ORIG-DEST", ...]}
List at most N route keys, best-to-refresh first, taken only from the candidates."""


def _stale_candidates(
    candidates: list[Route],
    prices: PricesService,
    now: datetime,
    freshness_hours: Optional[int],
) -> list[tuple[Route, Optional[datetime], int]]:
    """Return (route, last_observed, history_points) candidates.

    When ``freshness_hours`` is None, every route is a candidate (used for watched
    routes, which are never freshness-skipped). Otherwise routes observed within
    the window are dropped.
    """
    cutoff = None if freshness_hours is None else now - timedelta(hours=freshness_hours)
    out: list[tuple[Route, Optional[datetime], int]] = []
    for route in candidates:
        hist = prices.history(route.origin, route.destination, limit=500)
        last = hist[0].observed_at if hist else None  # history is newest-first
        if cutoff is None or last is None or last < cutoff:  # stale or never seen
            out.append((route, last, len(hist)))
    return out


def _deterministic_order(
    stale: list[tuple[Route, Optional[datetime], int]],
    demand: dict[Route, int],
) -> list[Route]:
    """Most-demanded first (highly-asked routes refresh more often), then stalest.

    Data is never dropped — lower-priority routes just wait for a later cycle; all
    their existing history is retained.
    """
    floor = datetime.min.replace(tzinfo=timezone.utc)
    return [
        r
        for r, _, _ in sorted(stale, key=lambda s: (-demand.get(s[0], 0), s[1] or floor))
    ]


def prioritize_routes(
    candidates: list[Route],
    *,
    storage: Optional[Storage] = None,
    budget: int,
    now: Optional[datetime] = None,
    freshness_hours: Optional[int] = 6,
    use_llm: bool = True,
    client=None,
    demand: Optional[dict[Route, int]] = None,
) -> list[Route]:
    """Pick up to ``budget`` candidate routes to refresh this cycle.

    ``freshness_hours=None`` disables freshness-skip (all candidates eligible) —
    used for watched routes, which must stay fresh for deals. ``demand`` (watcher
    count per route) makes highly-asked routes refresh more often. Routes left out
    are simply deferred to a later cycle; their stored history is never discarded.
    """
    if budget <= 0:
        return []
    storage = storage or get_storage()
    now = now or datetime.now(timezone.utc)
    demand = demand or {}
    prices = PricesService(storage.prices)

    stale = _stale_candidates(candidates, prices, now, freshness_hours)
    if not stale:
        return []

    deterministic = _deterministic_order(stale, demand)
    if not use_llm:
        return deterministic[:budget]

    by_key = {r.key: r for r, _, _ in stale}
    facts = {
        "budget": budget,
        "candidates": [
            {
                "route": r.key, "watchers": demand.get(r, 0),
                "hours_since_last": round((now - last).total_seconds() / 3600, 1)
                if last is not None else None,
                "history_points": count,
            }
            for r, last, count in stale
        ],
    }
    try:
        client = client or get_llm_client()
        result = client.complete(messages=[
            {"role": "system", "content": PRIORITIZE_SYSTEM_PROMPT.replace("N", str(budget))},
            {"role": "user", "content": json.dumps(facts)},
        ])
        data = json.loads((result.message.content or "").strip())
        ranked = [by_key[k] for k in data["routes"] if k in by_key]
        if ranked:
            return ranked[:budget]
    except Exception:
        pass  # any LLM/parse failure -> deterministic order
    return deterministic[:budget]


__all__ = ["prioritize_routes", "PRIORITIZE_SYSTEM_PROMPT"]
