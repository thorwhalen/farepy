"""Search orchestration — the main entry point for flight searches."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict

from farepy.base import FlightOffer, SearchRequest, SearchResult
from farepy.cache import get_cached, put_cache
from farepy.sources import ALL_SOURCES, available_sources, make_source
from farepy.util import extract_time, now_iso, parse_leg, time_in_range


def search_flights(
    leg: str,
    departure_date: str,
    *,
    return_date: str | None = None,
    sources: list[str] | None = None,
    currency: str = 'EUR',
    adults: int = 1,
    non_stop: bool | None = None,
    max_results: int = 50,
    outbound_departure_after: str | None = None,
    outbound_departure_before: str | None = None,
    outbound_arrival_after: str | None = None,
    outbound_arrival_before: str | None = None,
    inbound_departure_after: str | None = None,
    inbound_departure_before: str | None = None,
    inbound_arrival_after: str | None = None,
    inbound_arrival_before: str | None = None,
    use_cache: bool = True,
    cache_dir: str | None = None,
    cache_ttl_hours: float = 24,
    # API keys (override env vars)
    kiwi_api_key: str | None = None,
) -> dict:
    """Search for flights across selected sources.

    Args:
        leg: IATA pair like "MRS-REK"
        departure_date: YYYY-MM-DD
        return_date: YYYY-MM-DD or None for one-way
        sources: List of source names (e.g. ["kiwi", "kayak"]).
            None means all available.
        currency: ISO 4217 currency code
        adults: Number of adult travelers
        non_stop: If True, direct flights only
        max_results: Max results per source
        outbound_departure_after: HH:MM filter
        outbound_departure_before: HH:MM filter
        outbound_arrival_after: HH:MM filter
        outbound_arrival_before: HH:MM filter
        inbound_departure_after: HH:MM filter
        inbound_departure_before: HH:MM filter
        inbound_arrival_after: HH:MM filter
        inbound_arrival_before: HH:MM filter
        use_cache: Whether to use cached results
        cache_dir: Override default cache directory
        cache_ttl_hours: Cache time-to-live in hours
        kiwi_api_key: Explicit Kiwi API key

    Returns:
        SearchResult as a dict.
    """
    origin, destination = parse_leg(leg)

    request = SearchRequest(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        adults=adults,
        currency=currency,
        max_results=max_results,
        non_stop=non_stop,
        outbound_departure_after=outbound_departure_after,
        outbound_departure_before=outbound_departure_before,
        outbound_arrival_after=outbound_arrival_after,
        outbound_arrival_before=outbound_arrival_before,
        inbound_departure_after=inbound_departure_after,
        inbound_departure_before=inbound_departure_before,
        inbound_arrival_after=inbound_arrival_after,
        inbound_arrival_before=inbound_arrival_before,
    )

    key_kwargs = {
        'kiwi_api_key': kiwi_api_key,
    }

    # Determine which sources to query
    if sources is None:
        sources_to_query = [
            name
            for name in ALL_SOURCES
            if make_source(name, **key_kwargs).is_available()[0]
        ]
    else:
        sources_to_query = [s for s in sources if s in ALL_SOURCES]

    if not sources_to_query:
        return asdict(
            SearchResult(
                request=request,
                offers=[],
                sources_queried=[],
                sources_failed={
                    'all': 'No sources available. Configure API keys or install dependencies.'
                },
                searched_at=now_iso(),
            )
        )

    # Check cache (time filters are applied post-query, so cache key ignores them)
    if use_cache:
        cached = get_cached(
            request, sources_to_query,
            cache_dir=cache_dir, ttl_hours=cache_ttl_hours,
        )
        if cached is not None:
            # Apply time filters to cached results
            cached['offers'] = _apply_time_filters(cached.get('offers', []), request)
            return cached

    # Query sources in parallel
    all_offers: list[FlightOffer] = []
    sources_failed: dict[str, str] = {}

    def _query_source(name: str) -> tuple[str, list[FlightOffer] | str]:
        try:
            source = make_source(name, **key_kwargs)
            return name, source.search(request)
        except Exception as e:
            return name, str(e)

    with ThreadPoolExecutor(max_workers=len(sources_to_query)) as executor:
        futures = {
            executor.submit(_query_source, name): name
            for name in sources_to_query
        }
        for future in as_completed(futures):
            name, result = future.result()
            if isinstance(result, str):
                sources_failed[name] = result
            else:
                all_offers.extend(result)

    # Sort by price
    all_offers.sort(key=lambda o: o.price)

    result = SearchResult(
        request=request,
        offers=all_offers,
        sources_queried=sources_to_query,
        sources_failed=sources_failed,
        searched_at=now_iso(),
    )

    # Cache the unfiltered results
    if use_cache:
        put_cache(result, sources_to_query, cache_dir=cache_dir)

    # Apply time filters to the result
    result_dict = asdict(result)
    result_dict['offers'] = _apply_time_filters(result_dict['offers'], request)

    return result_dict


def _apply_time_filters(
    offers: list[dict], request: SearchRequest
) -> list[dict]:
    """Filter offers by time ranges (post-query)."""
    has_outbound_filter = any([
        request.outbound_departure_after,
        request.outbound_departure_before,
        request.outbound_arrival_after,
        request.outbound_arrival_before,
    ])
    has_inbound_filter = any([
        request.inbound_departure_after,
        request.inbound_departure_before,
        request.inbound_arrival_after,
        request.inbound_arrival_before,
    ])

    if not has_outbound_filter and not has_inbound_filter:
        return offers

    filtered = []
    for offer in offers:
        outbound = offer.get('outbound', {})
        segments = outbound.get('segments', [])

        if has_outbound_filter and segments:
            dep_time = extract_time(segments[0].get('departure_time', ''))
            arr_time = extract_time(segments[-1].get('arrival_time', ''))

            if not time_in_range(
                dep_time,
                after=request.outbound_departure_after,
                before=request.outbound_departure_before,
            ):
                continue
            if not time_in_range(
                arr_time,
                after=request.outbound_arrival_after,
                before=request.outbound_arrival_before,
            ):
                continue

        inbound = offer.get('inbound')
        if has_inbound_filter and inbound:
            in_segments = inbound.get('segments', [])
            if in_segments:
                dep_time = extract_time(in_segments[0].get('departure_time', ''))
                arr_time = extract_time(in_segments[-1].get('arrival_time', ''))

                if not time_in_range(
                    dep_time,
                    after=request.inbound_departure_after,
                    before=request.inbound_departure_before,
                ):
                    continue
                if not time_in_range(
                    arr_time,
                    after=request.inbound_arrival_after,
                    before=request.inbound_arrival_before,
                ):
                    continue

        filtered.append(offer)

    return filtered
