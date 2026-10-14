"""Normalization of Kayak result cards onto FlightOffer / Itinerary / Segment.

The fixture holds the visible text of a few result cards; a stand-in page and
card replace playwright, so no browser is launched. (Overnight/12-hour edge
cases and logging are covered in ``farepy/tests``; this module covers the
page-to-offers path and the field mapping.)
"""

import pytest

from farepy.base import SearchRequest
from farepy.sources import kayak_source as kayak
from farepy.sources.kayak_source import KayakSource

ONE_WAY = SearchRequest(origin="MRS", destination="REK", departure_date="2026-04-18")
RETURN = SearchRequest(origin="MRS", destination="REK", departure_date="2026-04-18",
                       return_date="2026-04-25", currency="USD")


class _Element:
    def __init__(self, text):
        self._text = text

    def inner_text(self):
        return self._text


class _Card(_Element):
    def __init__(self, text, selectors=None):
        super().__init__(text)
        self._selectors = selectors or {}

    def query_selector(self, selector):
        text = self._selectors.get(selector)
        return _Element(text) if text is not None else None


class _Page:
    def __init__(self, cards):
        self._cards = cards

    def query_selector_all(self, selector):
        return self._cards if selector == "[data-resultid]" else []


@pytest.fixture
def cards(load_fixture):
    return load_fixture("kayak_cards.json")


def test_page_of_one_way_cards(cards):
    offers = kayak._extract_offers(_Page([_Card(t) for t in cards["one_way"]]), ONE_WAY)
    assert [o.price for o in offers] == [312.0, 89.0]  # the two non-offer cards are skipped

    first = offers[0]
    assert (first.source, first.currency, first.airlines) == ("kayak", "EUR", ["Icelandair"])
    assert first.inbound is None and first.booking_url is None
    (seg,) = first.outbound.segments
    assert (seg.departure_airport, seg.arrival_airport) == ("MRS", "REK")
    assert seg.departure_time == "2026-04-18T22:30:00"
    assert seg.arrival_time == "2026-04-19T06:15:00"
    assert seg.carrier == seg.carrier_name == "Icelandair"
    assert seg.duration_minutes == first.outbound.duration_minutes == 465
    assert first.raw["text"].startswith("Icelandair")


def test_return_card_builds_both_itineraries(cards):
    (offer,) = kayak._extract_offers(_Page([_Card(cards["return"][0])]), RETURN)
    assert offer.price == 1410.0 and offer.currency == "USD"
    out, inb = offer.outbound.segments[0], offer.inbound.segments[0]
    assert (out.departure_time, out.arrival_time) == ("2026-04-18T07:10:00", "2026-04-18T09:40:00")
    assert (inb.departure_airport, inb.arrival_airport) == ("REK", "MRS")
    assert (inb.departure_time, inb.arrival_time) == ("2026-04-25T13:00:00", "2026-04-26T21:05:00")
    assert (out.duration_minutes, inb.duration_minutes) == (150, 305)


def test_return_leg_ignored_for_a_one_way_request(cards):
    offer = kayak._parse_card(_Card(cards["return"][0]), ONE_WAY)
    assert offer.inbound is None


def test_selector_elements_take_precedence_over_text(cards):
    card = _Card(
        cards["one_way"][1],
        {'[class*="price-text"]': "€ 1,050", '[class*="codeshares"]': "  Vueling, Iberia "},
    )
    offer = kayak._parse_card(card, ONE_WAY)
    assert offer.price == 1050.0
    assert offer.airlines == ["Vueling, Iberia"]


def test_unknown_airline_falls_back_to_placeholder_carrier():
    offer = kayak._parse_card(_Card("07:10 – 09:40\n2h 30m\n€ 89"), ONE_WAY)
    assert offer.airlines == [] and offer.outbound.segments[0].carrier == "UNKNOWN"


@pytest.mark.parametrize(
    "text, stops",
    [("Nonstop", 0), ("direct", 0), ("1 stop", 1), ("2 stops", 2), ("", 0)],
)
def test_extract_stops(text, stops):
    assert kayak._extract_stops(None, text) == stops


def test_extract_duration_reads_every_leg():
    assert kayak._extract_duration(None, "2h 30m ... 11h ... 0h 45m") == [150, 660, 45]


def test_build_url():
    assert kayak._build_url(ONE_WAY) == "https://www.kayak.com/flights/MRS-REK/2026-04-18"
    assert kayak._build_url(RETURN).endswith("/MRS-REK/2026-04-18/2026-04-25")


def test_without_playwright_search_raises_and_nothing_launches():
    ok, msg = KayakSource().is_available()
    assert not ok and "playwright" in msg.lower()
    with pytest.raises(RuntimeError, match="Playwright not installed"):
        KayakSource().search(ONE_WAY)
