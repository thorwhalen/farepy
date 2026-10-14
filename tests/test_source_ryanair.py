"""Normalization of ryanair-py fares onto FlightOffer / Itinerary / Segment.

The fixture mirrors the attribute shape of ryanair-py's ``Flight`` and
``Trip``; a fake ``ryanair`` module stands in for the library, so nothing is
fetched.
"""

import sys
import types
from datetime import datetime

import pytest

from farepy.base import FlightOffer, SearchRequest
from farepy.sources import ryanair_source
from farepy.sources.ryanair_source import RyanairSource


def _flight(d):
    return types.SimpleNamespace(**{**d, "departureTime": datetime.fromisoformat(d["departureTime"])})


@pytest.fixture
def fares(load_fixture):
    raw = load_fixture("ryanair_fares.json")
    one_way = [_flight(f) for f in raw["one_way"]]
    trips = [
        types.SimpleNamespace(
            totalPrice=t["totalPrice"], outbound=_flight(t["outbound"]), inbound=_flight(t["inbound"])
        )
        for t in raw["return"]
    ]
    return one_way, trips


@pytest.fixture
def fake_ryanair(monkeypatch, fares):
    one_way, trips = fares
    calls = []

    class Ryanair:
        def __init__(self, currency):
            calls.append(("init", currency))

        def get_cheapest_flights(self, **kwargs):
            calls.append(("one_way", kwargs))
            return one_way

        def get_cheapest_return_flights(self, **kwargs):
            calls.append(("return", kwargs))
            return trips

    module = types.ModuleType("ryanair")
    module.Ryanair = Ryanair
    monkeypatch.setitem(sys.modules, "ryanair", module)
    return calls


def test_one_way_flight_normalization(fares):
    flight = fares[0][0]
    offer = ryanair_source._convert_flight(flight)
    assert isinstance(offer, FlightOffer)
    assert (offer.source, offer.price, offer.currency, offer.airlines) == ("ryanair", 39.99, "EUR", ["FR"])
    assert offer.inbound is None
    (seg,) = offer.outbound.segments
    assert (seg.departure_airport, seg.arrival_airport) == ("MRS", "DUB")
    assert seg.departure_time == "2026-04-18T06:30:00"
    assert seg.arrival_time == ""  # the fare finder does not report arrivals
    assert (seg.carrier, seg.carrier_name, seg.flight_number) == ("FR", "Ryanair", "FR1234")
    assert offer.outbound.stops == 0


def test_return_trip_normalization(fares):
    offer = ryanair_source._convert_trip(fares[1][0])
    assert offer.price == 81.48 and offer.currency == "EUR"
    out, inb = offer.outbound.segments[0], offer.inbound.segments[0]
    assert (out.departure_airport, out.flight_number) == ("MRS", "FR1234")
    assert (inb.departure_airport, inb.arrival_airport) == ("DUB", "MRS")
    assert inb.departure_time == "2026-04-25T21:10:00"
    assert offer.inbound.departure_airport == "DUB"


def test_search_one_way_queries_the_fare_finder_and_converts(fake_ryanair):
    req = SearchRequest(origin="MRS", destination="DUB", departure_date="2026-04-18", currency="GBP")
    offers = RyanairSource().search(req)
    assert [o.price for o in offers] == [39.99, 24.5]
    assert fake_ryanair[0] == ("init", "GBP")
    kind, kwargs = fake_ryanair[1]
    assert kind == "one_way"
    assert kwargs == dict(airport="MRS", date_from="2026-04-18", date_to="2026-04-18",
                          destination_airport="DUB")


def test_search_return_uses_the_return_endpoint(fake_ryanair):
    req = SearchRequest(origin="MRS", destination="DUB", departure_date="2026-04-18",
                        return_date="2026-04-25")
    (offer,) = RyanairSource().search(req)
    assert offer.inbound is not None
    kind, kwargs = fake_ryanair[1]
    assert kind == "return"
    assert kwargs["return_date_from"] == kwargs["return_date_to"] == "2026-04-25"


def test_is_available_reflects_the_library(fake_ryanair, monkeypatch):
    assert RyanairSource().is_available()[0] is True
    monkeypatch.setitem(sys.modules, "ryanair", None)
    ok, msg = RyanairSource().is_available()
    assert not ok and "pip install ryanair-py" in msg
