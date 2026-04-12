"""Flight data source registry."""

from farepy.sources.kiwi_source import KiwiSource
from farepy.sources.kayak_source import KayakSource

ALL_SOURCES = {
    'kiwi': KiwiSource,
    'kayak': KayakSource,
}


def make_source(name: str, **kwargs):
    """Create a source instance by name, passing config kwargs."""
    cls = ALL_SOURCES.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown source: {name!r}. Available: {list(ALL_SOURCES)}"
        )
    return cls(**kwargs)


def available_sources(**kwargs) -> list[dict]:
    """Return status of all sources.

    Each dict has: name, available (bool), message (str).
    API key kwargs are forwarded to each source constructor.
    """
    result = []
    for name, cls in ALL_SOURCES.items():
        source = cls(**kwargs)
        avail, msg = source.is_available()
        result.append({'name': name, 'available': avail, 'message': msg})
    return result
