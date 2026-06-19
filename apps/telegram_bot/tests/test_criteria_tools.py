"""Offline tests for the interface agent's product tools and wiring.

Deterministic: exercises the tools directly against a temp DB; no LLM/network.
The full natural-language parse is validated by a separate live smoke check.
"""

from __future__ import annotations

import json

import pytest

from apps.telegram_bot.agent.interface_agent import build_interface_agent
from apps.telegram_bot.tools.criteria_tools import build_criteria_toolset
from packages.adapters.src.storage.sqlite import SqliteStorage


@pytest.fixture()
def storage(tmp_path):
    s = SqliteStorage(tmp_path / "t.sqlite3")
    s.initialize()
    yield s
    s.close()


def test_save_criterion_tool_persists_and_normalizes(storage):
    ts = build_criteria_toolset(storage, "u1")
    out = json.loads(
        ts.registry["save_criterion"](
            {
                "origin": "tlv",
                "destination": "lon",
                "depart_date": "2026-08",
                "target_price": 300,
                "label": "cheap london in august",
            }
        )
    )
    assert out["saved"] is True
    assert out["id"]
    assert out["origin"] == "TLV" and out["destination"] == "LON"

    items = storage.criteria.list_active(user_id="u1")
    assert len(items) == 1
    assert items[0].target_price == 300.0
    assert items[0].query.one_way is True  # no return_date -> one-way


def test_save_requires_origin_and_destination(storage):
    ts = build_criteria_toolset(storage, "u1")
    out = json.loads(ts.registry["save_criterion"]({"origin": "TLV"}))
    assert "error" in out


def test_list_and_deactivate_tools(storage):
    ts = build_criteria_toolset(storage, "u1")
    sid = json.loads(ts.registry["save_criterion"]({"origin": "TLV", "destination": "NYC"}))["id"]

    assert json.loads(ts.registry["list_criteria"]({}))["count"] == 1

    deact = json.loads(ts.registry["deactivate_criterion"]({"criterion_id": sid}))
    assert deact["deactivated"] is True
    assert json.loads(ts.registry["list_criteria"]({}))["count"] == 0


def test_deactivate_other_users_criterion_is_denied(storage):
    sid = json.loads(
        build_criteria_toolset(storage, "u1").registry["save_criterion"](
            {"origin": "TLV", "destination": "LON"}
        )
    )["id"]
    out = json.loads(
        build_criteria_toolset(storage, "u2").registry["deactivate_criterion"](
            {"criterion_id": sid}
        )
    )
    assert "error" in out  # u2 cannot touch u1's criterion


def test_build_interface_agent_wires_product_tools(storage):
    agent = build_interface_agent("u1", storage=storage, today="2026-06-11")
    assert set(agent.tools.registry) == {
        "save_criterion",
        "list_criteria",
        "deactivate_criterion",
        "route_insight",
    }
    assert "2026-06-11" in agent.system_prompt  # date injected


def test_route_insight_tool_summarizes_history(storage):
    from datetime import datetime, timezone

    from packages.domain.src import Money, PriceObservation

    for p in (400, 350, 380):
        storage.prices.record(
            PriceObservation("TLV", "LON", Money(p, "USD"), observed_at=datetime(2026, 6, 1, tzinfo=timezone.utc))
        )
    ts = build_criteria_toolset(storage, "u1")
    out = json.loads(ts.registry["route_insight"]({"origin": "TLV", "destination": "LON", "target_price": 100}))
    assert out["insight"] is not None
    assert "low 350" in out["insight"]
    assert "below the lowest" in out["insight"]  # target 100 < low 350 -> warning
