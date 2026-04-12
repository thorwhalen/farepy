# farepy

Multi-source flight search with normalized results, caching, and batch support.

Query Google Flights, Ryanair, and more from a single Python function. Results are
normalized into a common format so you can compare prices across sources without
worrying about each API's quirks.

## Install

```bash
pip install farepy[google_flights]   # Google Flights (recommended, broadest coverage)
pip install farepy[ryanair]          # Ryanair direct fares
pip install farepy[all]              # Everything
```

## Usage

### Search flights

```python
from farepy import search_flights

# One-way, all available sources
result = search_flights('MRS-REK', '2026-07-01')

for offer in result['offers'][:5]:
    seg = offer['outbound']['segments'][0]
    print(f"{offer['price']} {offer['currency']}  {offer['airlines']}  {seg['departure_time'][:16]}")
```

### Pick a source

```python
# Google Flights only (covers virtually all European LCCs)
result = search_flights('DUB-STN', '2026-07-01', sources=['google_flights'])

# Ryanair direct API (accurate fare-only pricing, includes flight numbers)
result = search_flights('DUB-STN', '2026-07-01', sources=['ryanair'])

# Both in parallel
result = search_flights('DUB-STN', '2026-07-01', sources=['google_flights', 'ryanair'])
```

### Round-trip

```python
result = search_flights('DUB-STN', '2026-07-01', return_date='2026-07-08')

for offer in result['offers'][:3]:
    out = offer['outbound']['segments'][0]
    ret = offer['inbound']['segments'][0] if offer['inbound'] else None
    print(f"{offer['price']} {offer['currency']}  out={out['departure_time'][:16]}", end='')
    if ret:
        print(f"  ret={ret['departure_time'][:16]}", end='')
    print()
```

### Filters

```python
result = search_flights(
    'MRS-REK', '2026-07-01',
    currency='USD',
    adults=2,
    non_stop=True,
    outbound_departure_after='06:00',
    outbound_departure_before='14:00',
)
```

### Batch search

Search multiple routes and dates in one call. Combinations run sequentially to
respect API rate limits; caching avoids re-querying repeated combinations.

```python
from farepy import batch_search

results = batch_search(
    legs=['MRS-REK', 'CDG-KEF'],
    departure_dates=['2026-07-01', '2026-07-02'],
    return_dates=['2026-07-08'],
)
# Returns one SearchResult dict per combination (4 in this case)
```

Or from a text file:

```python
from farepy import batch_from_file

results = batch_from_file("""
# route        depart       return
MRS-REK  2026-07-01  2026-07-08
CDG-KEF  2026-07-15  2026-07-22
DUB-STN  2026-08-01
""")
```

### Cache

Results are cached locally for 24 hours by default (in `~/.local/share/farepy/cache/`).

```python
from farepy import list_cached_searches, get_cached_result, clear_cache

# See what's cached
for entry in list_cached_searches():
    print(f"{entry['origin']}-{entry['destination']}  {entry['departure_date']}  ({entry['num_offers']} offers)")

# Retrieve a cached result
result = get_cached_result(entry['cache_id'])

# Clear everything
clear_cache()
```

Disable caching per-search with `use_cache=False`, or adjust the TTL:

```python
result = search_flights('MRS-REK', '2026-07-01', use_cache=False)
result = search_flights('MRS-REK', '2026-07-01', cache_ttl_hours=1)
```

### Check available sources

```python
from farepy import available_sources

for s in available_sources():
    status = 'ready' if s['available'] else 'not installed'
    print(f"  {s['name']}: {status}")
```

## Sources

| Source | Coverage | Install | Notes |
|---|---|---|---|
| `google_flights` | ~All airlines via Google Flights | `pip install farepy[google_flights]` | Protobuf API, no browser needed, broadest coverage |
| `ryanair` | Ryanair only | `pip install farepy[ryanair]` | Direct fare finder API, includes flight numbers |
| `kayak` | ~All airlines via Kayak | `pip install farepy[kayak]` | Experimental, requires Playwright + Chromium |

## Data model

Every source returns results normalized into the same structure:

```
SearchResult
  request: SearchRequest     # what was searched
  offers: [FlightOffer]      # sorted by price
  sources_queried: [str]     # which sources responded
  sources_failed: {str: str} # source -> error message
  searched_at: str            # ISO 8601 timestamp

FlightOffer
  source: str                # "google_flights" | "ryanair" | "kayak"
  outbound: Itinerary
  inbound: Itinerary | None  # None for one-way
  price: float
  currency: str
  airlines: [str]

Itinerary
  segments: [Segment]
  duration_minutes: int | None

Segment
  departure_airport: str     # IATA code
  arrival_airport: str       # IATA code
  departure_time: str        # ISO 8601
  arrival_time: str          # ISO 8601 (empty if unavailable)
  carrier: str
  carrier_name: str | None
  flight_number: str | None
  duration_minutes: int | None
```

Results are returned as plain dicts (via `dataclasses.asdict`), so they serialize
to JSON directly.
