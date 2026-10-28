"""Weather channel: a retro 'local forecast' in the spirit of the 90s cable
weather crawl.

Data comes from (in order, configurable in Settings):
  * Kodi's own weather service (Settings > Services > Weather), or
  * Open-Meteo (free, no API key) for a city / "lat,lon" you type in.
"""
import json
import threading
import time

try:
    from urllib.request import urlopen, Request
    from urllib.parse import quote
except ImportError:  # pragma: no cover
    from urllib2 import urlopen, Request
    from urllib import quote

import xbmc
import xbmcgui

from . import kodiutil as K
from .kodiutil import _

PAGES = ("current", "forecast", "extended", "almanac")
PAGE_SECS = 10
REFRESH_SECS = 15 * 60
ICON = "resource://resource.images.weathericons.default/%s.png"

# WMO weather code -> (text, kodi icon day, kodi icon night)
WMO = {
    0: (_("Sunny"), 32, 31), 1: (_("Mostly Sunny"), 34, 33), 2: (_("Partly Cloudy"), 30, 29),
    3: (_("Cloudy"), 26, 26), 45: (_("Fog"), 20, 20), 48: (_("Freezing Fog"), 20, 20),
    51: (_("Light Drizzle"), 9, 9), 53: (_("Drizzle"), 9, 9), 55: (_("Heavy Drizzle"), 9, 9),
    56: (_("Freezing Drizzle"), 8, 8), 57: (_("Freezing Drizzle"), 8, 8),
    61: (_("Light Rain"), 11, 11), 63: (_("Rain"), 12, 12), 65: (_("Heavy Rain"), 12, 12),
    66: (_("Freezing Rain"), 10, 10), 67: (_("Freezing Rain"), 10, 10),
    71: (_("Light Snow"), 14, 14), 73: (_("Snow"), 16, 16), 75: (_("Heavy Snow"), 16, 16), 77: (_("Snow Grains"), 13, 13),
    80: (_("Rain Showers"), 11, 11), 81: (_("Rain Showers"), 12, 12), 82: (_("Heavy Showers"), 12, 12),
    85: (_("Snow Showers"), 14, 14), 86: (_("Snow Showers"), 14, 14),
    95: (_("Thunderstorms"), 4, 4), 96: (_("T-Storms & Hail"), 3, 3), 99: (_("Severe T-Storms"), 3, 3),
}
COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def _clock(ts):
    try:
        f = xbmc.getRegion("time").replace(":%S", "")
    except Exception:
        f = "%I:%M %p"
    s = time.strftime(f, time.localtime(ts))
    return s[1:] if s.startswith("0") else s


def _hour(ts):
    s = time.strftime("%I %p", time.localtime(ts))
    return s[1:] if s.startswith("0") else s


def fahrenheit():
    pref = K.setting_int("weather_units", 0)  # 0 auto, 1 fahrenheit, 2 celsius
    if pref == 1:
        return True
    if pref == 2:
        return False
    try:
        return "F" in xbmc.getRegion("tempunit")
    except Exception:
        return True


def _get_json(url):
    req = Request(url, headers={"User-Agent": "CableBox42-Kodi"})
    with urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode("utf-8"))


# ------------------------------------------------------------------ sources
def from_kodi():
    """Normalised data from Kodi's weather service, or None."""
    if not xbmc.getCondVisibility("Weather.IsFetched"):
        xbmc.executebuiltin("Weather.Refresh")
        return None
    W = xbmcgui.Window(12600)
    g = W.getProperty
    unit = xbmc.getInfoLabel("System.TemperatureUnits") or ""

    def t(v):
        v = (v or "").strip()
        return v + unit if v and v.lstrip("-").replace(".", "").isdigit() else v

    def pct(v):
        v = (v or "").strip()
        return v + "%" if v and v.isdigit() else v

    d = {"location": xbmc.getInfoLabel("Weather.Location") or g("Location"),
         "now": {"temp": xbmc.getInfoLabel("Weather.Temperature") or t(g("Current.Temperature")),
                 "cond": g("Current.Condition") or xbmc.getInfoLabel("Weather.Conditions"),
                 "icon": g("Current.OutlookIcon") or xbmc.getInfoLabel("Weather.ConditionsIcon"),
                 "feels": t(g("Current.FeelsLike")), "humidity": pct(g("Current.Humidity")),
                 "wind": g("Current.Wind"), "dew": t(g("Current.DewPoint")),
                 "uv": g("Current.UVIndex"), "pressure": g("Current.Pressure")},
         "days": [], "hours": [],
         "sunrise": g("Today.Sunrise"), "sunset": g("Today.Sunset")}
    for i in range(1, 6):
        if g("Daily.%d.ShortDay" % i) or g("Daily.%d.HighTemperature" % i):
            d["days"].append({"name": g("Daily.%d.ShortDay" % i) or g("Daily.%d.LongDay" % i),
                              "hi": t(g("Daily.%d.HighTemperature" % i)),
                              "lo": t(g("Daily.%d.LowTemperature" % i)),
                              "cond": g("Daily.%d.Outlook" % i), "icon": g("Daily.%d.OutlookIcon" % i),
                              "pop": pct(g("Daily.%d.Precipitation" % i))})
    if not d["days"]:
        for i in range(0, 5):
            if not g("Day%d.Title" % i):
                break
            d["days"].append({"name": g("Day%d.Title" % i)[:3], "hi": t(g("Day%d.HighTemp" % i)),
                              "lo": t(g("Day%d.LowTemp" % i)), "cond": g("Day%d.Outlook" % i),
                              "icon": g("Day%d.OutlookIcon" % i), "pop": ""})
    for i in range(1, 7):
        if not g("Hourly.%d.Time" % i):
            break
        d["hours"].append({"time": g("Hourly.%d.Time" % i), "temp": t(g("Hourly.%d.Temperature" % i)),
                           "cond": g("Hourly.%d.Outlook" % i), "pop": pct(g("Hourly.%d.Precipitation" % i))})
    if not (d["now"]["temp"] or d["days"]):
        return None
    return d


def _geocode(place):
    st = K.load_json(K.STATE_FILE, {})
    cache = st.get("geocode", {})
    if place in cache:
        return cache[place]
    parts = [p.strip() for p in place.split(",")]
    try:
        if len(parts) == 2 and all(p.replace(".", "").lstrip("-").isdigit() for p in parts):
            hit = {"lat": float(parts[0]), "lon": float(parts[1]), "name": place}
        else:
            res = _get_json("https://geocoding-api.open-meteo.com/v1/search?count=5&language=en&name=%s"
                            % quote(parts[0]))
            results = res.get("results") or []
            if len(parts) > 1:  # "Dickson, TN" -> prefer matching admin/country
                want = parts[1].lower()
                results = [r for r in results if want in (r.get("admin1", "") + r.get("country_code", "") +
                                                          r.get("country", "")).lower()] or results
            if not results:
                return None
            r = results[0]
            hit = {"lat": r["latitude"], "lon": r["longitude"], "name": r.get("name", place)}
    except Exception as exc:
        K.log_err("geocode failed: %s" % exc)
        return None
    cache[place] = hit
    st["geocode"] = cache
    K.save_json(K.STATE_FILE, st)
    return hit


def from_open_meteo(place):
    loc = _geocode(place)
    if not loc:
        return None
    f = fahrenheit()
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
           "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,"
           "wind_speed_10m,wind_direction_10m,pressure_msl,is_day,dew_point_2m"
           "&hourly=temperature_2m,weather_code,precipitation_probability"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,"
           "precipitation_probability_max,uv_index_max"
           "&timezone=auto&forecast_days=6&timeformat=unixtime%s"
           % (loc["lat"], loc["lon"],
              "&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch" if f else ""))
    try:
        raw = _get_json(url)
    except Exception as exc:
        K.log_err("open-meteo failed: %s" % exc)
        return None
    return parse_open_meteo(raw, loc["name"], f)


def parse_open_meteo(raw, name, f):
    deg = u"°"
    spd = "mph" if f else "km/h"
    c = raw.get("current", {})
    code = int(c.get("weather_code", 3))
    text, iday, inight = WMO.get(code, ("", 26, 26))
    wd = c.get("wind_direction_10m")
    wind = _("Calm")
    if c.get("wind_speed_10m"):
        wind = "%s %d %s" % (COMPASS[int((wd or 0) / 22.5 + 0.5) % 16], round(c["wind_speed_10m"]), spd)
    pres = c.get("pressure_msl")
    if pres and f:
        pres = _("%.2f in") % (pres * 0.02953)
    elif pres:
        pres = _("%d hPa") % round(pres)
    dly = raw.get("daily", {})
    daily = []
    for i, ts in enumerate(dly.get("time", [])):
        dc = int(dly["weather_code"][i] or 3)
        dt, di, _night = WMO.get(dc, ("", 26, 26))
        daily.append({"name": time.strftime("%a", time.localtime(ts + 43200)), "ts": ts,
                      "hi": "%d%s" % (round(dly["temperature_2m_max"][i]), deg),
                      "lo": "%d%s" % (round(dly["temperature_2m_min"][i]), deg),
                      "cond": dt, "icon": ICON % di,
                      "pop": "%d%%" % (dly.get("precipitation_probability_max", [0] * 9)[i] or 0),
                      "rise": dly.get("sunrise", [None] * 9)[i], "set": dly.get("sunset", [None] * 9)[i],
                      "uv": dly.get("uv_index_max", [None] * 9)[i]})
    hrs = raw.get("hourly", {})
    now = time.time()
    hours = []
    for i, ts in enumerate(hrs.get("time", [])):
        if ts < now - 1800:
            continue
        if len(hours) >= 6:
            break
        hc = int(hrs["weather_code"][i] or 3)
        hours.append({"time": _hour(ts), "temp": "%d%s" % (round(hrs["temperature_2m"][i]), deg),
                      "cond": WMO.get(hc, ("",))[0],
                      "pop": "%d%%" % (hrs.get("precipitation_probability", [0] * 999)[i] or 0)})
    unit = deg + ("F" if f else "C")
    d = {"location": name,
         "now": {"temp": "%d%s" % (round(c.get("temperature_2m", 0)), unit), "cond": text,
                 "icon": ICON % (iday if c.get("is_day", 1) else inight),
                 "feels": "%d%s" % (round(c.get("apparent_temperature", 0)), deg),
                 "humidity": "%d%%" % round(c.get("relative_humidity_2m", 0)), "wind": wind,
                 "dew": "%d%s" % (round(c["dew_point_2m"]), deg) if c.get("dew_point_2m") is not None else "",
                 "uv": "%d" % round(daily[0]["uv"]) if daily and daily[0].get("uv") is not None else "",
                 "pressure": pres or ""},
         "days": daily[1:6] if len(daily) > 1 else daily, "today": daily[0] if daily else None,
         "hours": hours,
         "sunrise": _clock(daily[0]["rise"]) if daily and daily[0].get("rise") else "",
         "sunset": _clock(daily[0]["set"]) if daily and daily[0].get("set") else ""}
    return d


def narrative(d):
    """Old-school text forecast: TODAY... TONIGHT... TOMORROW..."""
    out = []
    today = d.get("today") or (d["days"][0] if d.get("days") else None)
    nxt = d["days"][0] if d.get("today") and d.get("days") else (d["days"][1] if len(d.get("days", [])) > 1 else None)
    hour = time.localtime().tm_hour
    if today:
        cond = (today.get("cond") or d["now"].get("cond") or "").lower()
        pop = today.get("pop", "")
        rain = (_(" Chance of precipitation %s.") % pop) if pop and pop not in ("0%", "") else ""
        if hour < 15:
            out.append(_("TODAY...%s. High %s.%s") % (cond.capitalize(), today.get("hi", ""), rain))
        out.append(_("TONIGHT...Low %s.") % today.get("lo", ""))
    if nxt:
        pop = nxt.get("pop", "")
        rain = (_(" Chance of precipitation %s.") % pop) if pop and pop not in ("0%", "") else ""
        out.append(_("%s...%s. High %s, low %s.%s") % (
            _("TOMORROW") if d.get("today") else nxt.get("name", "").upper(),
            (nxt.get("cond") or "").capitalize(), nxt.get("hi", ""), nxt.get("lo", ""), rain))
    return out


# ------------------------------------------------------------------ screen
class WeatherScreen(object):
    def __init__(self, win):
        self.win = win
        self.data = None
        self.fetched_at = 0
        self.fetching = False
        self.page_at = 0
        self.page = 0

    def _fetch(self):
        src = K.setting_int("weather_source", 0)  # 0 auto, 1 kodi only, 2 open-meteo only
        place = K.setting("weather_location", "").strip()
        d = None
        try:
            if src in (0, 1):
                d = from_kodi()
            if d is None and src != 1 and place:
                d = from_open_meteo(place)
        except Exception as exc:
            K.log_err("weather fetch: %s" % exc)
        if d:
            self.data = d
            self.fetched_at = time.time()
        else:
            self.fetched_at = time.time() - REFRESH_SECS + 60  # retry in a minute
        self.fetching = False
        self.render()

    def tick(self, now, force=False):
        if (force or now - self.fetched_at > REFRESH_SECS) and not self.fetching:
            self.fetching = True
            threading.Thread(target=self._fetch).start()
        if force:
            self.page = 0
            self.page_at = now + PAGE_SECS
            self.render()
        elif now >= self.page_at:
            self.page = (self.page + 1) % len(PAGES)
            self.page_at = now + PAGE_SECS
            self.render()

    def render(self):
        w = self.win
        P = w.setProperty
        P("wx_title", K.setting("weather_title", _("Your Local Forecast")))
        d = self.data
        if not d:
            P("wx_page", "nodata")
            P("wx_location", "")
            P("wx_ticker", _("Weather is not set up yet.   Choose a weather service in Kodi (Settings > "
                           "Services > Weather) or type your city in CableBox 42 > Settings > Weather."))
            return
        page = PAGES[self.page]
        P("wx_page", page)
        P("wx_location", d.get("location", ""))
        n = d["now"]
        P("wx_temp", n.get("temp", ""))
        P("wx_cond", n.get("cond", ""))
        P("wx_icon", n.get("icon", ""))
        rows = [(_("Humidity"), n.get("humidity")), (_("Dewpoint"), n.get("dew")), (_("Feels Like"), n.get("feels")),
                (_("Wind"), n.get("wind")), (_("Pressure"), n.get("pressure")), (_("UV Index"), n.get("uv"))]
        rows = [r for r in rows if r[1]][:6]
        P("wx_labels", "[CR]".join(r[0] + ":" for r in rows))
        P("wx_values", "[CR]".join(r[1] for r in rows))
        P("wx_text", "[CR][CR]".join(narrative(d)))
        days = d.get("days", [])[:4]
        for i in range(4):
            day = days[i] if i < len(days) else {}
            P("wx_d%d_name" % (i + 1), (day.get("name") or "").upper()[:3])
            P("wx_d%d_icon" % (i + 1), day.get("icon", ""))
            P("wx_d%d_cond" % (i + 1), day.get("cond", ""))
            P("wx_d%d_hi" % (i + 1), day.get("hi", ""))
            P("wx_d%d_lo" % (i + 1), day.get("lo", ""))
        hours = d.get("hours", [])[:6]
        P("wx_hours_t", "[CR]".join(h["time"] for h in hours))
        P("wx_hours_v", "[CR]".join(h["temp"] for h in hours))
        P("wx_hours_c", "[CR]".join("%s%s" % (h["cond"], ("   %s" % h["pop"]) if h.get("pop") and
                                                  h["pop"] != "0%" else "") for h in hours))
        P("wx_sun", (_("Sunrise  %s      Sunset  %s") % (d.get("sunrise"), d.get("sunset")))
          if d.get("sunrise") else "")
        P("wx_ticker", _("Conditions at %s:   %s   Temperature %s   Humidity %s   Wind %s      %s") % (
            d.get("location", ""), n.get("cond", ""), n.get("temp", ""), n.get("humidity", ""),
            n.get("wind", ""), "      ".join(narrative(d))))
