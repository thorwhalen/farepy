"""farepy -- Multi-source flight search with normalized results, caching, and batch support."""

from farepy.core import search_flights as search_flights
from farepy.batch import (
    batch_search as batch_search,
    batch_from_file as batch_from_file,
)
from farepy.sources import available_sources as available_sources
from farepy.cache import (
    list_cached_searches as list_cached_searches,
    get_cached_result as get_cached_result,
    clear_cache as clear_cache,
)
