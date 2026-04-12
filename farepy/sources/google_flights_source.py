"""Google Flights source via the fast-flights library.

Uses reverse-engineered Protobuf encoding to query Google Flights directly
via HTTP -- no browser automation needed. Covers virtually all European LCCs
including Ryanair, easyJet, Wizz Air, Vueling, Transavia, and more.

Install: pip install fast-flights
"""

import re
from datetime import datetime, timedelta

from farepy.base import FlightOffer, Itinerary, SearchRequest, Segment


class GoogleFlightsSource:
    name = "google_flights"

    def __init__(self, **_kwargs):
        pass

    def is_available(self) -> tuple[bool, str]:
        try:
            import fast_flights  # noqa: F401

            return True, "Google Flights source ready (via fast-flights)."
        except ImportError:
            return False, "fast-flights not installed. Run: pip install fast-flights"

    def search(self, request: SearchRequest) -> list[FlightOffer]:
        from fast_flights import (
            FlightData,
            Passengers,
            create_filter,
            get_flights_from_filter,
        )

        flight_data = [
            FlightData(
                date=request.departure_date,
                from_airport=request.origin,
                to_airport=request.destination,
            )
        ]

        trip = "one-way"
        if request.return_date:
            trip = "round-trip"
            flight_data.append(
                FlightData(
                    date=request.return_date,
                    from_airport=request.destination,
                    to_airport=request.origin,
                )
            )

        max_stops = 0 if request.non_stop else None

        filt = create_filter(
            flight_data=flight_data,
            trip=trip,
            passengers=Passengers(adults=request.adults),
            seat="economy",
            max_stops=max_stops,
        )

        result = get_flights_from_filter(
            filter=filt,
            currency=request.currency or "",
        )

        offers = []
        for flight in result.flights:
            offer = _convert_flight(flight, request)
            if offer is not None:
                offers.append(offer)

        return offers


def _convert_flight(flight, request: SearchRequest) -> FlightOffer | None:
    """Convert a fast-flights Flight object to a normalized FlightOffer."""
    price = _parse_price(flight.price)
    if price is None:
        return None

    dep_time_24h = _parse_12h_time(flight.departure)
    arr_time_24h = _parse_12h_time(flight.arrival)

    dep_dt = f"{request.departure_date}T{dep_time_24h}:00" if dep_time_24h else ""

    # Handle next-day arrival (arrival_time_ahead like "+1")
    arr_date = request.departure_date
    if flight.arrival_time_ahead and "+" in flight.arrival_time_ahead:
        try:
            days_ahead = int(flight.arrival_time_ahead.replace("+", "").strip())
            base = datetime.strptime(request.departure_date, "%Y-%m-%d")
            arr_date = (base + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass

    arr_dt = f"{arr_date}T{arr_time_24h}:00" if arr_time_24h else ""

    duration = _parse_duration(flight.duration)
    stops = flight.stops if isinstance(flight.stops, int) else 0

    # Use first airline name as carrier; full list goes in FlightOffer.airlines
    first_airline = flight.name.split(",")[0].strip() if flight.name else "Unknown"

    outbound = Itinerary(
        segments=[
            Segment(
                departure_airport=request.origin,
                arrival_airport=request.destination,
                departure_time=dep_dt,
                arrival_time=arr_dt,
                carrier=first_airline,
                carrier_name=first_airline,
                duration_minutes=duration,
            )
        ],
        duration_minutes=duration,
    )

    airlines = (
        [a.strip() for a in flight.name.split(",") if a.strip()] if flight.name else []
    )

    return FlightOffer(
        source="google_flights",
        outbound=outbound,
        price=price,
        currency=request.currency,
        airlines=airlines,
        raw={
            "is_best": flight.is_best,
            "stops": stops,
            "delay": flight.delay,
            "arrival_time_ahead": flight.arrival_time_ahead,
        },
    )


def _parse_price(price_str: str) -> float | None:
    """Parse a price string like '$342' or '€1,234' to a float.

    >>> _parse_price('$342')
    342.0
    >>> _parse_price('€1,234')
    1234.0
    >>> _parse_price('')
    """
    if not price_str:
        return None
    cleaned = re.sub(r"[^\d.]", "", price_str.replace(",", ""))
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_12h_time(time_str: str) -> str:
    """Extract and parse a 12-hour time to 24-hour HH:MM format.

    Handles both bare times and Google Flights format with date context
    like '6:55 PM on Wed, Jul 1'.

    >>> _parse_12h_time('8:00 AM')
    '08:00'
    >>> _parse_12h_time('1:30 PM')
    '13:30'
    >>> _parse_12h_time('12:00 AM')
    '00:00'
    >>> _parse_12h_time('12:45 PM')
    '12:45'
    >>> _parse_12h_time('6:55 PM on Wed, Jul 1')
    '18:55'
    """
    if not time_str:
        return ""
    # Extract the H:MM AM/PM portion from the string
    m = re.search(r"(\d{1,2}:\d{2})\s*(AM|PM|am|pm)", time_str)
    if m:
        try:
            dt = datetime.strptime(f"{m.group(1)} {m.group(2).upper()}", "%I:%M %p")
            return dt.strftime("%H:%M")
        except ValueError:
            pass
    # Fallback: try as 24-hour format
    m = re.search(r"(\d{1,2}:\d{2})", time_str)
    if m:
        return m.group(1).zfill(5)
    return ""


def _parse_duration(duration_str: str) -> int | None:
    """Parse a duration string like '5 hr 30 min' to total minutes.

    >>> _parse_duration('5 hr 30 min')
    330
    >>> _parse_duration('2 hr')
    120
    >>> _parse_duration('45 min')
    45
    """
    if not duration_str:
        return None
    hours_match = re.search(r"(\d+)\s*h", duration_str)
    mins_match = re.search(r"(\d+)\s*m", duration_str)
    hours = int(hours_match.group(1)) if hours_match else 0
    minutes = int(mins_match.group(1)) if mins_match else 0
    total = hours * 60 + minutes
    return total if total > 0 else None
