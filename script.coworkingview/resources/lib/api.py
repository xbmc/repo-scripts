"""Read the public CoworkingView Price Index.

The only request this module makes is ``GET /v1/market/rates`` on
``https://api.coworkingview.com``. That is the same call the other clients
in this repository use for ``rates()`` and ``cities()``.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

BASE_URL = "https://api.coworkingview.com"
RATES_PATH = "/v1/market/rates"
VERSION = "1.0.0"
USER_AGENT = (
    "script.coworkingview/" + VERSION + " (+https://github.com/coworkingview/flex-office-data)"
)
TIMEOUT = 20
FALLBACK_WAIT = 2.0
MAX_WAIT = 10.0

LOCALES = ("en", "es", "de")
CURRENCIES = ("EUR", "GBP", "USD", "CHF", "AED")
PRODUCT_ORDER = (
    "flex_desk",
    "fix_desk",
    "private_office",
    "exclusive_bereich",
    "day_pass",
    "meeting_room",
    "event_space",
    "virtual_office",
    "membership",
)
STAT_UNITS = {
    "day_pass": "day",
    "meeting_room": "hour",
    "event_space": "hour",
    "virtual_office": "month",
}
LOW_CONFIDENCE_BELOW = 10
RATE_COLUMNS = (
    "city_slug",
    "city_name",
    "country_code",
    "currency",
    "product",
    "unit",
    "median",
    "p25",
    "p75",
    "sample_size",
    "property_count",
    "operator_count",
    "low_confidence",
    "as_of",
)


class CoworkingViewError(Exception):
    """A failed Price Index read. ``code`` is for the add-on, not for display."""

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail if isinstance(detail, str) else ""
        super().__init__(self.detail or code)


class ApiError(CoworkingViewError):
    """HTTP problem body from ``GET /v1/market/rates``."""

    def __init__(self, status, code, title, detail):
        self.status = status
        self.title = title if isinstance(title, str) else ""
        problem = code if isinstance(code, str) and code else "HTTP_{0}".format(status)
        text = detail if isinstance(detail, str) else ""
        super().__init__("http", text or self.title or problem)
        self.problem_code = problem


def snake(key):
    """``dayPass`` to ``day_pass``."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()


def _amount(money):
    if money is None:
        return None
    return money["amount"]


def _is_stat(value):
    return isinstance(value, dict) and "median" in value and "sampleSize" in value


def _product_key(product):
    if product in PRODUCT_ORDER:
        return (0, PRODUCT_ORDER.index(product), "")
    return (1, 0, product)


def rate_rows(data):
    """One row per published city and product. Unpublished cities are skipped."""
    rows = []
    for city in data.get("cities") or []:
        base = {
            "city_slug": city["city"]["slug"],
            "city_name": city["city"]["name"],
            "country_code": city.get("countryCode"),
            "currency": city["currency"],
        }
        for item in city.get("figures") or city.get("byType") or []:
            rows.append(
                {
                    "city_slug": base["city_slug"],
                    "city_name": base["city_name"],
                    "country_code": base["country_code"],
                    "currency": base["currency"],
                    "product": item["optionType"],
                    "unit": "month",
                    "median": _amount(item["median"]),
                    "p25": _amount(item.get("p25")),
                    "p75": _amount(item.get("p75")),
                    "sample_size": item["sampleSize"],
                    "property_count": item.get("propertyCount"),
                    "operator_count": item.get("operatorCount"),
                }
            )
        for key, value in city.items():
            if not _is_stat(value):
                continue
            product = snake(key)
            rows.append(
                {
                    "city_slug": base["city_slug"],
                    "city_name": base["city_name"],
                    "country_code": base["country_code"],
                    "currency": base["currency"],
                    "product": product,
                    "unit": STAT_UNITS.get(product),
                    "median": _amount(value["median"]),
                    "p25": _amount(value.get("p25")),
                    "p75": _amount(value.get("p75")),
                    "sample_size": value["sampleSize"],
                    "property_count": value.get("propertyCount"),
                    "operator_count": value.get("operatorCount"),
                }
            )
    as_of = data.get("asOf")
    for row in rows:
        row["low_confidence"] = row["sample_size"] < LOW_CONFIDENCE_BELOW
        row["as_of"] = as_of
    rows.sort(key=lambda row: (row["city_slug"], _product_key(row["product"])))
    return [{column: row[column] for column in RATE_COLUMNS} for row in rows]


def parse_index(payload):
    """Cities and price-index rows from a ``/v1/market/rates`` JSON object."""
    if not isinstance(payload, dict):
        raise CoworkingViewError("bad_response")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise CoworkingViewError("bad_response")
    try:
        rows = rate_rows(data)
    except (KeyError, TypeError) as err:
        raise CoworkingViewError("bad_response", str(err)) from err

    cities = []
    for city in data.get("cities") or []:
        if not isinstance(city, dict):
            continue
        inner = city.get("city")
        if not isinstance(inner, dict):
            continue
        slug = inner.get("slug")
        name = inner.get("name")
        if not isinstance(slug, str) or not isinstance(name, str):
            continue
        country = city.get("countryCode")
        currency = city.get("currency")
        cities.append(
            {
                "slug": slug,
                "name": name,
                "country_code": country if isinstance(country, str) else None,
                "currency": currency if isinstance(currency, str) else None,
            }
        )
    cities.sort(key=lambda item: (item["name"].casefold(), item["slug"]))
    attribution = data.get("attribution")
    license_url = data.get("licenseUrl")
    as_of = data.get("asOf")
    return {
        "cities": cities,
        "rows": rows,
        "attribution": attribution if isinstance(attribution, str) else "",
        "license": license_url if isinstance(license_url, str) else "",
        "as_of": as_of if isinstance(as_of, str) else "",
    }


def rows_for_city(document, slug):
    return [row for row in document["rows"] if row["city_slug"] == slug]


def cities_with_rates(document):
    """Published cities that have at least one Price Index product row."""
    slugs = {row["city_slug"] for row in document["rows"]}
    return [city for city in document["cities"] if city["slug"] in slugs]


def _header(headers, name):
    if not headers:
        return None
    getter = getattr(headers, "get", None)
    if getter is None:
        return None
    direct = getter(name)
    if direct is not None:
        return direct
    lowered = name.lower()
    items = getattr(headers, "items", None)
    if items is None:
        return None
    for key, value in items():
        if str(key).lower() == lowered:
            return value
    return None


def _delay_seconds(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return max(0.0, float(text))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def retry_wait_seconds(headers):
    """Seconds to wait before the single retry, never more than 10."""
    wait = _delay_seconds(_header(headers, "Retry-After"))
    if wait is None:
        wait = _delay_seconds(_header(headers, "RateLimit-Reset"))
    if wait is None:
        wait = FALLBACK_WAIT
    return min(wait, MAX_WAIT)


def rates_url(locale, currency=None):
    """Absolute URL for ``GET /v1/market/rates``. ``currency`` is omitted when unset."""
    if locale not in LOCALES:
        raise CoworkingViewError("bad_request")
    if currency is not None and currency not in CURRENCIES:
        raise CoworkingViewError("bad_request")
    pairs = [("locale", locale)]
    if currency:
        pairs.append(("currency", currency))
    return BASE_URL + RATES_PATH + "?" + urllib.parse.urlencode(pairs)


def _problem(status, reason, raw):
    body = None
    try:
        body = json.loads(raw.decode("utf-8")) if raw else None
    except (UnicodeDecodeError, ValueError):
        body = None
    if not isinstance(body, dict):
        body = {}
    title = body.get("title")
    detail = body.get("detail")
    code = body.get("code")
    return ApiError(
        status,
        code if isinstance(code, str) else "",
        title if isinstance(title, str) else (reason or ""),
        detail if isinstance(detail, str) else "",
    )


def _decode(status, reason, raw):
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as err:
        raise CoworkingViewError("bad_response") from err
    if not isinstance(payload, dict):
        raise CoworkingViewError("bad_response")
    return payload


def _read_response(response):
    status = getattr(response, "status", None) or response.getcode()
    reason = getattr(response, "reason", "") or ""
    return int(status), str(reason), response.headers, response.read()


def fetch_index(locale, currency=None, urlopen=None, sleeper=None):
    """GET the Price Index once, with one retry on HTTP 429 or 5xx.

    ``urlopen`` and ``sleeper`` exist so tests can avoid the network.
    Nothing in this module runs a request at import time.
    """
    url = rates_url(locale, currency)
    opener = urlopen or urllib.request.urlopen
    pause = sleeper or time.sleep
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        method="GET",
    )
    for attempt in (1, 2):
        try:
            with opener(request, timeout=TIMEOUT) as response:
                status, reason, headers, raw = _read_response(response)
        except urllib.error.HTTPError as err:
            raw = err.read()
            status, reason, headers = err.code, str(err.reason or ""), err.headers
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            reason = getattr(err, "reason", err)
            raise CoworkingViewError("unreachable", str(reason)) from err

        if 200 <= status <= 299:
            return parse_index(_decode(status, reason, raw))
        if attempt == 1 and (status == 429 or 500 <= status <= 599):
            pause(retry_wait_seconds(headers))
            continue
        raise _problem(status, reason, raw)
    raise CoworkingViewError("unreachable")
