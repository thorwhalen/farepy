"""Normalized data model for multi-source flight search."""

from dataclasses import dataclass, field, asdict
from typing import Protocol


@dataclass
class Segment:
    """A single flight leg (one takeoff-to-landing)."""

    departure_airport: str  # IATA code, e.g. "MRS"
    arrival_airport: str  # IATA code, e.g. "REK"
    departure_time: str  # ISO 8601: "2026-04-18T06:30:00"
    arrival_time: str  # ISO 8601: "2026-04-18T10:45:00"
    carrier: str  # Airline IATA code, e.g. "FI"
    carrier_name: str | None = None  # Full name if available
    flight_number: str | None = None  # e.g. "FI543"
    duration_minutes: int | None = None
    aircraft: str | None = None


@dataclass
class Itinerary:
    """One direction of travel (outbound or return)."""

    segments: list[Segment]
    duration_minutes: int | None = None  # Total itinerary duration

    @property
    def departure_time(self) -> str:
        return self.segments[0].departure_time

    @property
    def arrival_time(self) -> str:
        return self.segments[-1].arrival_time

    @property
    def departure_airport(self) -> str:
        return self.segments[0].departure_airport

    @property
    def arrival_airport(self) -> str:
        return self.segments[-1].arrival_airport

    @property
    def stops(self) -> int:
        return len(self.segments) - 1


@dataclass
class FlightOffer:
    """A single bookable flight option, normalized across all sources."""

    source: str  # "google_flights" | "ryanair" | "kayak"
    outbound: Itinerary
    price: float
    currency: str
    airlines: list[str]  # Unique carrier codes across all segments
    inbound: Itinerary | None = None  # None for one-way
    booking_url: str | None = None
    raw: dict | None = field(default=None, repr=False)


@dataclass
class SearchRequest:
    """Normalized search parameters."""

    origin: str  # IATA code
    destination: str  # IATA code
    departure_date: str  # YYYY-MM-DD
    return_date: str | None = None
    adults: int = 1
    currency: str = "EUR"
    max_results: int = 50
    non_stop: bool | None = None
    # Time range filters (HH:MM format)
    outbound_departure_after: str | None = None
    outbound_departure_before: str | None = None
    outbound_arrival_after: str | None = None
    outbound_arrival_before: str | None = None
    inbound_departure_after: str | None = None
    inbound_departure_before: str | None = None
    inbound_arrival_after: str | None = None
    inbound_arrival_before: str | None = None


@dataclass
class SearchResult:
    """Container for search results with metadata."""

    request: SearchRequest
    offers: list[FlightOffer]
    sources_queried: list[str]
    sources_failed: dict[str, str]  # source -> error message
    searched_at: str  # ISO 8601 timestamp
    cached: bool = False


class FlightSource(Protocol):
    """Protocol that all source adapters implement."""

    name: str

    def search(self, request: SearchRequest) -> list[FlightOffer]:
        """Search for flights. Returns empty list on no results."""
        ...

    def is_available(self) -> tuple[bool, str]:
        """Check availability. Returns (available, message)."""
        ...
