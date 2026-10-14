"""Tests for :mod:`farepy.cache`: key derivation, TTL expiry, list/get/clear.

Every test writes under ``tmp_path`` (conftest also redirects the default dir).
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from farepy import cache
from farepy.base import FlightOffer, Itinerary, SearchRequest, SearchResult, Segment

SOURCES = ["google_flights", "ryanair"]


def _request(**overrides):
    params = dict(origin="MRS", destination="REK", departure_date="2026-04-18")
    params.update(overrides)
    return SearchRequest(**params)


def _result(request=None, *, searched_at=None, price=100.0):
    seg = Segment("MRS", "REK", "2026-04-18T06:30:00", "2026-04-18T10:45:00", "FI")
    offer = FlightOffer(
        source="ryanair",
        outbound=Itinerary(segments=[seg]),
        price=price,
        currency="EUR",
        airlines=["FI"],
        raw={"provider": "payload"},
    )
    return SearchResult(
        request=request or _request(),
        offers=[offer],
        sources_queried=list(SOURCES),
        sources_failed={},
        searched_at=searched_at or _iso_z(datetime.now(timezone.utc)),
    )


def _iso_z(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# --- key derivation ------------------------------------------------------------


def test_cache_key_is_deterministic_short_hex():
    key = cache.cache_key(_request(), SOURCES)
    assert key == cache.cache_key(_request(), SOURCES)
    assert len(key) == 12 and int(key, 16) >= 0


def test_cache_key_ignores_source_order():
    assert cache.cache_key(_request(), ["ryanair", "google_flights"]) == cache.cache_key(
        _request(), ["google_flights", "ryanair"]
    )


@pytest.mark.parametrize(
    "change",
    [
        {"origin": "CDG"},
        {"destination": "KEF"},
        {"departure_date": "2026-04-19"},
        {"return_date": "2026-04-30"},
        {"currency": "USD"},
        {"adults": 2},
        {"non_stop": True},
    ],
)
def test_cache_key_changes_with_each_search_parameter(change):
    assert cache.cache_key(_request(**change), SOURCES) != cache.cache_key(
        _request(), SOURCES
    )


def test_cache_key_changes_with_the_source_set():
    assert cache.cache_key(_request(), ["ryanair"]) != cache.cache_key(
        _request(), SOURCES
    )


def test_cache_key_ignores_post_query_filters_and_max_results():
    filtered = _request(
        outbound_departure_after="08:00", inbound_arrival_before="20:00", max_results=5
    )
    assert cache.cache_key(filtered, SOURCES) == cache.cache_key(_request(), SOURCES)


def test_cache_filename_is_readable_and_includes_return_date():
    key = cache.cache_key(_request(), SOURCES)
    assert cache._cache_filename(_request(), SOURCES) == f"2026-04-18_MRS_REK_{key}.json"
    rt = _request(return_date="2026-04-30")
    rt_key = cache.cache_key(rt, SOURCES)
    assert (
        cache._cache_filename(rt, SOURCES) == f"2026-04-18_MRS_REK_2026-04-30_{rt_key}.json"
    )


# --- put / get, TTL ------------------------------------------------------------


def test_put_then_get_round_trips_and_marks_cached(tmp_path):
    fname = cache.put_cache(_result(), SOURCES, cache_dir=str(tmp_path))
    assert (tmp_path / fname).exists()
    got = cache.get_cached(_request(), SOURCES, cache_dir=str(tmp_path))
    assert got["cached"] is True
    assert got["request"]["origin"] == "MRS"
    assert got["offers"][0]["price"] == 100.0


def test_put_strips_raw_provider_payload(tmp_path):
    fname = cache.put_cache(_result(), SOURCES, cache_dir=str(tmp_path))
    stored = json.loads((tmp_path / fname).read_text())
    assert "raw" not in stored["offers"][0]


def test_get_misses_for_another_request_or_source_set(tmp_path):
    cache.put_cache(_result(), SOURCES, cache_dir=str(tmp_path))
    assert cache.get_cached(_request(adults=3), SOURCES, cache_dir=str(tmp_path)) is None
    assert cache.get_cached(_request(), ["ryanair"], cache_dir=str(tmp_path)) is None


def test_expired_entry_is_a_miss(tmp_path):
    old = _iso_z(datetime.now(timezone.utc) - timedelta(hours=25))
    cache.put_cache(_result(searched_at=old), SOURCES, cache_dir=str(tmp_path))
    assert cache.get_cached(_request(), SOURCES, cache_dir=str(tmp_path)) is None


def test_ttl_hours_is_honoured(tmp_path):
    two_hours_ago = _iso_z(datetime.now(timezone.utc) - timedelta(hours=2))
    cache.put_cache(_result(searched_at=two_hours_ago), SOURCES, cache_dir=str(tmp_path))
    kw = dict(cache_dir=str(tmp_path))
    assert cache.get_cached(_request(), SOURCES, ttl_hours=3, **kw) is not None
    assert cache.get_cached(_request(), SOURCES, ttl_hours=1, **kw) is None


def test_corrupt_entry_is_a_miss_not_an_error(tmp_path):
    (tmp_path / cache._cache_filename(_request(), SOURCES)).write_text("{not json")
    assert cache.get_cached(_request(), SOURCES, cache_dir=str(tmp_path)) is None


def test_unparseable_timestamp_is_treated_as_fresh(tmp_path):
    fname = cache.put_cache(_result(searched_at="yesterday-ish"), SOURCES, cache_dir=str(tmp_path))
    assert (tmp_path / fname).exists()
    assert cache.get_cached(_request(), SOURCES, cache_dir=str(tmp_path)) is not None


def test_default_cache_dir_is_used_when_none_given(default_cache_in_tmp):
    fname = cache.put_cache(_result(), SOURCES)
    assert (default_cache_in_tmp / fname).exists()


# --- list / get by id / clear ---------------------------------------------------


def test_list_cached_searches_summarises_entries(tmp_path):
    cache.put_cache(_result(), SOURCES, cache_dir=str(tmp_path))
    cache.put_cache(
        _result(_request(departure_date="2026-05-01", return_date="2026-05-10")),
        SOURCES,
        cache_dir=str(tmp_path),
    )
    (tmp_path / "zz_broken.json").write_text("nope")

    listed = cache.list_cached_searches(cache_dir=str(tmp_path))
    assert [s["departure_date"] for s in listed] == ["2026-05-01", "2026-04-18"]
    newest = listed[0]
    assert newest["return_date"] == "2026-05-10"
    assert newest["num_offers"] == 1
    assert newest["sources_queried"] == SOURCES
    assert newest["filename"] == newest["cache_id"] + ".json"


def test_get_cached_result_by_id(tmp_path):
    fname = cache.put_cache(_result(), SOURCES, cache_dir=str(tmp_path))
    (entry,) = cache.list_cached_searches(cache_dir=str(tmp_path))
    got = cache.get_cached_result(entry["cache_id"], cache_dir=str(tmp_path))
    assert got["cached"] is True and entry["filename"] == fname


def test_get_cached_result_unknown_id_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="nope"):
        cache.get_cached_result("nope", cache_dir=str(tmp_path))


def test_clear_cache_removes_json_entries_only(tmp_path):
    cache.put_cache(_result(), SOURCES, cache_dir=str(tmp_path))
    cache.put_cache(_result(_request(adults=2)), SOURCES, cache_dir=str(tmp_path))
    (tmp_path / "notes.txt").write_text("keep me")
    assert cache.clear_cache(cache_dir=str(tmp_path)) == {"cleared": 2}
    assert cache.list_cached_searches(cache_dir=str(tmp_path)) == []
    assert (tmp_path / "notes.txt").exists()
    assert cache.clear_cache(cache_dir=str(tmp_path)) == {"cleared": 0}
