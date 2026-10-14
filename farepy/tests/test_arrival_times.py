"""Arrival times that are unknown or land the next day (thorwhalen/farepy#6).

No browser and no network: the filter is fed offer dicts, the Kayak parser
is fed a stand-in card, and playwright is replaced in ``is_available``.
"""

import sys
import types

from farepy.base import SearchRequest
from farepy.core import _apply_time_filters
from farepy.sources import kayak_source


def _offer(dep, arr):
    seg = {"departure_time": dep, "arrival_time": arr}
    return {"outbound": {"segments": [seg]}, "inbound": None}


# --- 1. an unknown arrival time cannot be filtered on ---------------------------


def test_unknown_arrival_is_kept_under_an_arrival_filter():
    """Ryanair emits arrival_time="" — it used to drop every Ryanair offer."""
    request = SearchRequest(
        origin="MRS", destination="DUB", departure_date="2026-04-18",
        outbound_arrival_after="08:00", outbound_arrival_before="18:00",
    )
    ryanair = _offer("2026-04-18T06:30:00", "")
    too_early = _offer("2026-04-18T05:00:00", "2026-04-18T07:00:00")
    in_range = _offer("2026-04-18T07:00:00", "2026-04-18T09:00:00")
    assert _apply_time_filters([ryanair, too_early, in_range], request) == [ryanair, in_range]


def test_a_known_time_is_still_filtered():
    request = SearchRequest(
        origin="MRS", destination="DUB", departure_date="2026-04-18",
        outbound_departure_after="08:00",
    )
    assert _apply_time_filters([_offer("2026-04-18T06:30:00", "")], request) == []


# --- 2. Kayak: next-day arrivals, 12-hour times --------------------------------


class _Card:
    def __init__(self, text):
        self._text = text

    def inner_text(self):
        return self._text

    def query_selector(self, _selector):
        return None


def _parse(text, **request):
    req = SearchRequest(origin="MRS", destination="REK", departure_date="2026-04-18", **request)
    return kayak_source._parse_card(_Card(text), req)


def test_overnight_kayak_arrival_lands_on_the_next_day():
    offer = _parse("Icelandair\n10:30 pm – 6:15 am\n+1\nnonstop\n8h 45m\n€ 312")
    seg = offer.outbound.segments[0]
    assert seg.departure_time == "2026-04-18T22:30:00"
    assert seg.arrival_time == "2026-04-19T06:15:00"


def test_same_day_kayak_arrival_and_inbound_use_their_own_dates():
    offer = _parse(
        "Icelandair\n07:10 – 09:40\n2h 30m\n13:00 – 21:05+1\n5h 05m\n€ 410",
        return_date="2026-04-25",
    )
    assert offer.outbound.segments[0].arrival_time == "2026-04-18T09:40:00"
    assert offer.inbound.segments[0].departure_time == "2026-04-25T13:00:00"
    assert offer.inbound.segments[0].arrival_time == "2026-04-26T21:05:00"


def test_twelve_hour_times_are_converted():
    assert kayak_source._to_24h("6:30", "pm") == "18:30"
    assert kayak_source._to_24h("12:05", "am") == "00:05"
    assert kayak_source._to_24h("12:05", "PM") == "12:05"
    assert kayak_source._to_24h("6:30", "") == "06:30"


# --- 3. Kayak.is_available says what actually failed ---------------------------


def _fake_playwright(monkeypatch, *, start_error=None, launch_error=None):
    launched = []

    class _Chromium:
        def launch(self, headless):
            if launch_error:
                raise launch_error
            launched.append(headless)
            return types.SimpleNamespace(close=lambda: None)

    class _Ctx:
        def __enter__(self):
            if start_error:
                raise start_error
            return types.SimpleNamespace(chromium=_Chromium())

        def __exit__(self, *exc):
            return False

    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = _Ctx
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)
    return launched


def test_a_startup_error_is_not_reported_as_a_missing_browser(monkeypatch):
    err = RuntimeError("It looks like you are using Playwright Sync API inside the asyncio loop")
    _fake_playwright(monkeypatch, start_error=err)
    ok, msg = kayak_source.KayakSource().is_available()
    assert not ok
    assert "asyncio loop" in msg and "not installed" not in msg


def test_a_missing_executable_is_reported_as_a_missing_browser(monkeypatch):
    err = RuntimeError("BrowserType.launch: Executable doesn't exist at /x/headless_shell")
    _fake_playwright(monkeypatch, launch_error=err)
    ok, msg = kayak_source.KayakSource().is_available()
    assert not ok and "playwright install chromium" in msg


def test_another_launch_failure_says_what_it_was(monkeypatch):
    _fake_playwright(monkeypatch, launch_error=RuntimeError("missing libnss3.so"))
    ok, msg = kayak_source.KayakSource().is_available()
    assert not ok and "libnss3" in msg and "not installed" not in msg


def test_a_headless_launch_is_what_counts_as_available(monkeypatch):
    """A headless-shell-only install works for search(), so it is available
    (review of #7: executable_path names the full browser even when absent)."""
    launched = _fake_playwright(monkeypatch)
    assert kayak_source.KayakSource().is_available()[0]
    assert launched == [True]


# --- review of #7: what is and is not a day marker ------------------------------


def test_things_after_the_arrival_that_are_not_day_markers():
    legs = kayak_source._extract_legs
    assert legs(None, "07:10 – 09:40\n+ 1 stop")[0][2] == 0
    assert legs(None, "07:10 – 09:40 +20 € bags")[0][2] == 0
    assert legs(None, "07:10 – 09:40\n+2 airlines")[0][2] == 0
    assert legs(None, "07:10 – 09:40\n+1 stop")[0][2] == 0
    assert legs(None, "11:00 pm – 6:15 am-1")[0][2] == -1
    assert legs(None, "11:00 pm – 6:15 am+1\nnonstop")[0][2] == 1


def test_an_hour_past_twelve_ignores_a_meridiem():
    assert kayak_source._to_24h("13:00", "pm") == "13:00"


def test_a_date_that_is_not_iso_keeps_the_old_stamp():
    assert kayak_source._arrival("2026/04/18", ("07:10", "09:40", 1)) == "2026/04/18T09:40:00"


def test_an_unknown_inbound_time_is_kept_too():
    request = SearchRequest(
        origin="MRS", destination="DUB", departure_date="2026-04-18",
        return_date="2026-04-25", inbound_arrival_before="18:00",
    )
    offer = {
        "outbound": {"segments": [{"departure_time": "2026-04-18T06:30:00", "arrival_time": ""}]},
        "inbound": {"segments": [{"departure_time": "2026-04-25T20:00:00", "arrival_time": ""}]},
    }
    assert _apply_time_filters([offer], request) == [offer]
