---
name: farepy-search
description: >-
  Flight search tooling for the farepy package. Search and compare flight prices
  across Google Flights, Ryanair, and Kayak from Python. Use this skill when
  searching for flights, comparing prices across airlines, building flight price
  tools, batch-searching multiple routes or dates, managing cached flight results,
  or when the user asks about European flight prices or cheap flights.
---

# farepy-search

Search and compare flight prices across multiple sources with a single function
call. farepy normalizes results from Google Flights, Ryanair, and Kayak into a
common format so prices are directly comparable.

## Install

```bash
pip install farepy[google_flights]   # Recommended — broadest coverage
pip install farepy[ryanair]          # Ryanair direct fares
pip install farepy[all]              # All sources
```

Each source is an optional dependency. Check what's available:

```python
from farepy import available_sources
for s in available_sources():
    print(f"{s['name']}: {'ready' if s['available'] else s['message']}")
```

## Core workflow: search_flights()

This is the main entry point. Two positional args, everything else keyword-only.

```python
from farepy import search_flights

# One-way search, all available sources
result = search_flights('MRS-REK', '2026-07-01')

# Round-trip
result = search_flights('DUB-STN', '2026-07-01', return_date='2026-07-08')

# Specific sources only
result = search_flights('DUB-STN', '2026-07-01', sources=['google_flights', 'ryanair'])

# With filters
result = search_flights(
    'MRS-REK', '2026-07-01',
    currency='USD',
    adults=2,
    non_stop=True,
    outbound_departure_after='06:00',
    outbound_departure_before='14:00',
)
```

### The result dict

`search_flights()` returns a plain dict (JSON-serializable):

```python
{
    'request': {
        'origin': 'MRS',
        'destination': 'REK',
        'departure_date': '2026-07-01',
        'return_date': None,
        'adults': 1,
        'currency': 'EUR',
        ...
    },
    'offers': [
        {
            'source': 'google_flights',        # or 'ryanair', 'kayak'
            'outbound': {
                'segments': [{
                    'departure_airport': 'MRS',
                    'arrival_airport': 'REK',
                    'departure_time': '2026-07-01T18:55:00',
                    'arrival_time': '2026-07-02T08:15:00',
                    'carrier': 'SWISS',
                    'carrier_name': 'SWISS',
                    'flight_number': None,      # only Ryanair provides this
                    'duration_minutes': 920,
                }],
                'duration_minutes': 920,
            },
            'inbound': None,                    # None for one-way
            'price': 237.0,
            'currency': 'EUR',
            'airlines': ['SWISS', 'Edelweiss Air'],
        },
        ...
    ],
    'sources_queried': ['google_flights', 'ryanair'],
    'sources_failed': {},                       # source -> error message
    'searched_at': '2026-07-01T12:00:00Z',
    'cached': False,
}
```

Offers are sorted by price (cheapest first).

### Iterating results

```python
result = search_flights('DUB-STN', '2026-07-01')

for offer in result['offers']:
    seg = offer['outbound']['segments'][0]
    print(f"{offer['price']} {offer['currency']}  "
          f"{offer['source']}  "
          f"{seg.get('departure_time', '')[:16]}  "
          f"{offer['airlines']}")
```

### Checking for failures

Always check `sources_failed` — a source might be down or blocked:

```python
result = search_flights('DUB-STN', '2026-07-01')
if result['sources_failed']:
    for source, error in result['sources_failed'].items():
        print(f"Warning: {source} failed: {error}")
```

## Source selection guide

| Source | Install | Coverage | Strengths | Limitations |
|---|---|---|---|---|
| `google_flights` | `farepy[google_flights]` | ~All airlines | Broadest coverage, no browser | No flight numbers, may be rate-limited |
| `ryanair` | `farepy[ryanair]` | Ryanair only | Flight numbers, accurate direct pricing | No arrival times, Ryanair routes only |
| `kayak` | `farepy[kayak]` | ~All airlines | Broad coverage | Experimental, slow (browser), often blocked |

**Recommendation**: Use `google_flights` as the primary source. Add `ryanair`
for accurate Ryanair-specific pricing and flight numbers. Only use `kayak` as
a fallback — it requires Playwright + Chromium and is fragile.

## Batch searching

Search multiple routes and/or dates in one call.

### Cartesian product

```python
from farepy import batch_search

results = batch_search(
    legs=['MRS-REK', 'CDG-KEF', 'DUB-STN'],
    departure_dates=['2026-07-01', '2026-07-02'],
    return_dates=['2026-07-08'],
)
# Returns 6 SearchResult dicts (3 legs x 2 dates x 1 return date)

for r in results:
    req = r['request']
    best = r['offers'][0] if r['offers'] else None
    price = f"{best['price']} {best['currency']}" if best else 'no results'
    print(f"{req['origin']}-{req['destination']} {req['departure_date']}: {price}")
```

### From a text file

```python
from farepy import batch_from_file

results = batch_from_file("""
# route        depart       return
MRS-REK  2026-07-01  2026-07-08
CDG-KEF  2026-07-15  2026-07-22
DUB-STN  2026-08-01
""")
```

Format: one search per line — `LEG DEPARTURE_DATE [RETURN_DATE]`. Lines starting
with `#` are comments.

## Caching

Results are cached locally for 24 hours by default in
`~/.local/share/farepy/cache/`. Cache keys ignore time filters, so the same
route/date combo with different time filters reuses the same cached data.

```python
# Disable caching for a single search
result = search_flights('MRS-REK', '2026-07-01', use_cache=False)

# Shorter TTL (1 hour)
result = search_flights('MRS-REK', '2026-07-01', cache_ttl_hours=1)

# Custom cache directory
result = search_flights('MRS-REK', '2026-07-01', cache_dir='/tmp/flights')
```

### Inspecting and managing the cache

```python
from farepy import list_cached_searches, get_cached_result, clear_cache

# List cached searches
for entry in list_cached_searches():
    print(f"{entry['origin']}-{entry['destination']}  "
          f"{entry['departure_date']}  "
          f"({entry['num_offers']} offers, {entry['searched_at']})")

# Retrieve a specific cached result by ID
result = get_cached_result(entry['cache_id'])

# Clear all cache
info = clear_cache()
print(f"Removed {info['cleared']} cached files")
```

## All search_flights parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `leg` | `str` | (required) | IATA pair: `"MRS-REK"` |
| `departure_date` | `str` | (required) | `"YYYY-MM-DD"` |
| `return_date` | `str \| None` | `None` | Return date for round-trip |
| `sources` | `list[str] \| None` | `None` | Source names; `None` = all available |
| `currency` | `str` | `"EUR"` | ISO 4217 code |
| `adults` | `int` | `1` | Number of passengers |
| `non_stop` | `bool \| None` | `None` | `True` = direct flights only |
| `max_results` | `int` | `50` | Max results per source |
| `outbound_departure_after` | `str \| None` | `None` | `"HH:MM"` earliest departure |
| `outbound_departure_before` | `str \| None` | `None` | `"HH:MM"` latest departure |
| `outbound_arrival_after` | `str \| None` | `None` | `"HH:MM"` earliest arrival |
| `outbound_arrival_before` | `str \| None` | `None` | `"HH:MM"` latest arrival |
| `inbound_departure_after` | `str \| None` | `None` | Same filters for return leg |
| `inbound_departure_before` | `str \| None` | `None` | |
| `inbound_arrival_after` | `str \| None` | `None` | |
| `inbound_arrival_before` | `str \| None` | `None` | |
| `use_cache` | `bool` | `True` | Enable/disable caching |
| `cache_dir` | `str \| None` | `None` | Override cache location |
| `cache_ttl_hours` | `float` | `24` | Cache expiry in hours |

## Gotchas

- **Ryanair has no arrival times.** The fare finder API only returns departure
  time + flight number. The `arrival_time` field will be `""`. Don't filter
  Ryanair results by arrival time — they'll all be excluded.
- **Google Flights returns string-parsed data.** Prices, times, and durations
  are parsed from rendered text, not structured API fields. Occasional parsing
  failures are possible — check for empty fields.
- **Time filters are post-query.** They don't reduce the API call — farepy
  fetches all results, caches them, then filters. This is by design (cache
  reuse across different time windows).
- **Kayak is experimental.** It uses headless Chromium and is frequently blocked
  by Akamai. Expect failures. It also requires `playwright install chromium`
  after pip install.
- **`search_flights` returns a dict, not a dataclass.** Results go through
  `dataclasses.asdict()` before returning, so they're plain dicts all the way
  down.
- **Rate limits matter.** Google Flights may block after many rapid requests.
  Ryanair's safe rate is ~1 request per minute. The cache helps — use it.
