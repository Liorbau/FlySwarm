"""Travelpayouts (Aviasales) Data Access API adapter: the only place that knows the
vendor JSON shape, field names, auth header, and URLs; maps responses into canonical
``FlightOffer``s. Booking links are affiliate Aviasales URLs built from the partner
``marker``, since the Data API returns no link.
Docs: https://api.travelpayouts.com/documentation
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional

from packages.domain.src import FlightOffer, Money, SearchQuery

SOURCE_NAME = "travelpayouts"
_BOOKING_HOST = "https://www.aviasales.com/search"


class TravelpayoutsFlightSource:
    """Concrete ``FlightSource`` backed by the Travelpayouts Data Access API."""

    def __init__(
        self,
        *,
        base_url: str,
        currency: str = "USD",
        api_key: Optional[str] = None,
        marker: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.currency = (currency or "USD").upper()
        self.api_key = api_key
        self.marker = marker
        self.options = dict(options or {})
        self.timeout_seconds = int(self.options.get("timeout_seconds", 20))

    # ── public contract ─────────────────────────────────────────────────────

    def search(self, query: SearchQuery) -> list[FlightOffer]:
        payload = self._fetch_cheap(query)
        return self._map_cheap_response(payload, query)

    # ── vendor I/O (network) ────────────────────────────────────────────────

    def _fetch_cheap(self, query: SearchQuery) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError(
                "Travelpayouts API key missing (set TRAVELPAYOUTS_API_KEY in .env)."
            )

        params: dict[str, str] = {
            "origin": query.origin,
            "destination": query.destination,
            "currency": (query.currency or self.currency).lower(),
        }
        if query.depart_date:
            params["depart_date"] = query.depart_date
        if query.return_date:
            params["return_date"] = query.return_date

        url = f"{self.base_url}/v1/prices/cheap?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"X-Access-Token": self.api_key})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw)

    # ── vendor -> canonical mapping (pure, offline-testable) ─────────────────

    def _map_cheap_response(
        self, payload: dict[str, Any], query: SearchQuery
    ) -> list[FlightOffer]:
        if not isinstance(payload, dict) or not payload.get("success", False):
            return []
        data = payload.get("data")
        if not isinstance(data, dict):
            return []
        currency = (query.currency or self.currency).upper()
        offers: list[FlightOffer] = []

        # Shape: data[<destination IATA>][<index>] = { price, airline, ... }
        for destination, by_index in data.items():
            if not isinstance(by_index, dict):
                continue
            for raw_offer in by_index.values():
                offer = self._map_single_offer(
                    raw_offer=raw_offer,
                    origin=query.origin,
                    destination=str(destination).upper(),
                    currency=currency,
                )
                if offer is not None:
                    offers.append(offer)
        return offers

    def _map_single_offer(
        self, *, raw_offer: Any, origin: str, destination: str, currency: str
    ) -> Optional[FlightOffer]:
        if not isinstance(raw_offer, dict):
            return None

        departure_at = _parse_utc(raw_offer.get("departure_at"))
        price_value = raw_offer.get("price")
        if departure_at is None or price_value is None:
            return None  # required canonical facts missing -> skip

        return_at = _parse_utc(raw_offer.get("return_at"))
        airline = _clean_code(raw_offer.get("airline"))
        flight_number = raw_offer.get("flight_number")
        flight_number = str(flight_number) if flight_number is not None else None

        return FlightOffer(
            origin=origin,
            destination=destination,
            departure_at=departure_at,
            price=Money(amount=float(price_value), currency=currency),
            booking_link=self._build_booking_link(
                origin=origin,
                destination=destination,
                departure_at=departure_at,
                return_at=return_at,
            ),
            source=SOURCE_NAME,
            return_at=return_at,
            airline=airline,
            flight_number=flight_number,
            # `v1/prices/cheap` does not expose a transfer count -> unknown.
            stops=None,
            observed_at=None,
            expires_at=_parse_utc(raw_offer.get("expires_at")),
        )

    # ── affiliate deep link ─────────────────────────────────────────────────

    def _build_booking_link(
        self, *, origin: str, destination: str,
        departure_at: datetime, return_at: Optional[datetime],
    ) -> str:
        # Aviasales search slug: ORIGIN + DDMM + DEST [+ DDMM] + passengers.
        slug = f"{origin}{departure_at.strftime('%d%m')}{destination}"
        if return_at is not None:
            slug += return_at.strftime("%d%m")
        slug += "1"  # one adult passenger

        url = f"{_BOOKING_HOST}/{slug}"
        if self.marker:
            url += f"?{urllib.parse.urlencode({'marker': self.marker})}"
        return url


def _parse_utc(value: Any) -> Optional[datetime]:
    """Parse an ISO 8601 string into a timezone-aware UTC datetime."""
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


__all__ = ["TravelpayoutsFlightSource", "SOURCE_NAME"]
