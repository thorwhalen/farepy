# farepy.sources

Flight data source registry.

### Functions

| [`available_sources`](#farepy.sources.available_sources)(\*\*kwargs)   | Return status of all sources.                            |
|----------------------------------------------------------------------------------|----------------------------------------------------------|
| [`make_source`](#farepy.sources.make_source)(name, \*\*kwargs)   | Create a source instance by name, passing config kwargs. |

### farepy.sources.available_sources(\*\*kwargs)

Return status of all sources.

Each dict has: name, available (bool), message (str).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

### farepy.sources.make_source(name, \*\*kwargs)

Create a source instance by name, passing config kwargs.

### Modules

| [`google_flights_source`](farepy.sources.google_flights_source.html.md#module-farepy.sources.google_flights_source)   | Google Flights source via the fast-flights library.              |
|----------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| [`kayak_source`](farepy.sources.kayak_source.html.md#module-farepy.sources.kayak_source)                     | Kayak flight search adapter using playwright browser automation. |
| [`ryanair_source`](farepy.sources.ryanair_source.html.md#module-farepy.sources.ryanair_source)                 | Ryanair source via the ryanair-py library.                       |
