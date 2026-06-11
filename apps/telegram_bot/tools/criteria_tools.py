"""Product tools for the interface agent — saving/listing monitoring criteria.

These are the user-facing counterpart to the harness's coding tools. Each tool
follows the same contract (``execute(args: dict) -> str`` returning a JSON
string), but is *bound* to a specific ``user_id`` and ``Repository`` at build
time so the LLM can never set the user id itself (it only supplies flight
fields). ``build_criteria_toolset`` assembles them into a harness ``ToolSet``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Callable

from harness.tools import ToolSet
from packages.contracts.src.storage import Repository
from packages.domain.src import MonitoringCriterion, SearchQuery
from packages.domain.src.policies import compute_expiry

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


def _err(message: str) -> str:
    return json.dumps({"error": message})


def make_save_criterion(repo: Repository, user_id: str) -> Callable[[dict], str]:
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
        saved = repo.save_criterion(
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


def make_list_criteria(repo: Repository, user_id: str) -> Callable[[dict], str]:
    def execute(args: dict) -> str:
        items = repo.list_active_criteria(user_id=user_id)
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


def make_deactivate_criterion(repo: Repository, user_id: str) -> Callable[[dict], str]:
    def execute(args: dict) -> str:
        criterion_id = args.get("criterion_id")
        if criterion_id is None:
            return _err("criterion_id is required")
        existing = repo.get_criterion(int(criterion_id))
        if existing is None or existing.user_id != user_id:
            return _err(f"no criterion {criterion_id} for this user")
        repo.deactivate_criterion(int(criterion_id))
        return json.dumps({"deactivated": True, "id": int(criterion_id)})

    return execute


def build_criteria_toolset(repo: Repository, user_id: str) -> ToolSet:
    """Assemble the criteria tools, bound to one user, into a harness ToolSet."""
    return ToolSet(
        schemas=[_SAVE_SCHEMA, _LIST_SCHEMA, _DEACTIVATE_SCHEMA],
        registry={
            "save_criterion": make_save_criterion(repo, user_id),
            "list_criteria": make_list_criteria(repo, user_id),
            "deactivate_criterion": make_deactivate_criterion(repo, user_id),
        },
    )


__all__ = ["build_criteria_toolset"]
