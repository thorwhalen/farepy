# farepy.core

Search orchestration – the main entry point for flight searches.

### Functions

| [`search_flights`](#farepy.core.search_flights)(leg, departure_date, \*[, ...])   | Search for flights across selected sources.   |
|---------------------------------------------------------------------------------------------------|-----------------------------------------------|

### farepy.core.search_flights(leg, departure_date, , return_date=None, sources=None, currency='EUR', adults=1, non_stop=None, max_results=50, outbound_departure_after=None, outbound_departure_before=None, outbound_arrival_after=None, outbound_arrival_before=None, inbound_departure_after=None, inbound_departure_before=None, inbound_arrival_after=None, inbound_arrival_before=None, use_cache=True, cache_dir=None, cache_ttl_hours=24)

Search for flights across selected sources.

* **Parameters:**
  * **leg** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – IATA pair like “MRS-REK”
  * **departure_date** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – YYYY-MM-DD
  * **return_date** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – YYYY-MM-DD or None for one-way
  * **sources** ([`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)] | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – List of source names (e.g. [“google_flights”, “ryanair”]).
    None means all available.
  * **currency** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – ISO 4217 currency code
  * **adults** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – Number of adult travelers
  * **non_stop** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – If True, direct flights only
  * **max_results** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – Max results per source
  * **outbound_departure_after** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – HH:MM filter
  * **outbound_departure_before** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – HH:MM filter
  * **outbound_arrival_after** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – HH:MM filter
  * **outbound_arrival_before** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – HH:MM filter
  * **inbound_departure_after** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – HH:MM filter
  * **inbound_departure_before** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – HH:MM filter
  * **inbound_arrival_after** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – HH:MM filter
  * **inbound_arrival_before** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – HH:MM filter
  * **use_cache** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to use cached results
  * **cache_dir** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Override default cache directory
  * **cache_ttl_hours** ([`float`](https://docs.python.org/3/builtins/functions.html#float)) – Cache time-to-live in hours
* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
* **Returns:**
  SearchResult as a dict.
