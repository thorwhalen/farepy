"""Ryanair source via the ryanair-py library.

Queries Ryanair's fare finder API directly (no browser automation).
Returns cheapest fares per route with flight numbers and departure times.
Arrival times are not available from the fare finder endpoint.

Install: pip install ryanair-py
"""

from farepy.base import FlightOffer, Itinerary, SearchRequest, Segment


class RyanairSource:
    name = "ryanair"

    def __init__(self, **_kwargs):
        pass

    def is_available(self) -> tuple[bool, str]:
        try:
            from ryanair import Ryanair  # noqa: F401

            return True, "Ryanair source ready (via ryanair-py)."
        except ImportError:
            return False, "ryanair-py not installed. Run: pip install ryanair-py"

    def search(self, request: SearchRequest) -> list[FlightOffer]:
        from ryanair import Ryanair

        api = Ryanair(currency=request.currency)

        if request.return_date:
            trips = api.get_cheapest_return_flights(
                source_airport=request.origin,
                date_from=request.departure_date,
                date_to=request.departure_date,
                return_date_from=request.return_date,
                return_date_to=request.return_date,
                destination_airport=request.destination,
            )
            return [_convert_trip(trip) for trip in trips]
        else:
            flights = api.get_cheapest_flights(
                airport=request.origin,
                date_from=request.departure_date,
                date_to=request.departure_date,
                destination_airport=request.destination,
            )
            return [_convert_flight(flight) for flight in flights]


def _convert_flight(flight) -> FlightOffer:
    """Convert a ryanair-py Flight to a normalized FlightOffer."""
    dep_time = flight.departureTime.strftime("%Y-%m-%dT%H:%M:%S")

    outbound = Itinerary(
        segments=[
            Segment(
                departure_airport=flight.origin,
                arrival_airport=flight.destination,
                departure_time=dep_time,
                arrival_time="",  # Not available from fare finder API
                carrier="FR",
                carrier_name="Ryanair",
                flight_number=flight.flightNumber,
            )
        ],
    )

    return FlightOffer(
        source="ryanair",
        outbound=outbound,
        price=flight.price,
        currency=flight.currency,
        airlines=["FR"],
    )


def _convert_trip(trip) -> FlightOffer:
    """Convert a ryanair-py Trip to a normalized FlightOffer."""
    out_time = trip.outbound.departureTime.strftime("%Y-%m-%dT%H:%M:%S")
    in_time = trip.inbound.departureTime.strftime("%Y-%m-%dT%H:%M:%S")

    outbound = Itinerary(
        segments=[
            Segment(
                departure_airport=trip.outbound.origin,
                arrival_airport=trip.outbound.destination,
                departure_time=out_time,
                arrival_time="",  # Not available from fare finder API
                carrier="FR",
                carrier_name="Ryanair",
                flight_number=trip.outbound.flightNumber,
            )
        ],
    )

    inbound = Itinerary(
        segments=[
            Segment(
                departure_airport=trip.inbound.origin,
                arrival_airport=trip.inbound.destination,
                departure_time=in_time,
                arrival_time="",  # Not available from fare finder API
                carrier="FR",
                carrier_name="Ryanair",
                flight_number=trip.inbound.flightNumber,
            )
        ],
    )

    return FlightOffer(
        source="ryanair",
        outbound=outbound,
        inbound=inbound,
        price=trip.totalPrice,
        currency=trip.outbound.currency,
        airlines=["FR"],
    )
