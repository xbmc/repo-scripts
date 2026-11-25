"""Weather channel: a retro 'local forecast' in the spirit of the 90s cable
weather crawl.

Data comes from (in order, configurable in Settings):
  * Kodi's own weather service (Settings > Services > Weather), or
  * Open-Meteo (free, no API key) for a city / "lat,lon" you type in.
"""
import json
import math
import os
import re
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

PAGES = ("current", "observations", "forecast", "map", "extended", "almanac")
NEAR_PAGES = ("observations", "map")    # only with nearby cities (and their temperatures)
PAGE_SECS = 10
REFRESH_SECS = 15 * 60
NODATA_AFTER = 3.0          # seconds of blank screen before "weather is not set up"
ICON = "wx/%s.png"          # CableBox's own icons (skin media), so they always show

# WMO weather code (Open-Meteo) -> (text, icon by day, icon by night)
WMO = {
    0: (_("Sunny"), "sunny", "clear_night"), 1: (_("Mostly Sunny"), "mostly_sunny", "mostly_clear_night"),
    2: (_("Partly Cloudy"), "partly_cloudy", "partly_cloudy_night"), 3: (_("Cloudy"), "cloudy", "cloudy"),
    45: (_("Fog"), "fog", "fog"), 48: (_("Freezing Fog"), "fog", "fog"),
    51: (_("Light Drizzle"), "drizzle", "drizzle"), 53: (_("Drizzle"), "drizzle", "drizzle"),
    55: (_("Heavy Drizzle"), "drizzle", "drizzle"),
    56: (_("Freezing Drizzle"), "freezing_rain", "freezing_rain"), 57: (_("Freezing Drizzle"), "freezing_rain", "freezing_rain"),
    61: (_("Light Rain"), "rain", "rain"), 63: (_("Rain"), "rain", "rain"), 65: (_("Heavy Rain"), "heavy_rain", "heavy_rain"),
    66: (_("Freezing Rain"), "freezing_rain", "freezing_rain"), 67: (_("Freezing Rain"), "freezing_rain", "freezing_rain"),
    71: (_("Light Snow"), "snow", "snow"), 73: (_("Snow"), "snow", "snow"), 75: (_("Heavy Snow"), "heavy_snow", "heavy_snow"),
    77: (_("Snow Grains"), "snow", "snow"),
    80: (_("Rain Showers"), "rain", "rain"), 81: (_("Rain Showers"), "rain", "rain"),
    82: (_("Heavy Showers"), "heavy_rain", "heavy_rain"),
    85: (_("Snow Showers"), "snow", "snow"), 86: (_("Snow Showers"), "heavy_snow", "heavy_snow"),
    95: (_("Thunderstorms"), "thunderstorm", "thunderstorm"), 96: (_("T-Storms & Hail"), "thunderstorm", "thunderstorm"),
    99: (_("Severe T-Storms"), "thunderstorm", "thunderstorm"),
}

# Kodi's weather icon numbers (the codes weather add-ons report) -> our icons
KODI_ICONS = {}
for _names, _codes in (("thunderstorm", (0, 1, 2, 3, 4, 37, 38, 39, 45, 47)), ("sleet", (5, 6, 7, 18, 35)),
                       ("freezing_rain", (8, 10, 17)), ("drizzle", (9,)), ("rain", (11, 12, 40)),
                       ("snow", (13, 14, 15, 16, 42, 46)), ("heavy_snow", (41, 43)), ("fog", (19, 20, 21, 22)),
                       ("windy", (23, 24)), ("cloudy", (25, 26)), ("partly_cloudy_night", (27, 29)),
                       ("partly_cloudy", (28, 30, 44)), ("clear_night", (31,)), ("sunny", (32, 36)),
                       ("mostly_clear_night", (33,)), ("mostly_sunny", (34,))):
    for _c in _codes:
        KODI_ICONS[_c] = _names
# words in a condition -> icon, for anything without a usable icon number
WORD_ICONS = (("thunder", "thunderstorm"), ("t-storm", "thunderstorm"), ("sleet", "sleet"),
              ("freezing", "freezing_rain"), ("heavy snow", "heavy_snow"), ("snow", "snow"), ("flurr", "snow"),
              ("heavy rain", "heavy_rain"), ("drizzle", "drizzle"), ("rain", "rain"), ("shower", "rain"),
              ("fog", "fog"), ("mist", "fog"), ("haze", "fog"), ("smok", "fog"), ("wind", "windy"),
              ("breez", "windy"), ("partly", "partly_cloudy"), ("mostly cloudy", "cloudy"), ("cloud", "cloudy"),
              ("overcast", "cloudy"), ("mostly sunny", "mostly_sunny"), ("fair", "mostly_sunny"),
              ("clear", "sunny"), ("sun", "sunny"))


def icon(value, cond=""):
    """Our icon for whatever a weather source gave: one of ours, a Kodi
    weather icon (…/32.png), or failing that the words of the condition."""
    v = (value or "").strip()
    if v.startswith("wx/"):
        return v
    base = os.path.splitext(os.path.basename(v.replace("\\", "/")))[0]
    if base.isdigit() and int(base) in KODI_ICONS:
        return ICON % KODI_ICONS[int(base)]
    c = (cond or "").lower()
    for word, name in WORD_ICONS:
        if word in c:
            return ICON % name
    return ""
COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def _local(ts, off=None):
    """The time tuple of ts at the forecast's place: off = its UTC offset in seconds
    (Open-Meteo's utc_offset_seconds); None (Kodi's weather, an old cache): this box's."""
    if off is None:
        return time.localtime(ts)
    return time.gmtime(ts + off)


def _clock(ts, off=None):
    try:
        f = xbmc.getRegion("time").replace(":%S", "")
    except Exception:
        f = "%I:%M %p"
    s = time.strftime(f, _local(ts, off))
    return s[1:] if s.startswith("0") else s


def _hour(ts, off=None):
    s = time.strftime("%I %p", _local(ts, off))
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


# ------------------------------------------------------------------ cache
# Kept in its own file (not state.json, which the TV writes too) so a weather
# thread can never clobber the viewer's state.
CACHE_FILE = os.path.join(K.PROFILE, "weather_cache.json")
STALE_OK = 6 * 3600          # show a saved forecast up to 6 hours old if every source fails
COMPLETE = 4


def _cache():
    c = K.load_json(CACHE_FILE, {})
    return c if isinstance(c, dict) else {}


def _save_cache(c):
    try:
        K.save_json(CACHE_FILE, c)
    except Exception as exc:
        K.log_err("weather cache: %s" % exc)


def _where():
    """Which place the forecast is for: your city, or wherever Kodi's weather is set."""
    city = K.setting("weather_location", "").strip().lower()
    return ("city:" + city) if city else "kodi"


def remember(d):
    c = _cache()
    c["last"] = {"at": time.time(), "data": d, "where": _where()}
    _save_cache(c)


def last_good(max_age=STALE_OK):
    """The last forecast - only if it's for the place you're set to now
    (change the city and the old town's weather doesn't come back)."""
    hit = _cache().get("last") or {}
    if hit.get("where", "kodi") != _where():
        return None
    if hit.get("data") and time.time() - float(hit.get("at") or 0) < max_age:
        return hit["data"]
    return None


def quality(d):
    """How complete a forecast is: 0 (nothing) to 5 (current, days and hours)."""
    if not d:
        return 0
    n = d.get("now") or {}
    q = (1 if n.get("temp") else 0) + (1 if n.get("cond") else 0)
    q += 2 if len(d.get("days") or []) >= 3 else (1 if d.get("days") else 0)
    q += 1 if len(d.get("hours") or []) >= 3 else 0
    return q


def has_place():
    """The weather channel knows where you are: a city typed in, or Kodi's own
    weather set to a place."""
    return bool(K.setting("weather_location", "").strip() or kodi_place())


def kodi_place():
    """The location Kodi's weather service is set to, cleaned up for geocoding
    ('Springfield, IL (US)' -> 'Springfield, IL')."""
    try:
        loc = xbmc.getInfoLabel("Weather.Location") or xbmcgui.Window(12600).getProperty("Location") or ""
    except Exception:
        return ""
    return re.sub(r"\s*\(.*?\)\s*", " ", loc).strip(" ,")


def _geocode(place):
    st = _cache()
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
            if len(parts) > 1:  # "Springfield, IL" -> prefer matching admin/country
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
    st = _cache()
    st.setdefault("geocode", {})[place] = hit
    _save_cache(st)
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
    text, iday, inight = WMO.get(code, ("", "cloudy", "cloudy"))
    wd = c.get("wind_direction_10m")
    wind = _("Calm")
    if c.get("wind_speed_10m"):
        wind = "%s %d %s" % (COMPASS[int((wd or 0) / 22.5 + 0.5) % 16], round(c["wind_speed_10m"]), spd)
    pres = c.get("pressure_msl")
    if pres and f:
        pres = _("%.2f in") % (pres * 0.02953)
    elif pres:
        pres = _("%d hPa") % round(pres)
    # the place's own time: times come as Unix timestamps (timeformat=unixtime), so they're
    # formatted with its UTC offset, not this box's zone (Leeds watched from Chicago)
    off = raw.get("utc_offset_seconds")
    off = int(off) if isinstance(off, (int, float)) else None
    dly = raw.get("daily", {})
    daily = []
    for i, ts in enumerate(dly.get("time", [])):
        dc = int(dly["weather_code"][i] or 3)
        dt, di, _night = WMO.get(dc, ("", "cloudy", "cloudy"))
        daily.append({"name": time.strftime("%a", _local(ts + 43200, off)), "ts": ts,
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
        hours.append({"time": _hour(ts, off), "temp": "%d%s" % (round(hrs["temperature_2m"][i]), deg),
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
         "sunrise": _clock(daily[0]["rise"], off) if daily and daily[0].get("rise") else "",
         "sunset": _clock(daily[0]["set"], off) if daily and daily[0].get("set") else "",
         "utc_offset": off}
    return d


def narrative(d):
    """Old-school text forecast: TODAY... TONIGHT... TOMORROW..."""
    out = []
    today = d.get("today") or (d["days"][0] if d.get("days") else None)
    nxt = d["days"][0] if d.get("today") and d.get("days") else (d["days"][1] if len(d.get("days", [])) > 1 else None)
    off = d.get("utc_offset")                # missing in Kodi's data and old caches: this box's time
    hour = _local(time.time(), off if isinstance(off, (int, float)) else None).tm_hour
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


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception as exc:
        K.log_err("weather source %s: %s" % (getattr(fn, "__name__", fn), exc))
        return None


def fetch():
    """Best forecast available right now.

    Automatic, with a city typed in (setup asks for one): Open-Meteo for that
    city - your city wins over wherever Kodi's own weather happens to be set.
    Automatic, no city: Kodi's weather if it's complete; if it's missing,
    broken or half-filled, Open-Meteo for the place Kodi's weather is set to."""
    src = K.setting_int("weather_source", 0)  # 0 auto, 1 kodi only, 2 open-meteo only
    if src == 1:
        return _safe(from_kodi)
    city = K.setting("weather_location", "").strip()
    if src == 0 and city:
        # not Kodi's weather as a fallback: that's another town; the last
        # forecast for your city (kept by the weather screen) is better
        return _safe(from_open_meteo, city)
    kd = _safe(from_kodi) if src == 0 else None
    if quality(kd) >= COMPLETE:
        return kd
    place = city or kodi_place()
    om = _safe(from_open_meteo, place) if place else None
    if om and quality(om) >= quality(kd):
        return om
    return kd or om


# ------------------------------------------------------------------ nearby cities and the regional map
# Natural Earth populated places (public domain), trimmed to places of 50,000 or more
# by G:\CableBox42\rig\wx_prerender.py, which also draws the map tiles (media/wxmap).
PLACES_FILE = os.path.join(K.ADDON_PATH, "resources", "weather", "places.json")
MAP_INDEX = os.path.join(K.ADDON_PATH, "resources", "skins", "Default", "media", "wxmap", "index.json")
NEAR_RADII = (300, 450, 650, 900)    # km: widened in empty areas
NEAR_MAX, NEAR_WANT, NEAR_MIN = 8, 6, 3
NEAR_SELF = 20                       # km: your own city
NEAR_APART = 25                      # km between two cities picked (no suburbs of the same one)
_PLACES = []
_MAP = []


def places():
    if not _PLACES:
        try:
            with open(PLACES_FILE, encoding="utf-8") as f:
                _PLACES.append(json.load(f))
        except (IOError, OSError, ValueError) as exc:
            K.log_err("weather places: %s" % exc)
            _PLACES.append([])
    return _PLACES[0]


def km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 12742.0 * math.asin(min(1.0, math.sqrt(a)))


def nearby(lat, lon, own="", table=None):
    """[{name, lat, lon, km}] of 6-8 cities of 50,000+ near (lat, lon), nearest first,
    your own city left out; the radius widens in empty areas.  [] if fewer than 3."""
    own = (own or "").split(",")[0].strip().lower()
    rows = []
    for name, plat, plon, pop, cc in (table if table is not None else places()):
        if abs(plat - lat) > 9:
            continue
        d = km(lat, lon, plat, plon)
        if d <= NEAR_RADII[-1]:
            rows.append((d, -pop, name, plat, plon))
    rows.sort()
    for radius in NEAR_RADII:
        picked = []
        for d, _p, name, plat, plon in rows:
            if d > radius or len(picked) >= NEAR_MAX:
                break
            if d < NEAR_SELF or name.lower() == own:
                continue
            if any(km(plat, plon, c["lat"], c["lon"]) < NEAR_APART for c in picked):
                continue
            picked.append({"name": name, "lat": plat, "lon": plon, "km": round(d)})
        if len(picked) >= NEAR_WANT:
            return picked
    return picked if len(picked) >= NEAR_MIN else []


def from_open_meteo_many(cities, f):
    """Current temperature and sky for every city in one request (open-meteo takes
    comma-separated coordinates).  [{name, lat, lon, temp, cond, icon}] or None."""
    if not cities:
        return None
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
           "&current=temperature_2m,weather_code,is_day&timezone=auto%s"
           % (",".join("%.3f" % c["lat"] for c in cities), ",".join("%.3f" % c["lon"] for c in cities),
              "&temperature_unit=fahrenheit" if f else ""))
    try:
        raw = _get_json(url)
    except Exception as exc:
        K.log_err("open-meteo (nearby) failed: %s" % exc)
        return None
    if isinstance(raw, dict):
        raw = [raw]
    out = []
    for c, r in zip(cities, raw or []):
        cur = (r or {}).get("current") or {}
        if cur.get("temperature_2m") is None:
            continue
        text, iday, inight = WMO.get(int(cur.get("weather_code", 3)), ("", "cloudy", "cloudy"))
        out.append(dict(c, temp=u"%d\u00b0" % round(cur["temperature_2m"]), cond=text,
                        icon=ICON % (iday if cur.get("is_day", 1) else inight)))
    return out or None


def coordinates():
    """(lat, lon, name) of the forecast's place for the nearby pages, or None: a city
    typed in, else (Automatic) the place Kodi's weather is set to, geocoded.  Kodi's
    weather service only: None (that setting means no Open-Meteo at all)."""
    src = K.setting_int("weather_source", 0)
    if src == 1:
        return None
    place = K.setting("weather_location", "").strip() or kodi_place()
    loc = _geocode(place) if place else None
    if not loc:
        return None
    return loc["lat"], loc["lon"], loc.get("name") or place


def fetch_nearby():
    """{lat, lon, name, cities} with temperatures, or None."""
    where = coordinates()
    if not where:
        return None
    lat, lon, name = where
    near, (mapc, z) = nearby(lat, lon, name), map_cities(lat, lon, name)
    both = near + [c for c in mapc if c["name"] not in set(x["name"] for x in near)]
    obs = from_open_meteo_many(both, fahrenheit())      # one request for both pages
    if not obs:
        return None
    got = dict((c["name"], c) for c in obs)
    return {"lat": lat, "lon": lon, "name": name,
            "cities": [got[c["name"]] for c in near if c["name"] in got],
            "map": [got[c["name"]] for c in mapc if c["name"] in got], "z": z}


def remember_nearby(n):
    c = _cache()
    c["nearby"] = {"at": time.time(), "data": n, "where": _where()}
    _save_cache(c)


def last_nearby(max_age=STALE_OK):
    hit = _cache().get("nearby") or {}
    if hit.get("where", "kodi") != _where():
        return None
    if hit.get("data") and time.time() - float(hit.get("at") or 0) < max_age:
        return hit["data"]
    return None


def map_index():
    if not _MAP:
        try:
            with open(MAP_INDEX) as f:
                ix = json.load(f)
            ix["have"] = set((t[0], t[1]) for t in ix.get("tiles", []))
            _MAP.append(ix)
        except (IOError, OSError, ValueError) as exc:
            K.log_err("weather map: %s" % exc)
            _MAP.append(None)
    return _MAP[0]


MAP_VIEW = (116, 256, 1688, 672)     # the map's area on the 1080p screen: x, y, w, h (skin: the grouplist)
MAP_COLS, MAP_ROWS = 4, 3            # tile slots in the skin (ids 4101-4112)
MAP_ZOOM = (0.9, 2.4)                # screen px per tile px (times cos(lat) across)
MAP_MARGIN = (150, 110)              # room for a city's name and temperature
MAP_APART = (230, 150)               # two cities' labels closer than this: the later one goes
MAP_EDGE = (110, 95, 60)             # a city's label stays inside the map: x, top, bottom


MAP_RADII = (180, 260, 380, 550)     # km from you to the map's top/bottom edge: a close-in map first
MAP_CITIES = 8


def _zoom(lat, radius, ix, view=MAP_VIEW):
    """Screen px per tile px for a map whose top/bottom edge is radius km away."""
    vx, vy, vw, vh = view
    k = ix["width"] / 360.0
    ts = ix["tile"]
    c = max(0.2, math.cos(math.radians(lat)))
    z = (vh / 2.0 - MAP_MARGIN[1]) / (radius / 111.2 * k)
    zmin = max(MAP_ZOOM[0], vw / ((MAP_COLS - 1) * ts * c), vh / ((MAP_ROWS - 1) * ts))
    return max(zmin, min(MAP_ZOOM[1], z))


def _project(lat, lon, z, ix, view=MAP_VIEW):
    vx, vy, vw, vh = view
    k = ix["width"] / 360.0
    c = max(0.2, math.cos(math.radians(lat)))
    X, Y = (lon + 180) * k, (90 - lat) * k

    def screen(wx, wy):
        return vx + vw / 2.0 + (wx - X) * z * c, vy + vh / 2.0 + (wy - Y) * z
    return screen


def _fits(points, x, y, view=MAP_VIEW):
    vx, vy, vw, vh = view
    if not (vx + MAP_EDGE[0] <= x <= vx + vw - MAP_EDGE[0] and vy + MAP_EDGE[1] <= y <= vy + vh - MAP_EDGE[2]):
        return False
    return not any(abs(x - qx) < MAP_APART[0] and abs(y - qy) < MAP_APART[1] for qx, qy in points)


def map_cities(lat, lon, own="", table=None, ix=None):
    """(cities, zoom) for the regional map: the biggest places whose labels fit on
    screen without touching each other or yours, up to 8, on a close-in map first,
    wider in empty areas.  ([], 0) without the map's tiles or anything near."""
    ix = ix or map_index()
    if not ix:
        return [], 0
    own = (own or "").split(",")[0].strip().lower()
    rows = []
    for name, plat, plon, pop, cc in (table if table is not None else places()):
        if abs(plat - lat) > 9 or name.lower() == own:
            continue
        d = km(lat, lon, plat, plon)
        if NEAR_SELF <= d <= 1500:
            rows.append((-pop, name, plat, plon, d))
    rows.sort()
    best = ([], 0)
    for radius in MAP_RADII:
        z = _zoom(lat, radius, ix)
        k = ix["width"] / 360.0
        screen = _project(lat, lon, z, ix)
        taken = [screen((lon + 180) * k, (90 - lat) * k)]
        picked = []
        for _p, name, plat, plon, d in rows:
            x, y = screen((plon + 180) * k, (90 - plat) * k)
            if _fits(taken, x, y):
                taken.append((x, y))
                picked.append({"name": name, "lat": plat, "lon": plon, "km": round(d)})
                if len(picked) >= MAP_CITIES:
                    break
        if len(picked) > len(best[0]):
            best = (picked, z)
        if len(picked) >= NEAR_WANT:
            break
    return best if len(best[0]) >= NEAR_MIN else ([], 0)


def map_layout(lat, lon, cities, ix, z, view=MAP_VIEW):
    """Where the tiles and the cities go on screen, centred on (lat, lon), at zoom z
    (screen px per tile px; map_cities chose it).  Tiles: [(file, x, y, w, h)] (at
    most MAP_COLS x MAP_ROWS); points: [(city, x, y)].  Equirectangular tiles, drawn
    narrower by cos(lat) so the map isn't stretched sideways away from the equator."""
    vx, vy, vw, vh = view
    k = ix["width"] / 360.0
    ts = ix["tile"]
    c = max(0.2, math.cos(math.radians(lat)))
    sx, sy = z * c, z
    X, Y = (lon + 180) * k, (90 - lat) * k
    screen = _project(lat, lon, z, ix, view)
    tx0, ty0 = int((X - (vw / 2.0) / sx) // ts), int((Y - (vh / 2.0) / sy) // ts)
    tiles = []
    for ty in range(ty0, ty0 + MAP_ROWS):
        for tx in range(tx0, tx0 + MAP_COLS):
            if (tx, ty) not in ix["have"]:
                continue
            x0, y0 = screen(tx * ts, ty * ts)
            x1, y1 = screen((tx + 1) * ts, (ty + 1) * ts)
            if x1 < vx or x0 > vx + vw or y1 < vy or y0 > vy + vh:
                continue
            tiles.append(("wxmap/%d_%d.png" % (tx, ty), int(round(x0)), int(round(y0)),
                          int(round(x1)) - int(round(x0)), int(round(y1)) - int(round(y0))))
    points = []
    for p in cities:
        x, y = screen((p["lon"] + 180) * k, (90 - p["lat"]) * k)
        if p.get("home") or _fits([(qx, qy) for _q, qx, qy in points], x, y, view):
            points.append((p, int(round(x)), int(round(y))))
    return tiles, points


# ------------------------------------------------------------------ screen
MAP_TILE_IDS = list(range(4101, 4101 + MAP_COLS * MAP_ROWS))
MAP_CITY_IDS = list(range(4120, 4129))      # 0: your own city, then up to 8 others


class WeatherScreen(object):
    def __init__(self, win):
        self.win = win
        self.data = None
        self.fetched_at = 0
        self.fetching = False
        self.page_at = 0
        self.page = 0
        self.tuned_at = 0           # when the weather channel came on screen
        self.nodata_shown = False
        self.near = None            # nearby cities with temperatures (fetch_nearby)
        self.page_name = PAGES[0]

    def _fetch(self):
        try:
            d = fetch()
        except Exception as exc:          # never let the weather take the TV down
            K.log_err("weather fetch: %s" % exc)
            d = None
        try:
            n = fetch_nearby()
        except Exception as exc:
            K.log_err("weather nearby: %s" % exc)
            n = None
        if n:
            self.near = n
            remember_nearby(n)
        elif not self.near:
            self.near = last_nearby()      # the last good temperatures; none ever: the pages are skipped
        if d:
            self.data = d
            self.fetched_at = time.time()
            remember(d)
        else:
            if not self.data:
                self.data = last_good()     # an older forecast beats a blank screen
            self.fetched_at = time.time() - REFRESH_SECS + 60  # retry in a minute
        self.fetching = False
        self.render()

    def tick(self, now, force=False):
        if force:
            self.tuned_at = now
            self.nodata_shown = False
            if not self.data:
                self.data = last_good()     # the last forecast straight away; the fresh one follows
            if not self.near:
                self.near = last_nearby()
        if not self.data and not self.nodata_shown and now - self.tuned_at >= NODATA_AFTER:
            self.render()                   # still nothing after a few seconds: say so
        if (force or now - self.fetched_at > REFRESH_SECS) and not self.fetching:
            self.fetching = True
            t = threading.Thread(target=self._fetch)
            t.daemon = True
            t.start()
        if force:
            self.page_name = PAGES[0]
            self.page_at = now + PAGE_SECS
            self.render()
        elif now >= self.page_at:
            pages = self.pages()
            i = pages.index(self.page_name) if self.page_name in pages else -1
            self.page_name = pages[(i + 1) % len(pages)]
            self.page_at = now + PAGE_SECS
            self.render()

    def pages(self):
        """The page cycle: Latest Observations and the map only when there are nearby
        cities with temperatures (never a blank page); the map also needs its tiles."""
        n = self.near
        out = []
        for p in PAGES:
            if p in NEAR_PAGES and not (n and n.get("cities")):
                continue
            if p == "map" and not (map_index() and n.get("map") and n.get("z")):
                continue
            out.append(p)
        return out

    def render(self):
        try:
            self._render()
        except Exception as exc:          # a bad value from a weather add-on mustn't stop the TV
            K.log_err("weather render: %s" % exc)

    def _render(self):
        w = self.win
        P = w.setProperty
        P("wx_title", K.setting("weather_title", _("Your Local Forecast")))
        d = self.data
        if not d and time.time() - self.tuned_at < NODATA_AFTER:
            # still loading: leave the screen blank rather than flash "not set up"
            P("wx_page", "")
            P("wx_location", "")
            P("wx_ticker", "")
            return
        if not d:
            self.nodata_shown = True
            P("wx_page", "nodata")
            P("wx_location", "")
            P("wx_ticker", _("Weather is not set up yet.   Choose a weather service in Kodi (Settings > "
                           "Services > Weather) or type your city in CableBox 42 > Settings > Guide & Weather."))
            return
        page = self.page_name if self.page_name in self.pages() else PAGES[0]
        P("wx_page", page)
        P("wx_location", d.get("location", ""))
        n = d["now"]
        P("wx_temp", n.get("temp", ""))
        P("wx_cond", n.get("cond", ""))
        P("wx_icon", icon(n.get("icon"), n.get("cond")))
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
            P("wx_d%d_icon" % (i + 1), icon(day.get("icon"), day.get("cond")))
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
        today = d.get("today") or (d["days"][0] if d.get("days") else None) or {}
        hilo = (_("Today's high %s, low %s") % (today.get("hi"), today.get("lo"))) if today.get("hi") else ""
        # the ticker runs on every page (the skin's fadelabel keeps scrolling while its text stays the same)
        P("wx_ticker", _("Conditions at %s:   %s   Temperature %s   Humidity %s   Wind %s      %s") % (
            d.get("location", ""), n.get("cond", ""), n.get("temp", ""), n.get("humidity", ""),
            n.get("wind", ""), "      ".join(([hilo] if hilo else []) + narrative(d))))
        if page == "observations":
            self.render_observations()
        elif page == "map":
            self.render_map(n)

    def render_observations(self):
        P = self.win.setProperty
        cities = (self.near or {}).get("cities") or []
        for i in range(NEAR_MAX):
            c = cities[i] if i < len(cities) else {}
            P("wx_o%d_name" % i, c.get("name", ""))
            P("wx_o%d_temp" % i, c.get("temp", ""))
            P("wx_o%d_cond" % i, c.get("cond", ""))
            P("wx_o%d_icon" % i, c.get("icon", "") if c else "")

    def render_map(self, now_info):
        """Tiles and cities placed from Python into the skin's fixed slots (the map page)."""
        w = self.win
        n = self.near or {}
        ix = map_index()
        if not (n.get("cities") and ix):
            return
        home = {"name": (self.data or {}).get("location") or n.get("name", ""), "lat": n["lat"], "lon": n["lon"],
                "temp": now_info.get("temp", "").replace("F", "").replace("C", ""),
                "icon": icon(now_info.get("icon"), now_info.get("cond")), "home": True}
        if not n.get("z"):
            return
        tiles, points = map_layout(n["lat"], n["lon"], [home] + list(n.get("map") or []), ix, n["z"])
        for i, cid in enumerate(MAP_TILE_IDS):
            try:
                ctl = w.getControl(cid)
                if i < len(tiles):
                    f, x, y, tw, th = tiles[i]
                    ctl.setImage(f, False)
                    ctl.setPosition(x - MAP_VIEW[0], y - MAP_VIEW[1])     # inside the clipping grouplist
                    ctl.setWidth(tw)
                    ctl.setHeight(th)
                    ctl.setVisible(True)
                else:
                    ctl.setImage("", False)
                    ctl.setVisible(False)
            except Exception as exc:
                K.log_err("weather map tile: %s" % exc)
                return
        for i, cid in enumerate(MAP_CITY_IDS):
            p = points[i] if i < len(points) else None
            P = w.setProperty
            P("wx_m%d" % i, "1" if p else "")
            if not p:
                continue
            c, x, y = p
            P("wx_m%d_name" % i, c.get("name", ""))
            P("wx_m%d_temp" % i, c.get("temp", ""))
            P("wx_m%d_icon" % i, c.get("icon", ""))
            P("wx_m%d_home" % i, "1" if c.get("home") else "")
            try:
                w.getControl(cid).setPosition(x, y)
            except Exception as exc:
                K.log_err("weather map city: %s" % exc)
