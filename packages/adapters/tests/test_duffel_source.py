"""Offline tests for the Duffel adapter — pure vendor->canonical mapping.

No network: canned offer-request payloads are fed to the pure ``_map_offers``;
date synthesis is checked directly. (Live calls need a real DUFFEL_API_TOKEN.)
"""

from __future__ import annotations

from datetime import datetime, timezone

from packages.adapters.src.flights.duffel_source import SOURCE_NAME, DuffelFlightSource
from packages.domain.src import SearchQuery

QUERY = SearchQuery("TLV", "LON")

PAYLOAD = {
    "data": {
        "id": "orq_123",
        "offers": [
            {
                "total_amount": "312.40",
                "total_currency": "USD",
                "owner": {"iata_code": "BA", "name": "British Airways"},
                "slices": [
                    {
                        "segments": [
                            {
                                "departure_at": "2026-07-30T10:15:00",
                                "arrival_at": "2026-07-30T14:30:00",
                                "origin": {"iata_code": "TLV"},
                                "destination": {"iata_code": "LON"},
                                "marketing_carrier": {"iata_code": "BA", "name": "British Airways"},
                                "marketing_carrier_flight_number": "165",
                            }
                        ]
                    }
                ],
            }
        ],
    }
}


def _adapter(**opts):
    return DuffelFlightSource(
        base_url="https://api.duffel.com", currency="USD", api_key="duffel_test_x", options=opts
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
    assert "marker" not in o.booking_link  # Duffel is NOT the monetized source


def test_stops_counts_segments():
    multi = {
        "data": {
            "offers": [
                {
                    "total_amount": "200.00",
                    "total_currency": "USD",
                    "slices": [
                        {
                            "segments": [
                                {"departure_at": "2026-07-30T10:00:00", "marketing_carrier": {"iata_code": "LH"}, "flight_number": "1"},
                                {"departure_at": "2026-07-30T13:00:00", "marketing_carrier": {"iata_code": "LH"}, "flight_number": "2"},
                            ]
                        }
                    ],
                }
            ]
        }
    }
    assert _adapter()._map_offers(multi, QUERY)[0].stops == 1


def test_malformed_offers_are_skipped():
    bad = {"data": {"offers": [{"slices": []}, "nonsense", {"total_amount": "x"}]}}
    assert _adapter()._map_offers(bad, QUERY) == []
    assert _adapter()._map_offers({}, QUERY) == []


def test_departure_date_synthesis():
    a = _adapter(days_ahead=30)
    assert a._departure_date(SearchQuery("TLV", "LON", depart_date="2026-09-01")) == "2026-09-01"
    assert a._departure_date(SearchQuery("TLV", "LON", depart_date="2026-09")) == "2026-09-15"
    synth = a._departure_date(SearchQuery("TLV", "LON"))
    assert len(synth) == 10 and synth > datetime.now(timezone.utc).date().isoformat()
