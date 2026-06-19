"""Duffel Flights API adapter.

The only place that knows Duffel's JSON shape, auth, and URL conventions; maps the
vendor response into canonical ``FlightOffer``s. Auth is a single static bearer
token (``DUFFEL_API_TOKEN``) — no OAuth exchange. Search is one POST to
``/air/offer_requests?return_offers=true`` (requires a departure date, synthesized
``days_ahead`` out when the query has none). Duffel returns no affiliate link, so we
build a neutral Google Flights deep link (monetization stays with Travelpayouts).

Docs: https://duffel.com/docs/api (Offer Requests, ``Duffel-Version: v2``)
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from packages.domain.src import FlightOffer, Money, SearchQuery

SOURCE_NAME = "duffel"
_BOOKING_HOST = "https://www.google.com/travel/flights"


class DuffelFlightSource:
    """Concrete ``FlightSource`` backed by the Duffel Offer Requests API."""

    def __init__(
        self,
        *,
        base_url: str,
        currency: str = "USD",
        api_key: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.currency = (currency or "USD").upper()
        self.api_key = api_key  # Duffel bearer token (duffel_test_… / duffel_live_…)
        self.options = dict(options or {})
        self.timeout_seconds = int(self.options.get("timeout_seconds", 30))
        self.days_ahead = int(self.options.get("days_ahead", 30))

    # ── public contract ─────────────────────────────────────────────────────

    def search(self, query: SearchQuery) -> list[FlightOffer]:
        return self._map_offers(self._fetch_offers(query), query)

    # ── vendor I/O (network) ────────────────────────────────────────────────

    def _fetch_offers(self, query: SearchQuery) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("Duffel token missing (set DUFFEL_API_TOKEN in .env).")
        body = json.dumps(
            {
                "data": {
                    "slices": [
                        {
                            "origin": query.origin,
                            "destination": query.destination,
                            "departure_date": self._departure_date(query),
                        }
                    ],
                    "passengers": [{"type": "adult"}],
                    "cabin_class": "economy",
                }
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/air/offer_requests?return_offers=true",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Duffel-Version": "v2",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _departure_date(self, query: SearchQuery) -> str:
        d = (query.depart_date or "").strip()
        if len(d) == 10:  # YYYY-MM-DD
            return d
        if len(d) == 7:  # YYYY-MM (flexible month) -> mid-month
            return f"{d}-15"
        return (datetime.now(timezone.utc).date() + timedelta(days=self.days_ahead)).isoformat()

    # ── vendor -> canonical mapping (pure, offline-testable) ─────────────────

    def _map_offers(self, payload: dict[str, Any], query: SearchQuery) -> list[FlightOffer]:
        data = payload.get("data") if isinstance(payload, dict) else None
        offers = data.get("offers") if isinstance(data, dict) else None
        if not isinstance(offers, list):
            return []
        mapped = (self._map_single_offer(o, query) for o in offers)
        return [o for o in mapped if o is not None]

    def _map_single_offer(self, raw: Any, query: SearchQuery) -> Optional[FlightOffer]:
        if not isinstance(raw, dict):
            return None
        try:
            segments = raw["slices"][0]["segments"]
            first = segments[0]
            amount = float(raw["total_amount"])
        except (KeyError, IndexError, TypeError, ValueError):
            return None

        departure_at = _parse_utc(first.get("departure_at"))
        if departure_at is None:
            return None

        currency = (raw.get("total_currency") or query.currency or self.currency).upper()
        carrier = first.get("marketing_carrier") or raw.get("owner") or {}
        airline = _clean_code(carrier.get("iata_code"))
        number = first.get("marketing_carrier_flight_number") or first.get("flight_number")
        flight_number = f"{airline}{number}" if airline and number else None

        return FlightOffer(
            origin=query.origin,
            destination=query.destination,
            departure_at=departure_at,
            price=Money(amount=amount, currency=currency),
            booking_link=self._build_booking_link(query, departure_at),
            source=SOURCE_NAME,
            return_at=None,
            airline=airline,
            flight_number=flight_number,
            stops=len(segments) - 1,
            observed_at=None,
            expires_at=None,
        )

    def _build_booking_link(self, query: SearchQuery, departure_at: datetime) -> str:
        q = f"Flights from {query.origin} to {query.destination} on {departure_at.date().isoformat()}"
        return f"{_BOOKING_HOST}?" + urllib.parse.urlencode({"q": q})


def _parse_utc(value: Any) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _clean_code(value: Any) -> Optional[str]:
    if value is None:
        return None
    code = str(value).strip().upper()
    return code or None


__all__ = ["DuffelFlightSource", "SOURCE_NAME"]
