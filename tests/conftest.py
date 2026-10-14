"""Shared fixtures for the offline test suite.

Three guards are autouse, so no test can reach the outside world by accident:

* every socket ``connect`` / DNS lookup raises, so a live HTTP call fails loudly
  instead of scraping;
* the provider libraries (``fast_flights``, ``ryanair``, ``playwright``) are
  made unimportable, so no real client or browser can start -- a test that
  needs one installs a fake module with ``monkeypatch.setitem(sys.modules, ...)``;
* the default cache directory points into ``tmp_path``, so nothing is written
  under the user's home even when a test forgets ``cache_dir``.
"""

import json
import socket
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
PROVIDER_MODULES = (
    "fast_flights",
    "ryanair",
    "playwright",
    "playwright.sync_api",
)


class NetworkBlocked(RuntimeError):
    """Raised by any attempt to open a network connection during tests."""


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def _refuse(*args, **kwargs):
        raise NetworkBlocked(f"network access attempted in a test: {args!r}")

    monkeypatch.setattr(socket.socket, "connect", _refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", _refuse)
    monkeypatch.setattr(socket, "create_connection", _refuse)
    monkeypatch.setattr(socket, "getaddrinfo", _refuse)


@pytest.fixture(autouse=True)
def no_provider_libraries(monkeypatch):
    for name in PROVIDER_MODULES:
        monkeypatch.setitem(sys.modules, name, None)  # import -> ImportError


@pytest.fixture(autouse=True)
def default_cache_in_tmp(monkeypatch, tmp_path):
    from farepy import cache

    default = tmp_path / "default_cache"
    monkeypatch.setattr(cache, "DEFAULT_CACHE_DIR", default)
    return default


@pytest.fixture
def load_fixture():
    def _load(name):
        return json.loads((FIXTURES / name).read_text())

    return _load
