"""Product tools for the interface agent — saving/listing monitoring criteria.

The user-facing counterpart to the harness's coding tools. Each tool follows the
same contract (``execute(args: dict) -> str`` returning a JSON string), but is
*bound* to a specific ``user_id`` and ``Repository`` at build time so the LLM can
never set the user id itself. ``build_criteria_toolset`` assembles a ``ToolSet``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Callable

from harness.tools import ToolSet
from packages.adapters.src.storage import Storage
from packages.domain.src import LESSON, MonitoringCriterion, SearchQuery
from packages.domain.src.learnings import LearningsService
from packages.domain.src.policies import compute_expiry, route_insight_text
from packages.domain.src.prices import PricesService
from packages.domain.src.watches import WatchesService

# ── tool schemas (static; bound to a user at build time) ─────────────────────

_SAVE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "save_criterion",
        "description": (
            "Persist a flight-monitoring criterion for the current user. Call this "
            "once you have at least an origin and a destination. Use IATA city/"
            "airport codes (e.g. Tel Aviv -> TLV, London -> LON, New York -> NYC)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "Origin IATA code, e.g. TLV."},
                "destination": {"type": "string", "description": "Destination IATA code, e.g. LON."},
                "depart_date": {
                    "type": "string",
                    "description": "Departure date as YYYY-MM-DD, or YYYY-MM for a flexible month. Omit if unknown.",
                },
                "return_date": {
                    "type": "string",
                    "description": "Return date as YYYY-MM-DD or YYYY-MM. Omit for one-way or if unknown.",
                },
                "currency": {"type": "string", "description": "ISO 4217 code; defaults to USD."},
                "target_price": {
                    "type": "number",
                    "description": "Optional budget/threshold in the chosen currency.",
                },
                "label": {
                    "type": "string",
                    "description": "Short human label, ideally the user's original phrasing.",
                },
            },
            "required": ["origin", "destination"],
        },
    },
}

_LIST_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_criteria",
        "description": "List the current user's active flight-monitoring criteria.",
        "parameters": {"type": "object", "properties": {}},
    },
}

_DEACTIVATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "deactivate_criterion",
        "description": "Stop monitoring one of the current user's criteria, by its id.",
        "parameters": {
            "type": "object",
            "properties": {
                "criterion_id": {"type": "integer", "description": "Id of the criterion to deactivate."}
            },
            "required": ["criterion_id"],
        },
    },
}

_INSIGHT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "route_insight",
        "description": (
            "Look up what the swarm has learned about a route (typical prices and "
            "past lessons) before saving. Use it to sanity-check a user's target and "
            "give data-informed guidance. Returns null when nothing is known yet."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "Origin IATA code."},
                "destination": {"type": "string", "description": "Destination IATA code."},
                "target_price": {
                    "type": "number",
                    "description": "The user's target, to check against typical prices.",
                },
            },
            "required": ["origin", "destination"],
        },
    },
}


def _err(message: str) -> str:
    return json.dumps({"error": message})


def make_save_criterion(watches: WatchesService, user_id: str) -> Callable[[dict], str]:
    def execute(args: dict) -> str:
        origin = (args.get("origin") or "").strip()
        destination = (args.get("destination") or "").strip()
        if not origin or not destination:
            return _err("origin and destination are required")

        target_price = args.get("target_price")
        try:
            target_price = float(target_price) if target_price is not None else None
        except (TypeError, ValueError):
            return _err("target_price must be a number")

        return_date = args.get("return_date") or None
        query = SearchQuery(
            origin=origin,
            destination=destination,
            depart_date=args.get("depart_date") or None,
            return_date=return_date,
            currency=(args.get("currency") or "USD"),
            one_way=return_date is None,
        )
        created_at = datetime.now(timezone.utc)
        saved = watches.add(
            MonitoringCriterion(
                user_id=user_id,
                query=query,
                target_price=target_price,
                label=(args.get("label") or None),
                created_at=created_at,
                expires_at=compute_expiry(query, created_at),
            )
        )
        return json.dumps(
            {
                "saved": True,
                "id": saved.id,
                "origin": query.origin,
                "destination": query.destination,
                "depart_date": query.depart_date,
                "return_date": query.return_date,
                "currency": query.currency,
                "target_price": saved.target_price,
                "monitored_until": saved.expires_at.date().isoformat() if saved.expires_at else None,
            }
        )

    return execute


def make_list_criteria(watches: WatchesService, user_id: str) -> Callable[[dict], str]:
    def execute(args: dict) -> str:
        items = watches.list_for_user(user_id)
        return json.dumps(
            {
                "count": len(items),
                "criteria": [
                    {
                        "id": c.id,
                        "origin": c.query.origin,
                        "destination": c.query.destination,
                        "depart_date": c.query.depart_date,
                        "return_date": c.query.return_date,
                        "currency": c.query.currency,
                        "target_price": c.target_price,
                        "label": c.label,
                    }
                    for c in items
                ],
            }
        )

    return execute


def make_deactivate_criterion(watches: WatchesService, user_id: str) -> Callable[[dict], str]:
    def execute(args: dict) -> str:
        criterion_id = args.get("criterion_id")
        if criterion_id is None:
            return _err("criterion_id is required")
        existing = watches.get(int(criterion_id))
        if existing is None or existing.user_id != user_id:
            return _err(f"no criterion {criterion_id} for this user")
        watches.stop(int(criterion_id))
        return json.dumps({"deactivated": True, "id": int(criterion_id)})

    return execute


def make_route_insight(prices: PricesService, learnings: LearningsService) -> Callable[[dict], str]:
    def execute(args: dict) -> str:
        origin = (args.get("origin") or "").strip()
        destination = (args.get("destination") or "").strip()
        if not origin or not destination:
            return _err("origin and destination are required")
        target_price = args.get("target_price")
        try:
            target_price = float(target_price) if target_price is not None else None
        except (TypeError, ValueError):
            target_price = None
        history = prices.history(origin, destination, limit=500)
        lessons = learnings.for_route(origin, destination, kind=LESSON, limit=3)
        insight = route_insight_text(history, lessons, target_price=target_price)
        return json.dumps({"insight": insight})

    return execute


def build_criteria_toolset(storage: Storage, user_id: str) -> ToolSet:
    """Assemble the criteria tools, bound to one user, into a harness ToolSet."""
    watches = WatchesService(storage.criteria)
    prices = PricesService(storage.prices)
    learnings = LearningsService(storage.learnings)
    return ToolSet(
        schemas=[_SAVE_SCHEMA, _LIST_SCHEMA, _DEACTIVATE_SCHEMA, _INSIGHT_SCHEMA],
        registry={
            "save_criterion": make_save_criterion(watches, user_id),
            "list_criteria": make_list_criteria(watches, user_id),
            "deactivate_criterion": make_deactivate_criterion(watches, user_id),
            "route_insight": make_route_insight(prices, learnings),
        },
    )


__all__ = ["build_criteria_toolset"]
