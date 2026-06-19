"""Amadeus Flight Offers Search adapter: the only place that knows Amadeus' OAuth2
flow, JSON shape, and URLs; maps the vendor response into canonical ``FlightOffer``s.
Amadeus returns no affiliate link, so we build a neutral Google Flights deep link.
Docs: https://developers.amadeus.com (Flight Offers Search v2)
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from packages.domain.src import FlightOffer, Money, SearchQuery

SOURCE_NAME = "amadeus"
_BOOKING_HOST = "https://www.google.com/travel/flights"


class AmadeusFlightSource:
    """Concrete ``FlightSource`` backed by the Amadeus Flight Offers Search API."""

    def __init__(
        self,
        *,
        base_url: str,
        currency: str = "USD",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.currency = (currency or "USD").upper()
        self.api_key = api_key
        self.api_secret = api_secret
        self.options = dict(options or {})
        self.timeout_seconds = int(self.options.get("timeout_seconds", 20))
        self.days_ahead = int(self.options.get("days_ahead", 30))
        self.max_offers = int(self.options.get("max_offers", 5))
        self._token: Optional[str] = None
        self._token_expiry = datetime.min.replace(tzinfo=timezone.utc)

    # ── public contract ─────────────────────────────────────────────────────

    def search(self, query: SearchQuery) -> list[FlightOffer]:
        payload = self._fetch_offers(query)
        return self._map_offers(payload, query)

    # ── vendor I/O (network) ────────────────────────────────────────────────

    def _access_token(self) -> str:
        now = datetime.now(timezone.utc)
        if self._token and now < self._token_expiry:
            return self._token
        if not self.api_key or not self.api_secret:
            raise RuntimeError(
                "Amadeus credentials missing (set AMADEUS_API_KEY and "
                "AMADEUS_API_SECRET in .env)."
            )
        body = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.api_secret,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/v1/security/oauth2/token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        self._token = str(data["access_token"])
        self._token_expiry = now + timedelta(seconds=int(data.get("expires_in", 1800)) - 60)
        return self._token

    def _fetch_offers(self, query: SearchQuery) -> dict[str, Any]:
        params = {
            "originLocationCode": query.origin,
            "destinationLocationCode": query.destination,
            "departureDate": self._departure_date(query),
            "adults": "1",
            "currencyCode": (query.currency or self.currency).upper(),
            "max": str(self.max_offers),
        }
        url = f"{self.base_url}/v2/shopping/flight-offers?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {self._access_token()}"}
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _departure_date(self, query: SearchQuery) -> str:
        d = (query.depart_date or "").strip()
        if len(d) == 10:  # YYYY-MM-DD
            return d
        if len(d) == 7:  # YYYY-MM (flexible month) -> mid-month
            return f"{d}-15"
        future = datetime.now(timezone.utc).date() + timedelta(days=self.days_ahead)
        return future.isoformat()

    # ── vendor -> canonical mapping (pure, offline-testable) ─────────────────

    def _map_offers(self, payload: dict[str, Any], query: SearchQuery) -> list[FlightOffer]:
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        if not isinstance(data, list):
            return []

        currency = (query.currency or self.currency).upper()
        offers = (self._map_single_offer(raw, query, currency) for raw in data)
        return [o for o in offers if o is not None]

    def _map_single_offer(
        self, raw: Any, query: SearchQuery, currency: str
    ) -> Optional[FlightOffer]:
        if not isinstance(raw, dict):
            return None
        try:
            itineraries = raw["itineraries"]
            segments = itineraries[0]["segments"]
            first, last = segments[0], segments[-1]
            price_total = float(raw["price"]["total"])
        except (KeyError, IndexError, TypeError, ValueError):
            return None

        departure_at = _parse_utc(first.get("departure", {}).get("at"))
        if departure_at is None:
            return None

        offer_currency = (raw.get("price", {}).get("currency") or currency).upper()
        airline = _clean_code(first.get("carrierCode"))
        number = first.get("number")
        flight_number = f"{airline}{number}" if airline and number else None

        return FlightOffer(
            origin=query.origin,
            destination=query.destination,
            departure_at=departure_at,
            price=Money(amount=price_total, currency=offer_currency),
            booking_link=self._build_booking_link(query, departure_at),
            source=SOURCE_NAME,
            return_at=_parse_utc(last.get("arrival", {}).get("at")) if len(segments) > 1 else None,
            airline=airline,
            flight_number=flight_number,
            stops=len(segments) - 1,
            observed_at=None,
            expires_at=None,
        )

    def _build_booking_link(self, query: SearchQuery, departure_at: datetime) -> str:
        # Neutral (non-affiliate) Google Flights search link.
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


__all__ = ["AmadeusFlightSource", "SOURCE_NAME"]
