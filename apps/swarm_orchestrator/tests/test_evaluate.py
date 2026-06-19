"""Offline tests for the analytics evaluation step (evaluate_deals, LLM off)."""

from __future__ import annotations

from datetime import timezone

from apps.swarm_orchestrator.evaluate import evaluate_deals
from apps.swarm_orchestrator.fetch import FetchReport
from apps.swarm_orchestrator.tests.helpers import NOW
from packages.domain.src import (
    FlightOffer,
    Money,
    MonitoringCriterion,
    PriceObservation,
    Route,
    SearchQuery,
)


def _offer(price: float) -> FlightOffer:
    return FlightOffer(
        origin="TLV",
        destination="LON",
        departure_at=NOW,
        price=Money(price, "USD"),
        booking_link="x",
        source="fake",
    )


def _report(offers, prior=None) -> FetchReport:
    route = Route("TLV", "LON")
    return FetchReport(
        offers_by_route={route: offers},
        prior_by_route={route: prior or []},
    )


def test_target_met_is_a_deal_and_picks_cheapest():
    crit = MonitoringCriterion(
        user_id="u1", query=SearchQuery("TLV", "LON"), target_price=300
    )
    deals = evaluate_deals([crit], _report([_offer(450), _offer(290)]), use_llm=False)
    assert len(deals) == 1
    assert deals[0].offer.price.amount == 290.0  # cheapest chosen


def test_no_deal_when_not_improved():
    crit = MonitoringCriterion(user_id="u1", query=SearchQuery("TLV", "LON"), target_price=None)
    prior = [PriceObservation("TLV", "LON", Money(200, "USD"), observed_at=NOW)]
    deals = evaluate_deals([crit], _report([_offer(260)], prior=prior), use_llm=False)
    assert deals == []  # no target, not a new low


def test_criterion_without_fetched_offers_is_skipped():
    # criterion route was not fetched this cycle -> nothing to judge
    crit = MonitoringCriterion(user_id="u1", query=SearchQuery("TLV", "NYC"))
    deals = evaluate_deals([crit], _report([_offer(100)]), use_llm=False)  # report only has TLV-LON
    assert deals == []
