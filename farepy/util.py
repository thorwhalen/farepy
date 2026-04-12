"""Internal utilities for farepy."""

import os
import re
from datetime import datetime


def parse_iso_duration(duration: str) -> int | None:
    """Parse ISO 8601 duration string to minutes.

    >>> parse_iso_duration('PT2H30M')
    150
    >>> parse_iso_duration('PT45M')
    45
    >>> parse_iso_duration('PT1H')
    60
    """
    if not duration:
        return None
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", duration)
    if not m:
        return None
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    return hours * 60 + minutes


def reformat_date(date_str: str, *, to_kiwi: bool = False) -> str:
    """Convert between date formats.

    >>> reformat_date('2026-04-18', to_kiwi=True)
    '18/04/2026'
    >>> reformat_date('18/04/2026')
    '2026-04-18'
    """
    if to_kiwi:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    else:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")


def parse_leg(leg: str) -> tuple[str, str]:
    """Parse a leg string like 'MRS-REK' into (origin, destination).

    >>> parse_leg('MRS-REK')
    ('MRS', 'REK')
    """
    parts = leg.strip().upper().split("-")
    if len(parts) != 2 or not all(len(p) == 3 and p.isalpha() for p in parts):
        raise ValueError(
            f"Invalid leg format: {leg!r}. Expected 'XXX-YYY' "
            f"(two 3-letter IATA codes separated by a dash)."
        )
    return parts[0], parts[1]


def extract_time(iso_datetime: str) -> str:
    """Extract HH:MM from an ISO 8601 datetime string.

    >>> extract_time('2026-04-18T06:30:00')
    '06:30'
    """
    return iso_datetime[11:16]


def time_in_range(
    time_str: str,
    *,
    after: str | None = None,
    before: str | None = None,
) -> bool:
    """Check if a HH:MM time falls within the given range.

    >>> time_in_range('14:30', after='08:00', before='18:00')
    True
    >>> time_in_range('06:00', after='08:00')
    False
    """
    if after and time_str < after:
        return False
    if before and time_str > before:
        return False
    return True


def check_api_key(
    env_var: str,
    *,
    service_name: str,
    signup_url: str,
    explicit_value: str | None = None,
) -> tuple[str | None, str]:
    """Check for an API key, returning (value, message).

    Checks explicit_value first, then the environment variable.
    """
    value = explicit_value or os.environ.get(env_var)
    if value:
        return value, f"{service_name} API key configured."
    return None, (
        f"{service_name} API key not configured. "
        f"Get one at {signup_url} . "
        f"Then set the {env_var} environment variable, "
        f"or pass it via the settings panel."
    )


def now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
