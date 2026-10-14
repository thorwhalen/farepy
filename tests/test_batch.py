"""Tests for :mod:`farepy.batch`: combination expansion and batch-file parsing.

``search_flights`` is replaced with a recorder, so nothing is searched.
"""

import pytest

from farepy import batch


@pytest.fixture
def calls(monkeypatch):
    recorded = []

    def fake_search_flights(leg, departure_date, **kwargs):
        recorded.append({"leg": leg, "departure_date": departure_date, **kwargs})
        return {"leg": leg, "departure_date": departure_date}

    monkeypatch.setattr(batch, "search_flights", fake_search_flights)
    return recorded


def _triples(calls):
    return [(c["leg"], c["departure_date"], c["return_date"]) for c in calls]


# --- batch_search: cartesian expansion -----------------------------------------


def test_one_way_expands_legs_by_dates(calls):
    results = batch.batch_search(["MRS-REK", "CDG-KEF"], ["2026-04-18", "2026-04-19"])
    assert _triples(calls) == [
        ("MRS-REK", "2026-04-18", None),
        ("MRS-REK", "2026-04-19", None),
        ("CDG-KEF", "2026-04-18", None),
        ("CDG-KEF", "2026-04-19", None),
    ]
    assert len(results) == 4
    assert results[0] == {"leg": "MRS-REK", "departure_date": "2026-04-18"}


def test_return_dates_multiply_the_combinations(calls):
    batch.batch_search(
        ["MRS-REK"], ["2026-04-18", "2026-04-19"], return_dates=["2026-04-25", "2026-04-30"]
    )
    assert _triples(calls) == [
        ("MRS-REK", "2026-04-18", "2026-04-25"),
        ("MRS-REK", "2026-04-18", "2026-04-30"),
        ("MRS-REK", "2026-04-19", "2026-04-25"),
        ("MRS-REK", "2026-04-19", "2026-04-30"),
    ]


def test_empty_inputs_search_nothing(calls):
    assert batch.batch_search([], ["2026-04-18"]) == []
    assert batch.batch_search(["MRS-REK"], []) == []
    assert calls == []


def test_options_are_forwarded_to_every_search(calls, tmp_path):
    batch.batch_search(
        ["MRS-REK"],
        ["2026-04-18"],
        sources=["ryanair"],
        currency="USD",
        adults=2,
        non_stop=True,
        max_results=7,
        use_cache=False,
        cache_dir=str(tmp_path),
        cache_ttl_hours=3,
    )
    (call,) = calls
    assert call["sources"] == ["ryanair"]
    assert call["currency"] == "USD"
    assert call["adults"] == 2
    assert call["non_stop"] is True
    assert call["max_results"] == 7
    assert call["use_cache"] is False
    assert call["cache_dir"] == str(tmp_path)
    assert call["cache_ttl_hours"] == 3


# --- parse_batch_file / batch_from_file -----------------------------------------

BATCH_TEXT = """
# Spring trips
MRS-REK 2026-04-18

   CDG-KEF\t2026-05-01   2026-05-15
   # an indented comment
\t
mrs-rek 2026-04-19 2026-04-30
"""


def test_parse_skips_comments_and_blank_lines_and_splits_on_any_whitespace():
    assert batch.parse_batch_file(BATCH_TEXT) == [
        {"leg": "MRS-REK", "departure_date": "2026-04-18", "return_date": None},
        {"leg": "CDG-KEF", "departure_date": "2026-05-01", "return_date": "2026-05-15"},
        # the leg is passed through as written; search_flights normalises case
        {"leg": "mrs-rek", "departure_date": "2026-04-19", "return_date": "2026-04-30"},
    ]


@pytest.mark.parametrize("text", ["", "   \n\n", "# only a comment\n  # another"])
def test_parse_of_nothing_is_empty(text):
    assert batch.parse_batch_file(text) == []


def test_parse_reports_the_offending_line_number():
    text = "MRS-REK 2026-04-18\n# fine\nCDG-KEF\n"
    with pytest.raises(ValueError, match=r"Line 3: .*'CDG-KEF'"):
        batch.parse_batch_file(text)


def test_line_numbers_count_from_the_first_non_blank_line():
    # the content is stripped before numbering, so leading blank lines don't count
    with pytest.raises(ValueError, match="Line 1:"):
        batch.parse_batch_file("\n\nMRS-REK\n")


def test_batch_from_file_runs_one_search_per_line(calls):
    results = batch.batch_from_file(BATCH_TEXT, sources=["ryanair"], currency="GBP")
    assert _triples(calls) == [
        ("MRS-REK", "2026-04-18", None),
        ("CDG-KEF", "2026-05-01", "2026-05-15"),
        ("mrs-rek", "2026-04-19", "2026-04-30"),
    ]
    assert len(results) == 3
    assert all(c["sources"] == ["ryanair"] and c["currency"] == "GBP" for c in calls)


def test_batch_from_file_rejects_a_bad_file_before_searching(calls):
    with pytest.raises(ValueError):
        batch.batch_from_file("MRS-REK 2026-04-18\nbroken\n")
    assert calls == []
