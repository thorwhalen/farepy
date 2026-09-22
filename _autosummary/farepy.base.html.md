# farepy.base

Normalized data model for multi-source flight search.

### Classes

| [`FlightOffer`](#farepy.base.FlightOffer)(source, outbound, price, ...[, ...])   | A single bookable flight option, normalized across all sources.   |
|-----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| [`FlightSource`](#farepy.base.FlightSource)(\*args, \*\*kwargs)                   | Protocol that all source adapters implement.                      |
| [`Itinerary`](#farepy.base.Itinerary)(segments[, duration_minutes])            | One direction of travel (outbound or return).                     |
| [`SearchRequest`](#farepy.base.SearchRequest)(origin, destination, ...[, ...])     | Normalized search parameters.                                     |
| [`SearchResult`](#farepy.base.SearchResult)(request, offers, ...[, cached])       | Container for search results with metadata.                       |
| [`Segment`](#farepy.base.Segment)(departure_airport, arrival_airport, ...)   | A single flight leg (one takeoff-to-landing).                     |

### *class* farepy.base.FlightOffer(source, outbound, price, currency, airlines, inbound=None, booking_url=None, raw=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A single bookable flight option, normalized across all sources.

### *class* farepy.base.FlightSource(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Protocol that all source adapters implement.

#### is_available()

Check availability. Returns (available, message).

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`bool`](https://docs.python.org/3/builtins/functions.html#bool), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

#### search(request)

Search for flights. Returns empty list on no results.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`FlightOffer`](#farepy.base.FlightOffer)]

### *class* farepy.base.Itinerary(segments, duration_minutes=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One direction of travel (outbound or return).

### *class* farepy.base.SearchRequest(origin, destination, departure_date, return_date=None, adults=1, currency='EUR', max_results=50, non_stop=None, outbound_departure_after=None, outbound_departure_before=None, outbound_arrival_after=None, outbound_arrival_before=None, inbound_departure_after=None, inbound_departure_before=None, inbound_arrival_after=None, inbound_arrival_before=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Normalized search parameters.

### *class* farepy.base.SearchResult(request, offers, sources_queried, sources_failed, searched_at, cached=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Container for search results with metadata.

### *class* farepy.base.Segment(departure_airport, arrival_airport, departure_time, arrival_time, carrier, carrier_name=None, flight_number=None, duration_minutes=None, aircraft=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A single flight leg (one takeoff-to-landing).
