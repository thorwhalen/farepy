"""JSON file-based caching for flight search results."""

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from farepy.base import SearchRequest, SearchResult

DEFAULT_CACHE_DIR = Path.home() / '.local' / 'share' / 'farepy' / 'cache'
DEFAULT_TTL_HOURS = 24


def _cache_dir(cache_dir: str | None = None) -> Path:
    d = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_key(request: SearchRequest, sources: list[str]) -> str:
    """Generate a deterministic cache key from search parameters."""
    key_data = {
        'origin': request.origin,
        'destination': request.destination,
        'departure_date': request.departure_date,
        'return_date': request.return_date,
        'currency': request.currency,
        'adults': request.adults,
        'non_stop': request.non_stop,
        'sources': sorted(sources),
    }
    return hashlib.sha256(
        json.dumps(key_data, sort_keys=True).encode()
    ).hexdigest()[:12]


def _cache_filename(request: SearchRequest, sources: list[str]) -> str:
    h = cache_key(request, sources)
    ret = f'_{request.return_date}' if request.return_date else ''
    return f'{request.departure_date}_{request.origin}_{request.destination}{ret}_{h}.json'


def get_cached(
    request: SearchRequest,
    sources: list[str],
    *,
    cache_dir: str | None = None,
    ttl_hours: float = DEFAULT_TTL_HOURS,
) -> dict | None:
    """Return cached result dict if fresh, else None."""
    d = _cache_dir(cache_dir)
    fname = _cache_filename(request, sources)
    path = d / fname

    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    # Check TTL
    searched_at = data.get('searched_at', '')
    if searched_at:
        try:
            ts = datetime.fromisoformat(searched_at.replace('Z', '+00:00'))
            if datetime.now(ts.tzinfo) - ts > timedelta(hours=ttl_hours):
                return None  # Expired
        except (ValueError, TypeError):
            pass

    data['cached'] = True
    return data


def put_cache(
    result: SearchResult,
    sources: list[str],
    *,
    cache_dir: str | None = None,
) -> str:
    """Cache a SearchResult. Returns the cache filename."""
    d = _cache_dir(cache_dir)
    fname = _cache_filename(result.request, sources)
    path = d / fname

    data = asdict(result)
    # Strip raw source data from cache to save space
    for offer in data.get('offers', []):
        offer.pop('raw', None)

    path.write_text(json.dumps(data, indent=2, default=str))
    return fname


def list_cached_searches(*, cache_dir: str | None = None) -> list[dict]:
    """Return summaries of all cached results."""
    d = _cache_dir(cache_dir)
    results = []

    for path in sorted(d.glob('*.json'), reverse=True):
        try:
            data = json.loads(path.read_text())
            req = data.get('request', {})
            results.append({
                'cache_id': path.stem,
                'filename': path.name,
                'origin': req.get('origin', ''),
                'destination': req.get('destination', ''),
                'departure_date': req.get('departure_date', ''),
                'return_date': req.get('return_date'),
                'num_offers': len(data.get('offers', [])),
                'sources_queried': data.get('sources_queried', []),
                'searched_at': data.get('searched_at', ''),
            })
        except (json.JSONDecodeError, OSError):
            continue

    return results


def get_cached_result(cache_id: str, *, cache_dir: str | None = None) -> dict:
    """Get a specific cached result by its ID (filename stem)."""
    d = _cache_dir(cache_dir)
    path = d / f'{cache_id}.json'

    if not path.exists():
        raise FileNotFoundError(f'Cache entry not found: {cache_id}')

    data = json.loads(path.read_text())
    data['cached'] = True
    return data


def clear_cache(*, cache_dir: str | None = None) -> dict:
    """Clear all cached results. Returns count of files removed."""
    d = _cache_dir(cache_dir)
    count = 0
    for path in d.glob('*.json'):
        path.unlink()
        count += 1
    return {'cleared': count}
