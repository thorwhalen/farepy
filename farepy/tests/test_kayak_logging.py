"""The Kayak scraper says when it swallows failures (thorwhalen/farepy#1).

No browser and no network: ``_extract_offers`` is driven with a stand-in page,
and ``_parse_card`` is replaced to fail on chosen cards.
"""

import logging

from farepy.base import SearchRequest
from farepy.sources import kayak_source

REQUEST = SearchRequest(origin="MRS", destination="REK", departure_date="2026-04-18")


class _Page:
    def __init__(self, cards):
        self._cards = cards

    def query_selector_all(self, selector):
        return self._cards if selector == "[data-resultid]" else []


def test_unparseable_cards_are_counted_in_a_warning(monkeypatch, caplog):
    def parse(card, request):
        if card == "bad":
            raise ValueError("selector drift")
        return f"offer-{card}"

    monkeypatch.setattr(kayak_source, "_parse_card", parse)
    with caplog.at_level(logging.DEBUG, logger=kayak_source.__name__):
        offers = kayak_source._extract_offers(_Page(["a", "bad", "bad"]), REQUEST)
    assert offers == ["offer-a"]
    (warning,) = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert "2 of 3 result cards could not be parsed" in warning.getMessage()
    debug = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug) == 2 and all(r.exc_info for r in debug)


def test_no_cards_at_all_is_a_warning_not_silence(caplog):
    with caplog.at_level(logging.WARNING, logger=kayak_source.__name__):
        assert kayak_source._extract_offers(_Page([]), REQUEST) == []
    assert "no result cards matched" in caplog.text


def test_a_clean_page_logs_no_warning(monkeypatch, caplog):
    monkeypatch.setattr(kayak_source, "_parse_card", lambda card, request: card)
    with caplog.at_level(logging.WARNING, logger=kayak_source.__name__):
        assert kayak_source._extract_offers(_Page(["a", "b"]), REQUEST) == ["a", "b"]
    assert not caplog.records
