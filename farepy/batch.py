"""Batch flight search — cartesian combinations and file parsing."""

from itertools import product

from farepy.core import search_flights


def batch_search(
    legs: list[str],
    departure_dates: list[str],
    *,
    return_dates: list[str] | None = None,
    sources: list[str] | None = None,
    currency: str = 'EUR',
    adults: int = 1,
    non_stop: bool | None = None,
    max_results: int = 50,
    use_cache: bool = True,
    cache_dir: str | None = None,
    cache_ttl_hours: float = 24,
    kiwi_api_key: str | None = None,
) -> list[dict]:
    """Run a cartesian product of legs x departure_dates x return_dates.

    Each combination is searched sequentially to respect API rate limits.
    Caching ensures repeated combinations are not re-queried.

    Args:
        legs: List of IATA pairs, e.g. ["MRS-REK", "CDG-KEF"]
        departure_dates: List of YYYY-MM-DD dates
        return_dates: List of YYYY-MM-DD dates (None for one-way)
        sources: Which sources to query (None = all available)
        currency: ISO 4217 currency code
        adults: Number of adult travelers
        non_stop: Direct flights only
        max_results: Max results per source per search
        use_cache: Use cached results
        cache_dir: Override cache directory
        cache_ttl_hours: Cache TTL
        kiwi_api_key: Explicit key

    Returns:
        List of SearchResult dicts, one per combination.
    """
    key_kwargs = {
        'kiwi_api_key': kiwi_api_key,
    }

    ret_dates = return_dates or [None]
    combos = list(product(legs, departure_dates, ret_dates))

    results = []
    for leg, dep_date, ret_date in combos:
        result = search_flights(
            leg=leg,
            departure_date=dep_date,
            return_date=ret_date,
            sources=sources,
            currency=currency,
            adults=adults,
            non_stop=non_stop,
            max_results=max_results,
            use_cache=use_cache,
            cache_dir=cache_dir,
            cache_ttl_hours=cache_ttl_hours,
            **key_kwargs,
        )
        results.append(result)

    return results


def parse_batch_file(file_content: str) -> list[dict]:
    """Parse a batch file into search parameter dicts.

    Format: one search per line
        ORIGIN-DEST YYYY-MM-DD [YYYY-MM-DD]

    Examples:
        MRS-REK 2026-04-18
        MRS-REK 2026-04-18 2026-04-30
        CDG-KEF 2026-05-01 2026-05-15

    Returns:
        List of dicts with keys: leg, departure_date, return_date
    """
    searches = []
    for line_num, line in enumerate(file_content.strip().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ValueError(
                f'Line {line_num}: expected "LEG DATE [RETURN_DATE]", got: {line!r}'
            )
        searches.append({
            'leg': parts[0],
            'departure_date': parts[1],
            'return_date': parts[2] if len(parts) > 2 else None,
        })
    return searches


def batch_from_file(
    file_content: str,
    *,
    sources: list[str] | None = None,
    currency: str = 'EUR',
    adults: int = 1,
    non_stop: bool | None = None,
    max_results: int = 50,
    use_cache: bool = True,
    cache_dir: str | None = None,
    cache_ttl_hours: float = 24,
    kiwi_api_key: str | None = None,
) -> list[dict]:
    """Parse a batch file and run all searches.

    Args:
        file_content: The text content of the batch file.
        (other args same as batch_search)

    Returns:
        List of SearchResult dicts.
    """
    key_kwargs = {
        'kiwi_api_key': kiwi_api_key,
    }
    searches = parse_batch_file(file_content)

    results = []
    for s in searches:
        result = search_flights(
            leg=s['leg'],
            departure_date=s['departure_date'],
            return_date=s['return_date'],
            sources=sources,
            currency=currency,
            adults=adults,
            non_stop=non_stop,
            max_results=max_results,
            use_cache=use_cache,
            cache_dir=cache_dir,
            cache_ttl_hours=cache_ttl_hours,
            **key_kwargs,
        )
        results.append(result)

    return results
