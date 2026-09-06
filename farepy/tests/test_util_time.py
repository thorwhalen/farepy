"""Tests for the time helpers in :mod:`farepy.util`.

These pin the two properties of ``now_iso`` that the rest of the package
depends on: the exact wire format of the string it returns (stamped onto
every ``SearchResult.searched_at`` and re-parsed by the cache), and the
absence of any deprecation warning from the underlying clock call.
"""

import re
import warnings

from farepy.util import now_iso

# The exact shape of the string `now_iso` has always produced: a UTC timestamp
# to second precision with a literal trailing "Z" (no numeric offset).
ISO_Z_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def test_now_iso_format_is_unchanged():
    """The emitted string keeps its literal-Z, second-precision UTC shape."""
    assert ISO_Z_PATTERN.fullmatch(now_iso())


def test_now_iso_emits_no_deprecation_warning():
    """The clock call must not be a deprecated (and soon removed) API."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        now_iso()
