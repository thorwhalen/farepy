"""Normalization of fast-flights results onto FlightOffer / Itinerary / Segment.

The fixture mirrors the attribute shape of fast-flights' ``Flight``; a fake
``fast_flights`` module stands in for the library, so nothing is fetched.
"""

import sys
import types

import pytest

from farepy.base import SearchRequest
from farepy.sources import google_flights_source as gf
from farepy.sources.google_flights_source import GoogleFlightsSource

REQUEST = SearchRequest(origin="MRS", destination="REK", departure_date="2026-04-18")


@pytest.fixture
def flights(load_fixture):
    return [types.SimpleNamespace(**f) for f in load_fixture("google_flights_result.json")["flights"]]


@pytest.fixture
def fake_fast_flights(monkeypatch, flights):
    calls = {}

    def FlightData(**kw):
        return ("FlightData", kw)

    def Passengers(**kw):
        return ("Passengers", kw)

    def create_filter(**kw):
        calls["filter"] = kw
        return "the-filter"

    def get_flights_from_filter(**kw):
        calls["fetch"] = kw
        return types.SimpleNamespace(flights=flights)

    module = types.ModuleType("fast_flights")
    for fn in (FlightData, Passengers, create_filter, get_flights_from_filter):
        setattr(module, fn.__name__, fn)
    monkeypatch.setitem(sys.modules, "fast_flights", module)
    return calls


def test_overnight_multi_airline_flight(flights):
    offer = gf._convert_flight(flights[0], REQUEST)
    assert (offer.source, offer.price, offer.currency) == ("google_flights", 1234.0, "EUR")
    assert offer.airlines == ["Icelandair", "Lufthansa"]
    (seg,) = offer.outbound.segments
    assert (seg.departure_airport, seg.arrival_airport) == ("MRS", "REK")
    assert seg.departure_time == "2026-04-18T22:30:00"
    assert seg.arrival_time == "2026-04-19T06:15:00"  # "+1" moves the date
    assert seg.carrier == seg.carrier_name == "Icelandair"
    assert seg.duration_minutes == offer.outbound.duration_minutes == 465
    assert offer.raw == {"is_best": True, "stops": 1, "delay": None, "arrival_time_ahead": "+1"}
    assert offer.inbound is None


def test_same_day_direct_flight(flights):
    offer = gf._convert_flight(flights[1], REQUEST)
    seg = offer.outbound.segments[0]
    assert offer.price == 89.0 and offer.airlines == ["easyJet"]
    assert (seg.departure_time, seg.arrival_time) == ("2026-04-18T08:05:00", "2026-04-18T11:40:00")
    assert seg.duration_minutes == 215
    assert offer.raw["stops"] == 0


def test_unpriced_flight_is_dropped(flights):
    assert gf._convert_flight(flights[2], REQUEST) is None


def test_non_integer_stops_default_to_zero(flights):
    flight = types.SimpleNamespace(**{**vars(flights[2]), "price": "€50"})
    assert gf._convert_flight(flight, REQUEST).raw["stops"] == 0


def test_missing_name_yields_unknown_carrier(flights):
    flight = types.SimpleNamespace(**{**vars(flights[1]), "name": ""})
    offer = gf._convert_flight(flight, REQUEST)
    assert offer.airlines == [] and offer.outbound.segments[0].carrier == "Unknown"


def test_search_one_way_builds_the_filter_and_drops_unpriced(fake_fast_flights):
    offers = GoogleFlightsSource().search(REQUEST)
    assert [o.price for o in offers] == [1234.0, 89.0]
    filt = fake_fast_flights["filter"]
    assert filt["trip"] == "one-way"
    assert len(filt["flight_data"]) == 1
    assert filt["max_stops"] is None
    assert filt["passengers"] == ("Passengers", {"adults": 1})
    assert fake_fast_flights["fetch"] == {"filter": "the-filter", "currency": "EUR"}


def test_search_round_trip_non_stop(fake_fast_flights):
    req = SearchRequest(origin="MRS", destination="REK", departure_date="2026-04-18",
                        return_date="2026-04-30", non_stop=True, adults=2)
    GoogleFlightsSource().search(req)
    filt = fake_fast_flights["filter"]
    assert filt["trip"] == "round-trip" and filt["max_stops"] == 0
    back = filt["flight_data"][1][1]
    assert back == {"date": "2026-04-30", "from_airport": "REK", "to_airport": "MRS"}


def test_is_available_reflects_the_library(fake_fast_flights, monkeypatch):
    assert GoogleFlightsSource().is_available()[0] is True
    monkeypatch.setitem(sys.modules, "fast_flights", None)
    ok, msg = GoogleFlightsSource().is_available()
    assert not ok and "pip install fast-flights" in msg
