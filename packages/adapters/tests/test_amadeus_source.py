"""Offline tests for the Amadeus adapter — pure vendor->canonical mapping.

No network: the OAuth/search HTTP is not exercised; we feed canned payloads to
the pure ``_map_offers`` and check date synthesis. (Live calls need real creds.)
"""

from __future__ import annotations

from datetime import datetime, timezone

from packages.adapters.src.flights.amadeus_source import SOURCE_NAME, AmadeusFlightSource
from packages.domain.src import SearchQuery

QUERY = SearchQuery("TLV", "LON")

PAYLOAD = {
    "data": [
        {
            "price": {"total": "312.40", "currency": "USD"},
            "itineraries": [
                {
                    "segments": [
                        {
                            "departure": {"iataCode": "TLV", "at": "2026-07-30T10:15:00"},
                            "arrival": {"iataCode": "LON", "at": "2026-07-30T14:30:00"},
                            "carrierCode": "BA",
                            "number": "165",
                        }
                    ]
                }
            ],
        }
    ]
}


def _adapter(**opts):
    return AmadeusFlightSource(
        base_url="https://test.api.amadeus.com",
        currency="USD",
        api_key="k",
        api_secret="s",
        options=opts,
    )


def test_maps_offer_to_canonical():
    offers = _adapter()._map_offers(PAYLOAD, QUERY)
    assert len(offers) == 1
    o = offers[0]
    assert o.origin == "TLV" and o.destination == "LON"
    assert o.price.amount == 312.40 and o.price.currency == "USD"
    assert o.airline == "BA" and o.flight_number == "BA165"
    assert o.stops == 0
    assert o.source == SOURCE_NAME
    assert o.departure_at == datetime(2026, 7, 30, 10, 15, tzinfo=timezone.utc)


def test_booking_link_is_a_neutral_google_flights_link():
    o = _adapter()._map_offers(PAYLOAD, QUERY)[0]
    assert "google.com/travel/flights" in o.booking_link
    assert "marker" not in o.booking_link  # Amadeus is NOT the monetized source


def test_stops_counts_segments():
    multi = {
        "data": [
            {
                "price": {"total": "200.00", "currency": "USD"},
                "itineraries": [
                    {
                        "segments": [
                            {"departure": {"at": "2026-07-30T10:00:00"}, "arrival": {"at": "2026-07-30T12:00:00"}, "carrierCode": "LH", "number": "1"},
                            {"departure": {"at": "2026-07-30T13:00:00"}, "arrival": {"at": "2026-07-30T15:00:00"}, "carrierCode": "LH", "number": "2"},
                        ]
                    }
                ],
            }
        ]
    }
    assert _adapter()._map_offers(multi, QUERY)[0].stops == 1


def test_malformed_offers_are_skipped():
    bad = {"data": [{"itineraries": []}, "nonsense", {"price": {"total": "x"}}]}
    assert _adapter()._map_offers(bad, QUERY) == []
    assert _adapter()._map_offers({}, QUERY) == []


def test_departure_date_synthesis():
    a = _adapter(days_ahead=30)
    # explicit full date passes through
    assert a._departure_date(SearchQuery("TLV", "LON", depart_date="2026-09-01")) == "2026-09-01"
    # flexible month -> mid-month
    assert a._departure_date(SearchQuery("TLV", "LON", depart_date="2026-09")) == "2026-09-15"
    # none -> a real future YYYY-MM-DD
    synth = a._departure_date(SearchQuery("TLV", "LON"))
    assert len(synth) == 10 and synth > datetime.now(timezone.utc).date().isoformat()
