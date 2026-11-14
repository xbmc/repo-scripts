"""City picker and Price Index text view. Every label comes from strings.po."""

from __future__ import annotations

import xbmc
import xbmcaddon
import xbmcgui

import api

ADDON = xbmcaddon.Addon()

PRODUCT_STRINGS = {
    "flex_desk": 32037,
    "fix_desk": 32038,
    "private_office": 32039,
    "exclusive_bereich": 32040,
    "day_pass": 32041,
    "meeting_room": 32042,
    "event_space": 32043,
    "virtual_office": 32044,
    "membership": 32045,
}
UNIT_STRINGS = {
    "month": 32046,
    "day": 32047,
    "hour": 32048,
}
ERROR_STRINGS = {
    "unreachable": 32023,
    "bad_response": 32050,
    "http": 32023,
    "bad_request": 32023,
}


def text(string_id):
    return ADDON.getLocalizedString(string_id)


def log(message):
    xbmc.log("script.coworkingview: {0}".format(message), xbmc.LOGDEBUG)


def _sleep(seconds):
    xbmc.sleep(int(max(0.0, seconds) * 1000))


def _amount(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _product_label(product):
    string_id = PRODUCT_STRINGS.get(product)
    if string_id is None:
        return product
    return text(string_id)


def _unit_label(unit):
    string_id = UNIT_STRINGS.get(unit)
    if string_id is None:
        return ""
    return text(string_id)


def _preferences():
    locale = ADDON.getSetting("locale")
    if locale not in api.LOCALES:
        locale = "en"
    currency = ADDON.getSetting("currency")
    if currency not in api.CURRENCIES:
        currency = None
    return locale, currency


def _fail(code, detail):
    lead = text(ERROR_STRINGS.get(code, 32023))
    body = lead
    if detail:
        body = lead + "\n" + detail
    xbmcgui.Dialog().ok(ADDON.getAddonInfo("name"), body)


def _city_label(city):
    if city["country_code"]:
        return text(32025).format(name=city["name"], code=city["country_code"])
    return text(32026).format(name=city["name"])


def _report(city, rows, document):
    lines = []
    if document.get("as_of"):
        lines.append(text(32028).format(date=document["as_of"]))
        lines.append("")
    for row in rows:
        label = _product_label(row["product"])
        median = _amount(row["median"])
        currency = row["currency"] or ""
        unit = _unit_label(row["unit"])
        if unit:
            lines.append(
                text(32029).format(label=label, median=median, currency=currency, unit=unit)
            )
        else:
            lines.append(text(32030).format(label=label, median=median, currency=currency))
        if row["p25"] is not None and row["p75"] is not None:
            lines.append(
                text(32031).format(
                    p25=_amount(row["p25"]),
                    p75=_amount(row["p75"]),
                    currency=currency,
                    count=row["sample_size"],
                )
            )
        else:
            lines.append(text(32032).format(count=row["sample_size"]))
        if row["property_count"] is not None and row["operator_count"] is not None:
            lines.append(
                text(32034).format(spaces=row["property_count"], operators=row["operator_count"])
            )
        elif row["property_count"] is not None:
            lines.append(text(32035).format(spaces=row["property_count"]))
        elif row["operator_count"] is not None:
            lines.append(text(32036).format(operators=row["operator_count"]))
        if row["low_confidence"]:
            lines.append(text(32033))
        lines.append("")
    attribution = document.get("attribution") or ""
    license_url = document.get("license") or ""
    if attribution:
        lines.append(attribution)
    if license_url and license_url not in attribution:
        lines.append(license_url)
    heading = text(32027).format(city=city["name"])
    xbmcgui.Dialog().textviewer(heading, "\n".join(lines).strip())


def run():
    locale, currency = _preferences()
    progress = xbmcgui.DialogProgress()
    progress.create(ADDON.getAddonInfo("name"), text(32022))
    try:
        document = api.fetch_index(locale, currency, sleeper=_sleep)
    except api.CoworkingViewError as err:
        log("{0} {1}".format(err.code, err.detail))
        progress.close()
        visible = err.detail if err.code in ("http", "unreachable") else ""
        _fail(err.code, visible)
        return
    except Exception as err:
        log(type(err).__name__)
        progress.close()
        _fail("unreachable", "")
        return
    canceled = progress.iscanceled()
    progress.close()
    if canceled:
        return

    cities = api.cities_with_rates(document)
    if not cities:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo("name"), text(32024))
        return

    saved = ADDON.getSetting("city")
    labels = [_city_label(city) for city in cities]
    preselect = 0
    for index, city in enumerate(cities):
        if city["slug"] == saved:
            preselect = index
            break
    chosen = xbmcgui.Dialog().select(text(32021), labels, preselect=preselect)
    if chosen < 0:
        return
    city = cities[chosen]
    ADDON.setSetting("city", city["slug"])
    rows = api.rows_for_city(document, city["slug"])
    if not rows:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo("name"), text(32049))
        return
    _report(city, rows, document)
