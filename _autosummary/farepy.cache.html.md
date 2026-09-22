# farepy.cache

JSON file-based caching for flight search results.

### Functions

| [`cache_key`](#farepy.cache.cache_key)(request, sources)                        | Generate a deterministic cache key from search parameters.   |
|-----------------------------------------------------------------------------------------------------|--------------------------------------------------------------|
| [`clear_cache`](#farepy.cache.clear_cache)(\*[, cache_dir])                       | Clear all cached results.                                    |
| [`get_cached`](#farepy.cache.get_cached)(request, sources, \*[, cache_dir, ...]) | Return cached result dict if fresh, else None.               |
| [`get_cached_result`](#farepy.cache.get_cached_result)(cache_id, \*[, cache_dir])       | Get a specific cached result by its ID (filename stem).      |
| [`list_cached_searches`](#farepy.cache.list_cached_searches)(\*[, cache_dir])              | Return summaries of all cached results.                      |
| [`put_cache`](#farepy.cache.put_cache)(result, sources, \*[, cache_dir])        | Cache a SearchResult.                                        |

### farepy.cache.cache_key(request, sources)

Generate a deterministic cache key from search parameters.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### farepy.cache.clear_cache(, cache_dir=None)

Clear all cached results. Returns count of files removed.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### farepy.cache.get_cached(request, sources, , cache_dir=None, ttl_hours=24)

Return cached result dict if fresh, else None.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### farepy.cache.get_cached_result(cache_id, , cache_dir=None)

Get a specific cached result by its ID (filename stem).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### farepy.cache.list_cached_searches(, cache_dir=None)

Return summaries of all cached results.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

### farepy.cache.put_cache(result, sources, , cache_dir=None)

Cache a SearchResult. Returns the cache filename.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
