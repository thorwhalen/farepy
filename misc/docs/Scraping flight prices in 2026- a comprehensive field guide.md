# Scraping flight prices in 2026: a comprehensive field guide

**The most effective path to programmatic European flight price comparison in 2026 combines reverse-engineered aggregator APIs with direct airline endpoints, not browser-based scraping.** Google Flights and Ryanair both expose internal APIs that Python libraries can query without a headless browser, while Skyscanner's Android app API has been reverse-engineered with TLS fingerprint impersonation. The landscape has shifted dramatically: Ryanair is now on every major aggregator (Booking Holdings deal, August 2025), the old public APIs are dead (QPX Express 2018, Skyscanner public API 2020), and post-quantum TLS fingerprinting has created a new detection vector that invalidates pre-2024 scraping techniques. This report maps the entire terrain — what works, what's broken, and what to build.

---

## 1. Aggregator scraping: Google Flights is the sweet spot

The five major flight aggregators sit on a clear difficulty gradient. **Google Flights (3/5 difficulty)** is the most accessible because it lacks third-party anti-bot solutions — no Cloudflare, no Akamai, no PerimeterX. Its internal transport uses Base64-encoded Protobuf parameters in the URL's `tfs` field, and two Python libraries have reverse-engineered this format. **Skyscanner (4/5)** uses PerimeterX/HUMAN Security with behavioral analysis, TLS fingerprinting, and "Press & Hold" CAPTCHA challenges, but its Android app API has been cracked. **Kayak and Momondo (5/5)** share Akamai Bot Manager infrastructure under Booking Holdings and are effectively unscrapable without expensive residential proxies and CAPTCHA-solving services. **Kiwi.com (2/5 via API)** had the most developer-friendly approach with its Tequila REST API, but new partnerships are now invitation-only.

### Google Flights tools and approach

The best open-source option is **`fast-flights`** (GitHub: `AWeirdDev/flights`, **~870 stars**, last release v2.2, March 2025), which programmatically constructs the Protobuf-encoded query parameter and fetches results via HTTP — no browser needed. It supports one-way, round-trip, and multi-city searches and is installable via `pip install fast-flights`. A more modern alternative is **`fli`** (GitHub: `punitarani/fli`, **~80 stars**), which includes a built-in MCP server (`fli-mcp`) for Claude Desktop integration and a CLI interface. Both libraries are functional but semi-maintained — they break when Google modifies its Protobuf schema.

The older **`google-flight-analysis`** (GitHub: `celebi-pkg/flight-analysis`, **~300 stars**) uses Selenium with ChromeDriver and is slow, fragile, and increasingly detected. Multiple Apify actors exist (e.g., `brilliant_gum/google-flights-scraper`, updated February 2026), running on Apify's platform using compute credits. For commercial use, **SerpApi** (`serpapi.com/google-flights-api`) provides structured JSON from Google Flights at $50+/month.

Google Flights covers virtually all European LCCs: **Ryanair** (listed since January 2014 partnership, 2,069+ routes), **easyJet, Wizz Air, Vueling, Transavia, Eurowings, Norwegian, Pegasus, Volotea**, and airBaltic are all indexed.

### Skyscanner's reverse-engineered Android API

The most notable tool is **`irrisolto/skyscanner`** (GitHub, **29 stars**, updated September 2025), which reverse-engineered Skyscanner's Android app API. It uses `curl_cffi` for TLS fingerprint impersonation and handles PerimeterX's `px_authorization` token. It supports flights, car rentals, and flexible "Everywhere"/"Anytime" searches. Skyscanner offers the broadest budget airline coverage among aggregators — **1,200+ airline/OTA partners** — and is widely regarded as the best metasearch engine for European LCCs.

Skyscanner's official **Partners/Travel API** remains available for approved partners (free, revenue via affiliate commission), but requires a case-by-case application at `partners.skyscanner.net`. The barrier is high: established, high-traffic travel businesses only.

### Kayak, Momondo, and Kiwi.com

**Kayak** uses Akamai Bot Manager with sensor data collection, behavioral biometrics, and hCaptcha challenges. No standalone open-source scraper exists. DIY requires Playwright with stealth patches, residential proxies, and CAPTCHA-solving — resource-intensive and unreliable. **Momondo** shares the exact same backend (Booking Holdings acquisition, 2017, $550M) and presents identical challenges.

**Kiwi.com's Tequila API** (`tequila-api.kiwi.com`) remains functional with endpoints like `/v2/search` for flight search, `/locations/query` for airports, and virtual interlining across 750+ carriers. Authentication is via API key in the `apikey` header. However, per Kiwi.com's blog, new partnerships are now **invitation-only** — existing partners retain access, but the platform is no longer open to new individual developers.

| Aggregator | Difficulty | Anti-bot system | Best approach | Public API |
|---|---|---|---|---|
| Google Flights | 3/5 | Google internal, reCAPTCHA v3 | `fast-flights` or `fli` Protobuf library | None (QPX dead 2018) |
| Skyscanner | 4/5 | PerimeterX/HUMAN | `irrisolto/skyscanner` Android API | Partners API (approval required) |
| Kayak | 5/5 | Akamai Bot Manager | Stealth Playwright + residential proxies | None |
| Momondo | 5/5 | Akamai (same as Kayak) | Same as Kayak | None |
| Kiwi.com | 2/5 via API | API key auth | Tequila REST API | Tequila (now invite-only) |

---

## 2. Budget airline APIs: Ryanair is gold, the rest is a gradient of pain

### Ryanair — the best-documented airline API in Europe

Ryanair's internal API is the most accessible and well-documented of any European budget carrier. The **fare finder endpoints** remain publicly accessible without authentication:

- **One-way fares:** `https://www.ryanair.com/api/farfnd/v4/oneWayFares`
- **Round-trip fares:** `https://www.ryanair.com/api/farfnd/v4/roundTripFares`
- **Cheapest per day:** `https://www.ryanair.com/api/farfnd/v4/roundTripFares/{ORIG}/{DEST}/cheapestPerDay`
- **Timetables:** `https://www.ryanair.com/api/timtbl/3/schedules/{ORIG}/{DEST}/years/{YYYY}/months/{MM}`
- **Airports:** `https://www.ryanair.com/api/views/locate/5/airports/{lang}/active`

The JSON response includes `fares[].outbound.price.value`, `currencyCode`, `flightNumber`, `departureDate`, and airport IATA codes. A community-maintained Postman collection exists at `postman.com/hakkotsu/workspace/ryanair`. The API has been documented via a GitHub Gist (**86 stars**, active since 2015, updated March 2026).

**Critical 2025 change:** The `/api/booking/v4/*/availability` endpoint now returns "Availability declined" without valid session cookies — PerimeterX/HUMAN cookie validation was recently added. The fare finder endpoints (`/farfnd/v4/*`) remain more accessible.

The go-to Python package is **`ryanair-py`** (GitHub: `cohaolain/ryanair-py`, PyPI: `ryanair-py` v3.0.0, **actively maintained**). It uses direct API calls (no browser automation), returns named tuples with price, currency, flight number, and departure/arrival data. Safe request rate is approximately **1 request per minute** — faster rates lead to IP blocks.

### easyJet, Wizz Air, and the Akamai wall

**easyJet** has a known internal API at `https://www.easyjet.com/ejavailability/api/v16/availability/query` accepting parameters like `DepartureIata`, `ArrivalIata`, `AdultSeats`, and `IncludePrices`. However, it requires heavy session cookie management (`ASP.NET_SessionId`, `ejCC_3`, `RBKPOD`, `AVLPOD`), and the API version number increments regularly. easyJet uses **Akamai Bot Manager**, making it significantly harder than Ryanair. **No well-maintained Python package exists** — the `kranjcevblaz/easyjet_scraper` on GitHub uses Selenium and is stale.

**Wizz Air** exposes a POST-based API at `https://be.wizzair.com/{VERSION}/Api/search/timetable` and `/Api/search/search`, but the **version number in the URL changes every few weeks** (e.g., `10.1.0`, `8.7.1`). This is the biggest pain point — scrapers must dynamically discover the current version from the site's JavaScript bundles. The JSON response includes `outboundFlights[].fares[].fullBasePrice.amount` and `currencyCode` with bundle types (BASIC, WIZZ GO). Wizz Air uses **Akamai Bot Manager at HIGH protection level**. No PyPI package exists; the best GitHub option is `kovacskokokornel/wizzair-scraper` (low stars, recent).

### Two airlines with official APIs: Transavia and Norwegian

**Transavia** is unique — it is the only airline on this list with an **officially documented public developer API**. Register at `developer.transavia.com`, subscribe to products, and receive an API key. The Flight Offers API returns availability and prices with deeplinks for booking. As part of the Air France-KLM group, the infrastructure is professionally maintained with 10+ years of API distribution. The only Python wrapper (`bbelderbos/transavia`) is stale, but calling the REST API directly with `httpx` or `requests` is straightforward.

**Norwegian Air Shuttle** has publicly visible API documentation at `services.dev.norwegian.com/retail/docs/index.html`, including endpoints for `/retail/availability/calendar`, `/retail/offers`, and `/retail/routes`. It uses the **IATA NDC v17.2 standard** (XML-based), requires Basic Auth with partner credentials, and supports 100 requests/second. However, obtaining partner credentials requires a business relationship.

### The rest: sparse coverage

**Vueling** (IAG Group) runs on Navitaire SkySales with Akamai Bot Manager — no Python tools exist. **Eurowings** (Lufthansa Group) has no publicly documented API or community tools. **Pegasus Airlines** has an unstable internal API (documented only by a .NET client, `sirdx/Pegasustan`), which warns that "Pegasus API is unstable — some functionalities can be suddenly gone." **Volotea** is the most opaque — no internal API endpoints have been publicly documented, and no scraping tools exist. The Go-language project `fgparamio/api-flight.com` lists Volotea as "To Do" — it was never completed.

| Airline | Best approach | Python package | Anti-bot | Difficulty |
|---|---|---|---|---|
| Ryanair | Direct API (`/farfnd/v4/*`) | `ryanair-py` (PyPI, active) | PerimeterX/HUMAN | Medium |
| easyJet | Session-based API scraping | None maintained | Akamai Bot Manager | High |
| Wizz Air | Versioned API + version discovery | `wizzair-scraper` (GitHub, low stars) | Akamai (HIGH) | High |
| Transavia | **Official public API** | None (call REST directly) | Standard (API key) | Low |
| Vueling | Browser automation only | None | Akamai + SkySales | Very High |
| Eurowings | Aggregator scraping only | None | Lufthansa Group protections | High |
| Norwegian | Partner API (NDC standard) | None | Basic Auth | Medium |
| Pegasus | Unstable internal API | None (.NET only) | Unknown vendor | Medium-High |
| Volotea | Aggregator scraping only | None | Unknown | Unknown |

---

## 3. Which airlines will you miss, and what to scrape directly

### The aggregator coverage question is largely solved

The landscape changed dramatically in 2024-2025. **Ryanair — historically the biggest gap — is now available on every major aggregator.** The timeline: Kiwi.com partnership (January 2024), Skyscanner partnership (September 2024), Expedia (April 2025), and Booking Holdings/Kayak (August 2025). As of 2026, Ryanair's "Approved OTA" partners include loveholidays, lastminute, Travelfusion, Kiwi, TUI, Expedia, and Booking Holdings.

No major European airline currently follows the pre-2024 Southwest Airlines model of being entirely absent from aggregators. The era of "Ryanair-only-on-Ryanair.com" is over.

### Where gaps persist

**Direct-only promotional fares** remain systematically absent from aggregators. LCCs run flash sales, loyalty pricing (like Volotea's Megavolotea membership), and app-exclusive deals that are never distributed through third parties. Airlines save **10-15% on distribution costs** through direct bookings, creating strong incentives for direct-only pricing.

**Volotea's niche routes** are a notable gap. Over half of Volotea's routes are exclusive connections between small and mid-sized European cities (e.g., Milan Bergamo–Lyon, Malta–Bordeaux). While Volotea appears on major aggregators, these niche routes may have limited or inconsistent representation.

**Charter and seasonal operators** from Germany, Scandinavia, and the UK to Mediterranean destinations (Greece, Turkey, Spain, Egypt) are often only bookable through tour operators like TUI or Jet2holidays. These routes appear on aggregators inconsistently or not at all.

**Ancillary pricing accuracy** is poor across aggregators. Per going.com (2026), "Google Flights often omits ULCCs entirely or lists them without accurate baggage pricing." Skyscanner testing found that **43% of lowest displayed fares** required additional bag fees not shown in the initial price. For true price comparison, baggage costs from direct airline APIs are essential.

### The minimum viable scraping configuration

For **~95% European LCC coverage**, scrape three sources in parallel: (1) Google Flights via the `fli` or `fast-flights` library — free, fast, covers all major LCCs; (2) Ryanair's direct API via `ryanair-py` — for accurate fare-only pricing and promotional fares; (3) Kiwi.com Tequila API (if accessible) — for virtual interlining options and creative multi-carrier routes. Add Transavia's official API for Air France-KLM group coverage. For the hardest-to-reach airlines (Volotea, Wizz Air promotional fares), fall back to stealth browser scraping with Camoufox or Patchright.

---

## 4. Python tooling: what actually works in 2026

### The anti-detection hierarchy

Not all scraping tools are created equal. The current hierarchy, ranked by stealth effectiveness:

- **Camoufox** (GitHub: `daijro/camoufox`, **~4K stars**, active development) — a modified Firefox browser with fingerprint spoofing at the **C++ implementation level**. Uses BrowserForge for statistically realistic fingerprint generation. Achieves **0% headless detection scores on CreepJS** — the best of any tool tested. Uses Firefox's Juggler protocol instead of CDP, eliminating CDP detection entirely. Compatible with Playwright's API. Caveat: Firefox's ~3% market share means some WAFs may flag Firefox users more aggressively, and the project is still in beta.

- **Patchright** (GitHub: `nicedouble/patchright`) — a patched Playwright that fixes CDP leaks (`Runtime.enable`) and executes JavaScript in isolated ExecutionContexts. A **drop-in replacement** requiring only one import line change. Passes CreepJS, BrowserScan, and Rebrowser bot detection tests. Production-ready as of August 2025.

- **Nodriver** (GitHub: `ultrafunkamsterdam/nodriver`, v0.48.1, November 2025) — the official successor to undetected-chromedriver. Fully async, eliminates Selenium/WebDriver dependency, communicates directly via CDP. Still has issues on VPS/headless environments.

- **curl_cffi** (GitHub: `lexiforest/curl_cffi`, **~3K stars**) — Python bindings for curl-impersonate. Reproduces exact TLS signatures (JA3/JA4) of Chrome, Firefox, and Safari. Supports HTTP/2 and HTTP/3. Cannot execute JavaScript — useful only for direct API calls where TLS fingerprinting matters.

Standard **Playwright** (without stealth patches) is detectable: it leaks `navigator.webdriver`, sends `Runtime.enable` CDP commands, and has non-standard TLS fingerprints. **`undetected-chromedriver`** (10K+ stars) is increasingly unreliable — open issues are piling up (#2130-#2301+ in 2025). **`cloudscraper`** works against basic Cloudflare challenges only and fails against Bot Management v2/v3 used by all travel sites. **`puppeteer-extra-plugin-stealth`** was deprecated in February 2025 — Cloudflare now specifically identifies its evasion techniques.

### MCP servers for Claude Code integration

Several MCP servers provide flight search capabilities:

- **`fli-mcp`** (GitHub: `punitarani/fli`) — reverse-engineered Google Flights Protobuf API, works with Claude Desktop, Python-based, provides `search_flights` tool. **Best choice for Claude Code agents.**
- **`flights-mcp`** (GitHub: `ravinahp/flights-mcp`) — wraps Duffel API (400+ airlines), requires Duffel API key.
- **`google-flights-mcp`** (GitHub: `salamentic/google-flights-mcp`) — wraps the `fast-flights` library.
- **Flight Search MCP** (`flights.fctolabs.com`) — wraps Kiwi/Tequila API, remote SSE endpoint at `findflights.me/sse`.

### The recommended architecture for a Claude Code agent

```
Claude Code Agent (orchestrates, normalizes, compares)
├── fli MCP Server → Google Flights (free, fast, no API key)
├── ryanair-py → Ryanair direct API (free, PyPI package)
├── httpx/requests → Transavia official API (free, API key)
├── httpx/requests → Amadeus SDK (free tier, production paid)
├── Camoufox + Playwright → Fallback stealth scraping
└── SQLite/DuckDB → Price history, caching, analytics
```

Use **async parallel search** across sources, normalize results into a `NormalizedFlight` dataclass (source, airline, flight_number, airports, times, price, currency, cabin_class, scraped_at), deduplicate by flight number and date, and store in SQLite for price tracking. Cache results for **15-30 minutes** — flight prices change, but not second-by-second.

---

## 5. Staying invisible: anti-detection and the law

### Post-quantum TLS — the detection vector nobody talks about

The most significant anti-detection development in 2025-2026 is **post-quantum TLS fingerprinting**. Chrome enabled post-quantum key exchange (X25519MLKEM768) by default in April 2024; Firefox followed in November 2024. Akamai made PQ the default for all connections in January 2026. Scraping traffic without a PQ key share now creates a fingerprint mismatch against Cloudflare's and Akamai's known-good browser databases. Action required: stop pinning pre-PQ Chrome fingerprints (HelloChrome_120 is now detectable) and use **HelloChrome_131+** with X25519MLKEM768 in `curl_cffi`.

### The coherence principle

The cardinal rule of anti-detection is **coherence, not randomness**. Anti-bot systems evaluate consistency across all signal layers simultaneously. A Chrome 131 profile on Windows must look internally consistent across JavaScript APIs (navigator, canvas, WebGL, AudioContext), network signatures (JA4 hash, HTTP/2 pseudo-header order), and behavioral patterns (mouse movements, scroll cadence, timing). Random noise across sessions is itself a detection signal.

Practically, this means: tie each proxy IP to a single cookie jar, fingerprint, and User-Agent — one "identity." Never reuse the same session across different proxy IPs (Cloudflare detects cookie/IP mismatches). Use **residential proxies** ($5-15/GB) — datacenter IPs are flagged almost instantly by Akamai on travel sites. For European flight scraping, use geo-targeted proxies matching the market (a German proxy for EUR German-market pricing, a UK proxy for GBP).

### Safe request rates

For flight aggregators (Google Flights, Skyscanner), **1-3 requests per minute per IP** is conservative; 5-10 is moderate. For direct airline sites (Ryanair), stay at **1 request per minute**. Use Poisson-distributed delays rather than fixed intervals: `delay = -mean_delay * ln(random())`. Retire sessions after 10-15 page loads. Implement exponential backoff on 429/403 errors (5s → 10s → 20s → 40s).

Required headers beyond User-Agent include `sec-ch-ua` (must match claimed browser version), `sec-ch-ua-platform`, `sec-fetch-dest`, `sec-fetch-mode`, `Accept-Language`, and `Accept-Encoding`. HTTP/2 pseudo-header order matters: Chrome uses `m,a,s,p` (method, authority, scheme, path) — Akamai fingerprints this. The User-Agent string must match the TLS fingerprint: claiming "Chrome 131" with a Python `requests` TLS signature is an instant block.

### Legal reality in the EU

Flight prices are **non-personal data** and generally fall outside GDPR. However, the legal landscape is nuanced. In **Ryanair v PR Aviation** (CJEU, Case C-30/14, January 2015), the Court ruled that website operators can prohibit screen scraping through enforceable Terms of Service when their database isn't protected by IP rights — paradoxically giving unprotected databases potentially greater contractual protection. In **Ryanair v Flightbox** (Irish High Court, December 2023), a permanent injunction prohibited scraping based on breach of binding Terms of Use.

The **Ryanair v Booking.com** saga took a dramatic turn: a July 2024 jury found Booking.com violated the US CFAA with "intent to defraud" (awarding the statutory minimum $5,000), but in January 2025, the judge **overturned** the verdict entirely. Booking.com plans to appeal.

The safest legal position: scraping publicly visible, non-personal flight price data is likely permissible under EU law, but **ToS violations can create contract law liability**. Respect `robots.txt` (non-compliance is evidence of bad faith), cache aggressively to minimize server impact, scrape during off-peak hours (00:00-06:00 local time), and store only structured non-personal data (route, price, airline, date) — delete raw HTML after extraction.

---

## 6. Keeping scrapers alive when everything changes

### What breaks and how to detect it

Major flight booking sites update their frontend **every 2-6 weeks**. The most common failure modes are CAPTCHA walls appearing when detection thresholds change, API version rotations (Wizz Air's URL-embedded version changes every few weeks), currency mismatches from proxy geolocation shifts, and empty results that look like "no flights" but are actually blocked responses.

Build monitoring around five signals: **data volume drops** (>20% decline from rolling average = breakage), **HTTP error rate spikes** (>5% 403/429/503 = detection), **price anomalies** (>3 standard deviations from route mean = parsing error), **schema drift** (unexpected fields appearing or disappearing), and **cross-source divergence** (>30% price discrepancy between sources = one source is broken).

### Schema validation with Pydantic

Validate every scraped result against strict Pydantic models with field-level constraints: IATA codes as `regex=r'^[A-Z]{3}$'`, prices with `gt=0, lt=50000` sanity bounds, currencies as ISO 4217, and a validator ensuring arrival time is after departure time. Detect currency mismatches by cross-referencing returned currency against expected currency for the market — if scraping a EUR market and suddenly getting HUF prices, flag immediately. Monitor for duplicate prices (every flight on a route at the same price = parsing failure).

### The resilience playbook

Use **API-level scraping over HTML parsing** whenever possible — APIs change less frequently than UI elements. When you must scrape rendered pages, intercept XHR/GraphQL/Protobuf network requests rather than parsing the DOM. Use semantic selectors (data-* attributes, ARIA roles) rather than CSS class names. For Wizz Air's version-rotating API, dynamically discover the current version from the site's JavaScript bundles before making API calls. Implement circuit breaker patterns per source: if Google Flights returns errors 3 times in a row, fall back to Amadeus.

---

## 7. The graveyard: what has been tried and failed

### Dead APIs and broken tools

**Google QPX Express API** shut down April 10, 2018. Google acquired ITA Software for $700M in 2011, launched QPX Express in 2013 ($0.035/query), and killed it citing "low interest among travel partners." The DOJ-mandated 5-year public access period expired in April 2016. **Nothing replaced it publicly.** Developers who built on QPX Express (multiple GitHub repos from 2013-2017 with 25+ stars) lost their data source overnight.

**Skyscanner's public API and Python SDK** were deprecated May 1, 2020. The official repo (`Skyscanner/skyscanner-python-sdk`, **~500 stars**) is archived and throws 403 Forbidden errors. Skyscanner killed its direct affiliate program in late 2017, forcing partners to Commission Junction by January 2018. The current B2B API (v3) requires partner approval with no open access.

**FlareSolverr** (GitHub: `FlareSolverr/FlareSolverr`) was the go-to Cloudflare bypass proxy. The team has indicated they will **no longer actively maintain it**. Success rate dropped from >90% to **<30%** against current Cloudflare challenges. Its replacement is **Byparr** (uses Camoufox under the hood).

**`puppeteer-extra-plugin-stealth`** was effectively deprecated in February 2025. Cloudflare updated its detection to specifically identify this library's fingerprint modifications. **`undetected-chromedriver`** broke with Chrome ≥115 (2023) when Google changed ChromeDriver distribution URLs; the maintainer shifted focus to `nodriver` as the successor.

### Known dead ends to avoid

**Simple `requests`-based scraping** is completely dead for all major flight sites. A `requests.get()` returns empty HTML shells — every flight site requires full JavaScript rendering. **Datacenter proxies** are flagged "almost instantly" by Akamai on travel sites — residential proxies are mandatory, at ~10x the cost. **Building a single-source scraper** guarantees missed routes and promotional fares — multi-source is mandatory. **Expecting stable HTML selectors** leads to constant breakage (2-6 week redesign cycles) — intercept API calls instead of parsing DOM. **Caching flight data longer than 30 minutes** produces stale prices due to dynamic pricing algorithms that adjust continuously. And finally, **ignoring legal risk** is dangerous: Ryanair has won permanent injunctions against scrapers (Flightbox, December 2023) and actively litigates against unauthorized data extraction.

---

## Conclusion: the practical path forward

The 2026 flight scraping landscape has consolidated around a few viable strategies. **For a Claude Code agent**, the optimal architecture starts with `fli`'s MCP server for Google Flights (free, no browser, Protobuf-based), adds `ryanair-py` for direct Ryanair fares, and supplements with Transavia's official API and Amadeus Self-Service for broader coverage. This combination, with SQLite price tracking and Pydantic validation, covers roughly 95% of European LCC routes without any browser automation.

For the remaining 5% — Wizz Air promotions, Volotea niche routes, easyJet flash sales — **Camoufox** with Playwright's API represents the current stealth ceiling (0% detection on CreepJS), while **Patchright** offers the easiest path for Playwright users (one-line import change). Budget $5-15/GB for residential proxies and pace at 1-3 requests per minute per IP. The most important insight from this research is that the era of "just scrape everything with Selenium" is definitively over — the winners are developers who reverse-engineer APIs rather than automate browsers, and who treat anti-bot systems as adversaries deserving genuine respect.