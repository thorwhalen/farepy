"""Tests for :func:`farepy.core.search_flights` with stub sources.

The real source registry is swapped for stubs, so the orchestration (source
selection, fan-out, failure aggregation, sorting, filters, caching) is tested
without any provider library or network.
"""

import pytest

import farepy.sources
from farepy import core
from farepy.base import FlightOffer, Itinerary, Segment


def _offer(source, price, *, dep="2026-04-18T06:30:00", arr="2026-04-18T10:45:00",
           in_dep=None, in_arr=None):
    seg = Segment("MRS", "REK", dep, arr, "FI")
    inbound = None
    if in_dep is not None:
        inbound = Itinerary(segments=[Segment("REK", "MRS", in_dep, in_arr or "", "FI")])
    return FlightOffer(
        source=source,
        outbound=Itinerary(segments=[seg]),
        inbound=inbound,
        price=price,
        currency="EUR",
        airlines=["FI"],
    )


def _stub_source(name, offers=(), *, error=None, available=True):
    class Stub:
        calls = []

        def __init__(self, **_kwargs):
            pass

        def is_available(self):
            return available, f"{name} {'ready' if available else 'missing'}"

        def search(self, request):
            Stub.calls.append(request)
            if error is not None:
                raise error
            return list(offers)

    Stub.name = name
    return Stub


@pytest.fixture
def register(monkeypatch):
    """Replace the source registry (in both modules that read it) with stubs."""
    registry = {}
    monkeypatch.setattr(farepy.sources, "ALL_SOURCES", registry)
    monkeypatch.setattr(core, "ALL_SOURCES", registry)

    def _register(*stubs):
        for stub in stubs:
            registry[stub.name] = stub
        return stubs

    return _register


def _search(tmp_path, **kwargs):
    kwargs.setdefault("cache_dir", str(tmp_path))
    return core.search_flights("MRS-REK", "2026-04-18", **kwargs)


# --- fan-out, failures, sorting -------------------------------------------------


def test_offers_from_all_sources_are_merged_and_sorted_by_price(register, tmp_path):
    register(
        _stub_source("alpha", [_offer("alpha", 300.0), _offer("alpha", 120.0)]),
        _stub_source("beta", [_offer("beta", 199.0)]),
    )
    result = _search(tmp_path, sources=["alpha", "beta"])
    assert [o["price"] for o in result["offers"]] == [120.0, 199.0, 300.0]
    assert result["sources_queried"] == ["alpha", "beta"]
    assert result["sources_failed"] == {}
    assert result["cached"] is False
    assert result["searched_at"].endswith("Z")


def test_one_failing_source_is_reported_and_the_other_still_answers(register, tmp_path):
    register(
        _stub_source("good", [_offer("good", 99.0)]),
        _stub_source("bad", error=RuntimeError("provider changed its markup")),
    )
    result = _search(tmp_path, sources=["good", "bad"])
    assert result["sources_failed"] == {"bad": "provider changed its markup"}
    assert [o["source"] for o in result["offers"]] == ["good"]
    assert set(result["sources_queried"]) == {"good", "bad"}


def test_request_fields_reach_the_sources(register, tmp_path):
    (stub,) = register(_stub_source("alpha"))
    _search(tmp_path, sources=["alpha"], return_date="2026-04-30", currency="USD",
            adults=2, non_stop=True, max_results=5, use_cache=False)
    (req,) = stub.calls
    assert (req.origin, req.destination) == ("MRS", "REK")
    assert req.return_date == "2026-04-30"
    assert (req.currency, req.adults, req.non_stop, req.max_results) == ("USD", 2, True, 5)


def test_leg_is_normalised_and_validated(register, tmp_path):
    (stub,) = register(_stub_source("alpha"))
    core.search_flights(" mrs-rek ", "2026-04-18", sources=["alpha"], use_cache=False)
    assert stub.calls[0].origin == "MRS"
    with pytest.raises(ValueError, match="Invalid leg"):
        core.search_flights("MRSREK", "2026-04-18", sources=["alpha"])


# --- source selection -----------------------------------------------------------


def test_none_means_every_available_source(register, tmp_path):
    up, down = register(
        _stub_source("up", [_offer("up", 50.0)]),
        _stub_source("down", [_offer("down", 10.0)], available=False),
    )
    result = _search(tmp_path)
    assert result["sources_queried"] == ["up"]
    assert down.calls == [] and len(up.calls) == 1


def test_unknown_source_names_are_dropped(register, tmp_path):
    register(_stub_source("alpha", [_offer("alpha", 50.0)]))
    result = _search(tmp_path, sources=["alpha", "no_such_source"])
    assert result["sources_queried"] == ["alpha"]


def test_no_usable_source_returns_an_explanatory_failure(register, tmp_path):
    register(_stub_source("down", available=False))
    result = _search(tmp_path)
    assert result["offers"] == [] and result["sources_queried"] == []
    assert "No sources available" in result["sources_failed"]["all"]
    assert list(tmp_path.iterdir()) == []  # nothing cached


# --- time filters ---------------------------------------------------------------


def _filter_fixture(register):
    register(
        _stub_source(
            "alpha",
            [
                _offer("alpha", 100.0, dep="2026-04-18T06:00:00", arr="2026-04-18T09:00:00"),
                _offer("alpha", 200.0, dep="2026-04-18T09:30:00", arr="2026-04-18T13:00:00"),
                _offer("alpha", 300.0, dep="2026-04-18T19:00:00", arr="2026-04-18T23:30:00"),
            ],
        )
    )


def test_outbound_departure_window(register, tmp_path):
    _filter_fixture(register)
    result = _search(tmp_path, sources=["alpha"], outbound_departure_after="08:00",
                     outbound_departure_before="20:00")
    assert [o["price"] for o in result["offers"]] == [200.0, 300.0]


def test_outbound_arrival_window(register, tmp_path):
    _filter_fixture(register)
    result = _search(tmp_path, sources=["alpha"], outbound_arrival_before="14:00")
    assert [o["price"] for o in result["offers"]] == [100.0, 200.0]


def test_inbound_window_filters_only_offers_with_an_inbound(register, tmp_path):
    register(
        _stub_source(
            "alpha",
            [
                _offer("alpha", 100.0, in_dep="2026-04-30T07:00:00", in_arr="2026-04-30T11:00:00"),
                _offer("alpha", 200.0, in_dep="2026-04-30T18:00:00", in_arr="2026-04-30T22:00:00"),
                _offer("alpha", 300.0),  # one-way: the inbound filter can't apply
            ],
        )
    )
    result = _search(tmp_path, sources=["alpha"], inbound_departure_after="12:00")
    assert [o["price"] for o in result["offers"]] == [200.0, 300.0]


# --- caching --------------------------------------------------------------------


def test_second_search_is_served_from_cache_unfiltered_then_refiltered(register, tmp_path):
    _filter_fixture(register)
    first = _search(tmp_path, sources=["alpha"], outbound_departure_after="08:00")
    assert len(first["offers"]) == 2

    stub = farepy.sources.ALL_SOURCES["alpha"]
    n_calls = len(stub.calls)
    second = _search(tmp_path, sources=["alpha"])  # same cache key, no filter
    assert second["cached"] is True
    assert len(second["offers"]) == 3  # the cache kept the unfiltered set
    third = _search(tmp_path, sources=["alpha"], outbound_departure_before="08:00")
    assert [o["price"] for o in third["offers"]] == [100.0]
    assert len(stub.calls) == n_calls  # neither hit the source


def test_use_cache_false_neither_reads_nor_writes(register, tmp_path):
    (stub,) = register(_stub_source("alpha", [_offer("alpha", 50.0)]))
    _search(tmp_path, sources=["alpha"], use_cache=False)
    _search(tmp_path, sources=["alpha"], use_cache=False)
    assert len(stub.calls) == 2
    assert list(tmp_path.iterdir()) == []
