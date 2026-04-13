---
name: farepy-source
description: >-
  Source adapter tooling for the farepy package. Build new flight source adapters
  that wrap airline APIs or aggregator endpoints. Use this skill when adding a new
  airline or aggregator source to farepy, wrapping a flight API, extending farepy's
  coverage to a new data provider, or when the user asks about how farepy sources
  work internally.
---

# farepy-source

Build new flight source adapters for farepy. A source wraps an external flight
API (airline or aggregator) and converts its results into farepy's normalized
`FlightOffer` format. Once registered, the new source participates in
`search_flights()` automatically.

## The FlightSource protocol

Every source must satisfy this protocol (defined in `farepy/base.py`):

```python
class FlightSource(Protocol):
    name: str

    def search(self, request: SearchRequest) -> list[FlightOffer]:
        """Search for flights. Returns empty list on no results."""
        ...

    def is_available(self) -> tuple[bool, str]:
        """Check availability. Returns (available, message)."""
        ...
```

Three things to implement: a `name` class attribute, `search()`, and
`is_available()`.

## Step-by-step: add a new source

### 1. Create the source module

Create `farepy/sources/{name}_source.py`. Follow this template:

```python
"""Transavia source via the Transavia Flight Offers API.

Install: pip install httpx  (or whatever dependency is needed)
"""

from farepy.base import FlightOffer, Itinerary, SearchRequest, Segment


class TransaviaSource:
    name = 'transavia'

    def __init__(self, **_kwargs):
        # Accept **_kwargs so make_source() can pass arbitrary config.
        # Store any source-specific config here.
        pass

    def is_available(self) -> tuple[bool, str]:
        # Check that the required dependency is installed.
        # Do NOT check API key validity here — just import availability.
        try:
            import httpx  # noqa: F401
            return True, 'Transavia source ready.'
        except ImportError:
            return False, 'httpx not installed. Run: pip install httpx'

    def search(self, request: SearchRequest) -> list[FlightOffer]:
        # Import the dependency lazily (inside the method).
        import httpx

        # Call the external API using fields from request:
        #   request.origin          — IATA code, e.g. "MRS"
        #   request.destination     — IATA code, e.g. "REK"
        #   request.departure_date  — "YYYY-MM-DD"
        #   request.return_date     — "YYYY-MM-DD" or None
        #   request.adults          — int
        #   request.currency        — "EUR"
        #   request.non_stop        — True/False/None
        #   request.max_results     — int

        response = httpx.get(
            'https://api.transavia.com/v3/flights',
            params={
                'origin': request.origin,
                'destination': request.destination,
                'departureDate': request.departure_date,
                'adults': request.adults,
            },
            headers={'apiKey': 'YOUR_KEY'},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        # Convert each result to a FlightOffer
        return [_convert(item, request) for item in data.get('flights', [])]


def _convert(item: dict, request: SearchRequest) -> FlightOffer:
    """Convert an API response item to a normalized FlightOffer."""
    outbound = Itinerary(
        segments=[
            Segment(
                departure_airport=item['departureAirport'],
                arrival_airport=item['arrivalAirport'],
                departure_time=item['departureDateTime'],
                arrival_time=item.get('arrivalDateTime', ''),
                carrier='TO',                           # IATA code
                carrier_name='Transavia',
                flight_number=item.get('flightNumber'),
                duration_minutes=item.get('durationMinutes'),
            )
        ],
        duration_minutes=item.get('durationMinutes'),
    )

    return FlightOffer(
        source='transavia',
        outbound=outbound,
        price=float(item['price']),
        currency=request.currency,
        airlines=['TO'],
        raw=item,                                       # preserve raw data
    )
```

### 2. Register the source

Add the source to `farepy/sources/__init__.py`:

```python
from farepy.sources.google_flights_source import GoogleFlightsSource
from farepy.sources.ryanair_source import RyanairSource
from farepy.sources.kayak_source import KayakSource
from farepy.sources.transavia_source import TransaviaSource  # new

ALL_SOURCES = {
    'google_flights': GoogleFlightsSource,
    'ryanair': RyanairSource,
    'kayak': KayakSource,
    'transavia': TransaviaSource,  # new
}
```

### 3. Add the optional dependency

In `pyproject.toml`:

```toml
[project.optional-dependencies]
google_flights = ["fast-flights"]
ryanair = ["ryanair-py"]
kayak = ["playwright"]
transavia = ["httpx"]                                   # new
all = ["fast-flights", "ryanair-py", "playwright", "httpx"]  # update
```

### 4. Verify

```python
from farepy import available_sources, search_flights

# Check it shows up
for s in available_sources():
    print(s['name'], s['available'])

# Test a search
result = search_flights('AMS-BCN', '2026-07-01', sources=['transavia'])
print(len(result['offers']), 'offers')
```

## The data model

Understand these four dataclasses (all in `farepy/base.py`):

```
SearchRequest           — what the user asked for
  .origin, .destination — IATA codes
  .departure_date       — "YYYY-MM-DD"
  .return_date          — "YYYY-MM-DD" or None
  .adults, .currency, .non_stop, .max_results
  .outbound_departure_after/before  — HH:MM time filters (applied post-query)
  .inbound_departure_after/before

FlightOffer             — one bookable option
  .source               — your source name string
  .outbound             — Itinerary (required)
  .inbound              — Itinerary or None (one-way)
  .price                — float
  .currency             — str
  .airlines             — list[str] (carrier names or codes)
  .booking_url          — str or None
  .raw                  — dict or None (original API response, stripped on cache)

Itinerary               — one direction of travel
  .segments             — list[Segment]
  .duration_minutes     — int or None

Segment                 — one takeoff-to-landing
  .departure_airport    — IATA code
  .arrival_airport      — IATA code
  .departure_time       — ISO 8601 string
  .arrival_time         — ISO 8601 string (use "" if unavailable)
  .carrier              — airline code or name
  .carrier_name         — full name or None
  .flight_number        — str or None
  .duration_minutes     — int or None
  .aircraft             — str or None
```

## Key conventions

### Lazy imports

Always import third-party dependencies **inside** `search()` and
`is_available()`, not at module top level. This prevents `ImportError` when the
optional dep isn't installed:

```python
# GOOD
def search(self, request):
    from ryanair import Ryanair
    ...

# BAD — crashes on import if ryanair-py isn't installed
from ryanair import Ryanair
class RyanairSource:
    ...
```

### Accept **_kwargs in __init__

The `make_source(name, **kwargs)` factory passes arbitrary kwargs to the
constructor. Accept and ignore unknown ones:

```python
def __init__(self, *, timeout: int = 30, **_kwargs):
    self._timeout = timeout
```

### Use "" for unknown fields, not None

`Segment.departure_time` and `Segment.arrival_time` are required `str` fields
(not `Optional`). If your API doesn't provide a value (e.g., Ryanair's fare
finder has no arrival time), use an empty string:

```python
Segment(
    departure_time=dep_time,
    arrival_time='',          # not available from this API
    ...
)
```

### Store raw data

Pass the original API response as `raw=item` in `FlightOffer`. This helps with
debugging. The cache system strips `raw` automatically when persisting to save
space.

### Let exceptions propagate

Don't catch and swallow errors in `search()`. The orchestrator in `core.py`
catches exceptions per-source and records them in `sources_failed`. If your API
returns a 401, let it raise — the user will see which source failed and why.

### Source name consistency

The `name` class attribute, the key in `ALL_SOURCES`, and the `source` field in
`FlightOffer` must all match:

```python
class TransaviaSource:
    name = 'transavia'          # <- matches

ALL_SOURCES = {
    'transavia': TransaviaSource,   # <- matches
}

FlightOffer(source='transavia', ...)    # <- matches
```

## Existing sources as reference

Read these files for working examples:

- `farepy/sources/google_flights_source.py` — API-based source wrapping
  `fast-flights`. Shows how to parse string-formatted times, prices, and
  durations. Handles next-day arrivals and multi-airline results.

- `farepy/sources/ryanair_source.py` — API-based source wrapping `ryanair-py`.
  Shows the simplest pattern: call library, convert dataclass fields. Handles
  both one-way (`get_cheapest_flights`) and round-trip (`get_cheapest_return_flights`).

- `farepy/sources/kayak_source.py` — Browser-based source using Playwright.
  Shows the DOM-scraping pattern with fallback selectors. Use this pattern only
  when no API is available.

## How the orchestrator uses your source

When `search_flights()` runs:

1. It calls `make_source(name)` which instantiates your class
2. It calls `is_available()` — if `(False, msg)`, skips your source entirely
3. It calls `search(request)` in a `ThreadPoolExecutor` thread
4. If `search()` raises, the exception message goes into `sources_failed`
5. If `search()` returns offers, they're merged with other sources and sorted
   by price
6. Results are cached (with `raw` stripped), then time-filtered

Your source runs in parallel with other sources. Keep it stateless — a new
instance is created for each search call.
