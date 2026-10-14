"""The conftest guards really do block the network and the provider libraries."""

import importlib
import socket
import urllib.request

import pytest

PROVIDER_MODULES = ("fast_flights", "ryanair", "playwright", "playwright.sync_api")


#: RFC 5737 TEST-NET-1: reserved for documentation, routed nowhere. If a guard ever
#: regressed, these self-tests would time out against it instead of reaching a real host.
TEST_NET = "192.0.2.1"

def test_raw_socket_connect_is_refused():
    with socket.socket() as s, pytest.raises(RuntimeError, match="network access attempted"):
        s.connect((TEST_NET, 80))


def test_http_client_is_refused():
    with pytest.raises(Exception) as exc_info:
        urllib.request.urlopen(f"http://{TEST_NET}/", timeout=1)
    assert "network access attempted" in str(exc_info.value)


@pytest.mark.parametrize("name", PROVIDER_MODULES)
def test_provider_libraries_cannot_be_imported(name):
    with pytest.raises(ImportError):
        importlib.import_module(name)
