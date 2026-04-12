"""Kiwi (Tequila) flight search adapter."""

import requests

from farepy.base import FlightOffer, Itinerary, SearchRequest, Segment
from farepy.util import check_api_key, reformat_date, parse_iso_duration

KIWI_BASE_URL = 'https://tequila-api.kiwi.com'
KIWI_SIGNUP_URL = 'https://tequila.kiwi.com/'


class KiwiSource:
    name = 'kiwi'

    def __init__(self, *, kiwi_api_key: str | None = None, **_kwargs):
        self._api_key = kiwi_api_key

    def is_available(self) -> tuple[bool, str]:
        key, msg = check_api_key(
            'KIWI_API_KEY',
            service_name='Kiwi (Tequila)',
            signup_url=KIWI_SIGNUP_URL,
            explicit_value=self._api_key,
        )
        if not key:
            return False, msg
        return True, 'Kiwi source ready.'

    def search(self, request: SearchRequest) -> list[FlightOffer]:
        key, msg = check_api_key(
            'KIWI_API_KEY',
            service_name='Kiwi',
            signup_url=KIWI_SIGNUP_URL,
            explicit_value=self._api_key,
        )
        if not key:
            raise RuntimeError(msg)

        params = {
            'fly_from': request.origin,
            'fly_to': request.destination,
            'date_from': reformat_date(request.departure_date, to_kiwi=True),
            'date_to': reformat_date(request.departure_date, to_kiwi=True),
            'adults': request.adults,
            'curr': request.currency,
            'limit': request.max_results,
        }

        if request.return_date:
            params['flight_type'] = 'round'
            params['return_from'] = reformat_date(request.return_date, to_kiwi=True)
            params['return_to'] = reformat_date(request.return_date, to_kiwi=True)
        else:
            params['flight_type'] = 'oneway'

        if request.non_stop:
            params['max_stopovers'] = 0

        headers = {'apikey': key}
        resp = requests.get(
            f'{KIWI_BASE_URL}/v2/search',
            headers=headers,
            params=params,
            timeout=30,
        )

        if resp.status_code == 401:
            raise RuntimeError(
                'Kiwi authentication failed. Check that your API key is correct. '
                f'Get a new one at {KIWI_SIGNUP_URL}'
            )
        if resp.status_code == 403:
            raise RuntimeError(
                'Kiwi access forbidden. Your API key may be inactive or rate-limited. '
                f'Check your account at {KIWI_SIGNUP_URL}'
            )
        resp.raise_for_status()
        data = resp.json()

        return [_parse_offer(item, request) for item in data.get('data', [])]


def _parse_offer(item: dict, request: SearchRequest) -> FlightOffer:
    """Parse a single Kiwi flight result into a normalized FlightOffer."""
    routes = item.get('route', [])

    # Split routes into outbound and inbound based on the 'return' field
    # Kiwi marks return segments with return == 1
    outbound_routes = [r for r in routes if r.get('return', 0) == 0]
    inbound_routes = [r for r in routes if r.get('return', 0) == 1]

    outbound = _routes_to_itinerary(outbound_routes)

    inbound = None
    if inbound_routes:
        inbound = _routes_to_itinerary(inbound_routes)

    airlines = sorted(set(r.get('airline', '') for r in routes if r.get('airline')))

    return FlightOffer(
        source='kiwi',
        outbound=outbound,
        inbound=inbound,
        price=float(item.get('price', 0)),
        currency=request.currency,
        airlines=airlines,
        booking_url=item.get('deep_link'),
        raw=item,
    )


def _routes_to_itinerary(routes: list[dict]) -> Itinerary:
    """Convert Kiwi route entries to a normalized Itinerary."""
    segments = []
    for r in routes:
        dep_time = r.get('local_departure', '')
        arr_time = r.get('local_arrival', '')

        # Calculate duration from timestamps if available
        duration = None
        utc_dep = r.get('utc_departure', '')
        utc_arr = r.get('utc_arrival', '')
        if utc_dep and utc_arr:
            from datetime import datetime

            try:
                fmt = '%Y-%m-%dT%H:%M:%S.000Z'
                d = datetime.strptime(utc_dep, fmt)
                a = datetime.strptime(utc_arr, fmt)
                duration = int((a - d).total_seconds() / 60)
            except (ValueError, TypeError):
                pass

        segments.append(
            Segment(
                departure_airport=r.get('flyFrom', ''),
                arrival_airport=r.get('flyTo', ''),
                departure_time=dep_time,
                arrival_time=arr_time,
                carrier=r.get('airline', ''),
                carrier_name=None,  # Kiwi doesn't provide full names in search
                flight_number=(
                    f"{r.get('airline', '')}{r.get('flight_no', '')}"
                    if r.get('flight_no')
                    else None
                ),
                duration_minutes=duration,
                aircraft=None,
            )
        )

    # Total itinerary duration
    total_duration = None
    if segments and all(s.duration_minutes is not None for s in segments):
        total_duration = sum(s.duration_minutes for s in segments)
        # Add layover times
        for i in range(len(segments) - 1):
            from datetime import datetime

            try:
                arr = datetime.fromisoformat(segments[i].arrival_time)
                dep = datetime.fromisoformat(segments[i + 1].departure_time)
                layover = int((dep - arr).total_seconds() / 60)
                total_duration += max(0, layover)
            except (ValueError, TypeError):
                pass

    return Itinerary(segments=segments, duration_minutes=total_duration)
