# farepy.util

Internal utilities for farepy.

### Functions

| [`check_api_key`](#farepy.util.check_api_key)(env_var, \*, service_name, ...)   | Check for an API key, returning (value, message).             |
|--------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| [`extract_time`](#farepy.util.extract_time)(iso_datetime)                      | Extract HH:MM from an ISO 8601 datetime string.               |
| [`now_iso`](#farepy.util.now_iso)()                                       | Return current UTC time as ISO 8601 string.                   |
| [`parse_iso_duration`](#farepy.util.parse_iso_duration)(duration)                    | Parse ISO 8601 duration string to minutes.                    |
| [`parse_leg`](#farepy.util.parse_leg)(leg)                                  | Parse a leg string like 'MRS-REK' into (origin, destination). |
| [`reformat_date`](#farepy.util.reformat_date)(date_str, \*[, to_kiwi])          | Convert between date formats.                                 |
| [`time_in_range`](#farepy.util.time_in_range)(time_str, \*[, after, before])    | Check if a HH:MM time falls within the given range.           |

### farepy.util.check_api_key(env_var, , service_name, signup_url, explicit_value=None)

Check for an API key, returning (value, message).

Checks explicit_value first, then the environment variable.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### farepy.util.extract_time(iso_datetime)

Extract HH:MM from an ISO 8601 datetime string.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> extract_time('2026-04-18T06:30:00')
'06:30'
```

### farepy.util.now_iso()

Return current UTC time as ISO 8601 string.

The format is fixed: second precision with a literal trailing `Z`, never
a numeric offset. Callers stamp it onto `SearchResult.searched_at` and
the cache parses it back, so the shape must not drift – and the clock call
behind it must not be a deprecated one.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> import re, warnings
>>> with warnings.catch_warnings():
...     warnings.simplefilter("error", DeprecationWarning)
...     s = now_iso()
>>> bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", s))
True
```

### farepy.util.parse_iso_duration(duration)

Parse ISO 8601 duration string to minutes.

* **Return type:**
  [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

```pycon
>>> parse_iso_duration('PT2H30M')
150
>>> parse_iso_duration('PT45M')
45
>>> parse_iso_duration('PT1H')
60
```

### farepy.util.parse_leg(leg)

Parse a leg string like ‘MRS-REK’ into (origin, destination).

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> parse_leg('MRS-REK')
('MRS', 'REK')
```

### farepy.util.reformat_date(date_str, , to_kiwi=False)

Convert between date formats.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> reformat_date('2026-04-18', to_kiwi=True)
'18/04/2026'
>>> reformat_date('18/04/2026')
'2026-04-18'
```

### farepy.util.time_in_range(time_str, , after=None, before=None)

Check if a HH:MM time falls within the given range.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

```pycon
>>> time_in_range('14:30', after='08:00', before='18:00')
True
>>> time_in_range('06:00', after='08:00')
False
```
