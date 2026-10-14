"""Kayak flight search adapter using playwright browser automation."""

import logging
import re
import time
from datetime import date, timedelta

from farepy.base import FlightOffer, Itinerary, SearchRequest, Segment

KAYAK_BASE = "https://www.kayak.com/flights"
#: What playwright's launch error says when the browser was never installed.
MISSING_BROWSER = "Executable doesn't exist"

# A scraper that swallows errors silently makes "no flights" indistinguishable
# from "Kayak changed its markup" (thorwhalen/farepy#1). The per-attempt misses
# below are expected and logged at DEBUG; the outcomes that point at a broken
# selector are logged at WARNING.
logger = logging.getLogger(__name__)


class KayakSource:
    name = "kayak"

    def __init__(self, *, timeout: int = 60, **_kwargs):
        self._timeout = timeout

    def is_available(self) -> tuple[bool, str]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return False, (
                "Playwright not installed. Run: pip install playwright && "
                "playwright install chromium"
            )
        # Probe exactly what search() does: a headless launch. That is the only
        # honest test, since headless runs playwright's separate headless shell,
        # and ``executable_path`` names the full browser whether or not it is
        # there. A failure is reported as itself; only a missing executable reads
        # as "Chromium not installed" (thorwhalen/farepy#6).
        try:
            with sync_playwright() as p:
                try:
                    p.chromium.launch(headless=True).close()
                except Exception as e:
                    logger.debug("Kayak: chromium launch failed: %r", e)
                    if MISSING_BROWSER in str(e):
                        return False, (
                            "Chromium browser not installed for playwright. "
                            "Run: playwright install chromium"
                        )
                    return False, f"Chromium could not start: {type(e).__name__}: {e}"
        except Exception as e:
            logger.debug("Kayak: playwright start failed: %r", e)
            return False, f"Playwright could not start: {type(e).__name__}: {e}"
        return True, "Kayak source ready (browser automation, experimental)."

    def search(self, request: SearchRequest) -> list[FlightOffer]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && "
                "playwright install chromium"
            )

        url = _build_url(request)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                return _scrape_results(browser, url, request, self._timeout)
            finally:
                browser.close()


def _build_url(request: SearchRequest) -> str:
    """Build Kayak search URL.

    One-way: https://www.kayak.com/flights/MRS-REK/2026-04-18
    Return:  https://www.kayak.com/flights/MRS-REK/2026-04-18/2026-04-30
    """
    path = (
        f"{KAYAK_BASE}/{request.origin}-{request.destination}/{request.departure_date}"
    )
    if request.return_date:
        path += f"/{request.return_date}"
    return path


def _scrape_results(
    browser,
    url: str,
    request: SearchRequest,
    timeout_seconds: int,
) -> list[FlightOffer]:
    """Navigate to Kayak and scrape flight results."""
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
    )
    page = context.new_page()

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_seconds * 1000)

        # Wait for results to load — Kayak uses various selectors across versions
        # Try multiple possible selectors
        result_selectors = [
            '[class*="resultInner"]',
            '[class*="nrc6-inner"]',
            '[class*="Flights-Results"]',
            ".resultWrapper",
            "[data-resultid]",
        ]

        loaded = False
        for selector in result_selectors:
            try:
                page.wait_for_selector(selector, timeout=timeout_seconds * 1000)
                loaded = True
                break
            except Exception as e:
                logger.debug("Kayak: results selector %r not found: %r", selector, e)
                continue

        if not loaded:
            logger.warning(
                "Kayak: none of the results selectors %s appeared within %ss; "
                "falling back to a fixed wait (the page markup may have changed)",
                result_selectors,
                timeout_seconds,
            )
            # Last resort: wait a fixed time for dynamic content
            time.sleep(10)

        # Try to dismiss any modals/overlays
        for dismiss_sel in [
            'button[aria-label="Close"]',
            '[class*="close"]',
            ".dDYU-close",
        ]:
            try:
                btn = page.query_selector(dismiss_sel)
                if btn:
                    btn.click()
                    time.sleep(0.5)
            except Exception as e:
                # Overlays are optional; failing to close one is not an error.
                logger.debug("Kayak: could not dismiss %r: %r", dismiss_sel, e)

        # Scroll to load more results
        for _ in range(3):
            page.evaluate("window.scrollBy(0, 1000)")
            time.sleep(1)

        return _extract_offers(page, request)

    finally:
        context.close()


def _extract_offers(page, request: SearchRequest) -> list[FlightOffer]:
    """Extract flight offers from the Kayak results page."""
    offers = []

    # Kayak uses various class naming conventions; try multiple approaches
    # Approach 1: Look for result cards with data-resultid
    cards = page.query_selector_all("[data-resultid]")

    if not cards:
        # Approach 2: result inner containers
        cards = page.query_selector_all('[class*="resultInner"], [class*="nrc6-inner"]')

    if not cards:
        # Approach 3: broader search for flight result rows
        cards = page.query_selector_all(
            '[class*="resultWrapper"], [class*="Flights-Results-FlightResultItem"]'
        )

    if not cards:
        logger.warning(
            "Kayak: no result cards matched any known selector; the page "
            "markup may have changed, or the search has no results"
        )

    failed = 0
    for card in cards:
        try:
            offer = _parse_card(card, request)
            if offer:
                offers.append(offer)
        except Exception:
            failed += 1
            logger.debug("Kayak: could not parse a result card", exc_info=True)
            continue

    if failed:
        logger.warning(
            "Kayak: %d of %d result cards could not be parsed (stale selectors?); "
            "returning the %d that could",
            failed,
            len(cards),
            len(offers),
        )
    return offers


def _parse_card(card, request: SearchRequest) -> FlightOffer | None:
    """Parse a single Kayak result card into a FlightOffer."""
    text = card.inner_text()
    if not text or len(text) < 10:
        return None

    # Extract price — look for currency symbol followed by digits
    price = _extract_price(card, text)
    if price is None:
        return None

    # Extract time pairs (departure - arrival) for each leg
    legs = _extract_legs(card, text)
    if not legs:
        return None

    # Extract airline name(s)
    airline_text = _extract_airline(card, text)
    airlines = [airline_text] if airline_text else []

    # Extract duration
    duration = _extract_duration(card, text)

    # Build outbound itinerary
    outbound_leg = legs[0]
    outbound = Itinerary(
        segments=[
            Segment(
                departure_airport=request.origin,
                arrival_airport=request.destination,
                departure_time=f"{request.departure_date}T{outbound_leg[0]}:00",
                arrival_time=_arrival(request.departure_date, outbound_leg),
                carrier=airline_text or "UNKNOWN",
                carrier_name=airline_text,
                flight_number=None,
                duration_minutes=duration[0] if duration else None,
            )
        ],
        duration_minutes=duration[0] if duration else None,
    )

    # Build inbound itinerary if return trip
    inbound = None
    if request.return_date and len(legs) > 1:
        inbound_leg = legs[1]
        inbound = Itinerary(
            segments=[
                Segment(
                    departure_airport=request.destination,
                    arrival_airport=request.origin,
                    departure_time=f"{request.return_date}T{inbound_leg[0]}:00",
                    arrival_time=_arrival(request.return_date, inbound_leg),
                    carrier=airline_text or "UNKNOWN",
                    carrier_name=airline_text,
                    flight_number=None,
                    duration_minutes=duration[1]
                    if duration and len(duration) > 1
                    else None,
                )
            ],
            duration_minutes=duration[1] if duration and len(duration) > 1 else None,
        )

    return FlightOffer(
        source="kayak",
        outbound=outbound,
        inbound=inbound,
        price=price,
        currency=request.currency,  # Kayak shows in local currency
        airlines=airlines,
        booking_url=None,
        raw={"text": text[:500]},  # Store raw text for debugging
    )


def _extract_price(card, text: str) -> float | None:
    """Extract price from a result card."""
    # Try specific price selectors first
    for sel in ['[class*="price-text"]', '[class*="price"]', ".f8F1-price-text"]:
        el = card.query_selector(sel)
        if el:
            price_text = el.inner_text()
            m = re.search(r"[\d,]+(?:\.\d+)?", price_text.replace(",", ""))
            if m:
                return float(m.group())

    # Fallback: find price pattern in full text
    # Match common patterns: $123, 123 €, €123, 123€, $1,234
    m = re.search(r"[$€£]\s*[\d,]+(?:\.\d+)?|[\d,]+(?:\.\d+)?\s*[$€£]", text)
    if m:
        digits = re.search(r"[\d,]+(?:\.\d+)?", m.group().replace(",", ""))
        if digits:
            return float(digits.group())
    return None


#: "06:30 – 10:45", "6:30 am – 10:45 pm", and Kayak's day marker after the
#: arrival ("10:45 pm+1", "+1" on the next line of the card's text, or "-1"). The
#: marker is a sign glued to ONE digit, so "+ 1 stop", "+20 €" or "+2 airlines"
#: are not read as days.
_LEG_PATTERN = re.compile(
    r"(\d{1,2}:\d{2})\s*(am|pm)?\s*[-–—]\s*(\d{1,2}:\d{2})\s*(am|pm)?"
    r"(?:[ \t]*\n?[ \t]*([+-]\d)(?!\d)(?!\s*(?:stops?|airlines?)\b))?",
    re.IGNORECASE,
)


def _to_24h(hhmm: str, meridiem: str) -> str:
    """``"6:30", "pm"`` -> ``"18:30"``; no meridiem means already 24h."""
    hours, minutes = hhmm.split(":")
    h = int(hours)
    m = meridiem.lower() if h <= 12 else ""  # "13:00 pm" is already 24-hour
    if m == "pm" and h != 12:
        h += 12
    elif m == "am" and h == 12:
        h = 0
    return f"{h:02d}:{minutes}"


def _extract_legs(card, text: str) -> list[tuple[str, str, int]]:
    """Extract departure-arrival time pairs.

    Returns list of (departure_time, arrival_time, days_later): times as
    24-hour HH:MM strings, and the number of days after the departure date on
    which the flight lands (Kayak's "+1" or "-1"; 0 when absent).
    """
    return [
        (_to_24h(dep, dep_m), _to_24h(arr, arr_m), int(days or 0))
        for dep, dep_m, arr, arr_m, days in _LEG_PATTERN.findall(text)
    ]


def _arrival(departure_date: str, leg: tuple[str, str, int]) -> str:
    """The arrival as ISO local time, on the date the flight actually lands.

    Stamping it with the departure date put an overnight arrival on the wrong
    day (thorwhalen/farepy#6), the way ``google_flights_source`` already avoids.
    """
    try:
        landed = (date.fromisoformat(departure_date) + timedelta(days=leg[2])).isoformat()
    except ValueError:  # not YYYY-MM-DD: keep the date as given, as before
        landed = departure_date
    return f"{landed}T{leg[1]}:00"


def _extract_airline(card, text: str) -> str | None:
    """Extract airline name from a result card."""
    for sel in ['[class*="codeshares"]', '[class*="airline"]', ".c_cgF-carrier-name"]:
        el = card.query_selector(sel)
        if el:
            return el.inner_text().strip()
    # Fallback: first non-time, non-price line that looks like an airline
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    for line in lines:
        if re.match(r"^[A-Z][a-zA-Z\s]+$", line) and len(line) < 30:
            return line
    return None


def _extract_stops(card, text: str) -> int:
    """Extract number of stops."""
    if re.search(r"nonstop|non-stop|direct", text, re.IGNORECASE):
        return 0
    m = re.search(r"(\d+)\s*stop", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 0


def _extract_duration(card, text: str) -> list[int]:
    """Extract duration(s) in minutes from text like '2h 30m' or '5h 15m'."""
    pattern = r"(\d+)h\s*(?:(\d+)m)?"
    matches = re.findall(pattern, text)
    durations = []
    for h, m in matches:
        durations.append(int(h) * 60 + int(m or 0))
    return durations
