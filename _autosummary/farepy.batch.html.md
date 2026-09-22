# farepy.batch

Batch flight search – cartesian combinations and file parsing.

### Functions

| [`batch_from_file`](#farepy.batch.batch_from_file)(file_content, \*[, sources, ...])   | Parse a batch file and run all searches.                          |
|------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| [`batch_search`](#farepy.batch.batch_search)(legs, departure_dates, \*[, ...])      | Run a cartesian product of legs x departure_dates x return_dates. |
| [`parse_batch_file`](#farepy.batch.parse_batch_file)(file_content)                      | Parse a batch file into search parameter dicts.                   |

### farepy.batch.batch_from_file(file_content, , sources=None, currency='EUR', adults=1, non_stop=None, max_results=50, use_cache=True, cache_dir=None, cache_ttl_hours=24)

Parse a batch file and run all searches.

* **Parameters:**
  * **file_content** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The text content of the batch file.
  * **batch_search****)** ( *(**other args same as*)
* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]
* **Returns:**
  List of SearchResult dicts.

### farepy.batch.batch_search(legs, departure_dates, , return_dates=None, sources=None, currency='EUR', adults=1, non_stop=None, max_results=50, use_cache=True, cache_dir=None, cache_ttl_hours=24)

Run a cartesian product of legs x departure_dates x return_dates.

Each combination is searched sequentially to respect API rate limits.
Caching ensures repeated combinations are not re-queried.

* **Parameters:**
  * **legs** ([`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – List of IATA pairs, e.g. [“MRS-REK”, “CDG-KEF”]
  * **departure_dates** ([`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – List of YYYY-MM-DD dates
  * **return_dates** ([`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)] | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – List of YYYY-MM-DD dates (None for one-way)
  * **sources** ([`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)] | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Which sources to query (None = all available)
  * **currency** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – ISO 4217 currency code
  * **adults** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – Number of adult travelers
  * **non_stop** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Direct flights only
  * **max_results** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – Max results per source per search
  * **use_cache** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Use cached results
  * **cache_dir** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Override cache directory
  * **cache_ttl_hours** ([`float`](https://docs.python.org/3/builtins/functions.html#float)) – Cache TTL
* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]
* **Returns:**
  List of SearchResult dicts, one per combination.

### farepy.batch.parse_batch_file(file_content)

Parse a batch file into search parameter dicts.

Format: one search per line
: ORIGIN-DEST YYYY-MM-DD [YYYY-MM-DD]

### Examples

MRS-REK 2026-04-18
MRS-REK 2026-04-18 2026-04-30
CDG-KEF 2026-05-01 2026-05-15

* **Returns:**
  leg, departure_date, return_date
* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]
