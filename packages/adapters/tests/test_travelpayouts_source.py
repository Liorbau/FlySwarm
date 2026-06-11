"""Offline fixture gate for the Travelpayouts flight source adapter.

Maps a scrubbed sample response (no PII, no real token) through the adapter and
asserts the canonical FlightOffer output: airport codes, UTC datetimes, price +
ISO-4217 currency, airline/flight number, stops, expiry, and a complete
affiliate booking link. No network access.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from packages.contracts.src.flight_source import FlightSource
from packages.domain.src import FlightOffer, Money, SearchQuery
from packages.adapters.src.flights.travelpayouts_source import TravelpayoutsFlightSource

_FIXTURE = Path(__file__).resolve().parents[1] / "src" / "flights" / "fixtures" / "travelpayouts.json"


def _load_fixture() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def _adapter() -> TravelpayoutsFlightSource:
    return TravelpayoutsFlightSource(
        base_url="https://api.travelpayouts.com",
        currency="USD",
        api_key="test-token-not-real",
        marker="12345",
    )


def test_adapter_satisfies_flight_source_protocol():
    assert isinstance(_adapter(), FlightSource)


def test_maps_cheap_response_to_canonical_offers():
    adapter = _adapter()
    query = SearchQuery(origin="MOW", destination="HKT", currency="USD")

    offers = adapter._map_cheap_response(_load_fixture(), query)

    assert len(offers) == 2
    first = offers[0]
    assert isinstance(first, FlightOffer)

    # Route + codes
    assert first.origin == "MOW"
    assert first.destination == "HKT"
    assert first.airline == "UN"
    assert first.flight_number == "571"

    # Price normalized to requested ISO-4217 currency
    assert isinstance(first.price, Money)
    assert first.price.amount == 35443.0
    assert first.price.currency == "USD"

    # Datetimes are timezone-aware UTC
    assert first.departure_at == datetime(2015, 6, 9, 21, 20, tzinfo=timezone.utc)
    assert first.return_at == datetime(2015, 7, 15, 12, 40, tzinfo=timezone.utc)
    assert first.expires_at == datetime(2015, 1, 8, 18, 30, 40, tzinfo=timezone.utc)
    assert first.departure_at.tzinfo is not None

    # Gap flagged in mapping: cheap endpoint has no transfer count
    assert first.stops is None
    assert first.source == "travelpayouts"


def test_booking_link_is_affiliate_ready():
    adapter = _adapter()
    query = SearchQuery(origin="MOW", destination="HKT", currency="USD")

    first = adapter._map_cheap_response(_load_fixture(), query)[0]

    # ORIGIN + DDMM + DEST + DDMM(return) + passengers, with affiliate marker
    assert first.booking_link == "https://www.aviasales.com/search/MOW0906HKT15071?marker=12345"


def test_money_currency_is_normalized_uppercase():
    offer_currency = Money(amount=10.0, currency="usd")
    assert offer_currency.currency == "USD"


def test_unsuccessful_payload_yields_no_offers():
    adapter = _adapter()
    query = SearchQuery(origin="MOW", destination="HKT", currency="USD")
    assert adapter._map_cheap_response({"success": False, "data": {}}, query) == []
