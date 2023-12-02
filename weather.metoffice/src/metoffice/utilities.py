import math
import time
import traceback
from datetime import datetime
from functools import wraps

import xbmc
import xbmcgui

from .constants import (ADDON_BROWSER_WINDOW_ID, TEMPERATUREUNITS,
                        WEATHER_WINDOW_ID, addon, dialog)


def log(msg, level=xbmc.LOGINFO):
    # by importing utilities all messages in xbmc log will be prepended with LOGPREFIX
    xbmc.log("weather.metoffice: {0}".format(msg), level)


def strptime(dt, fmt):
    # python datetime.strptime is not thread safe: sometimes causes 'NoneType is not callable' error
    return datetime.fromtimestamp(time.mktime(time.strptime(dt, fmt)))


def failgracefully(f):
    """
    Function decorator. When a script fails (raises an exception) we
    don't want it to make an awful 'parp' noise. Instead catch the
    generic exception, log it and if the user is on a weather page,
    show something to the user in a dialog box.
    """

    @wraps(f)
    def wrapper(*args, **kwds):
        try:
            return f(*args, **kwds)
        except Exception as e:
            e.args = map(str, e.args)
            log(traceback.format_exc(), xbmc.LOGERROR)
            if len(e.args) == 0 or e.args[0] == "":
                e.args = ("Error",)
            if len(e.args) == 1:
                e.args = e.args + ("See log file for details",)
            if (
                xbmcgui.getCurrentWindowId() == WEATHER_WINDOW_ID
                or xbmcgui.getCurrentWindowId() == ADDON_BROWSER_WINDOW_ID
            ):
                args = (e.args[0].title(),) + e.args[1:4]
                dialog().ok(*args)

    return wrapper


def xbmcbusy(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        if (
            xbmcgui.getCurrentWindowId() == WEATHER_WINDOW_ID
            or xbmcgui.getCurrentWindowId() == ADDON_BROWSER_WINDOW_ID
        ):
            xbmc.executebuiltin("ActivateWindow(busydialognocancel)")
        try:
            return f(*args, **kwds)
        finally:
            xbmc.executebuiltin("Dialog.Close(busydialognocancel)")

    return wrapper


def f_or_nla(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        try:
            return f(*args, **kwds)
        except KeyError:
            return "n/a"

    return wrapper


def f_or_na(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        try:
            return f(*args, **kwds)
        except KeyError:
            return "na"

    return wrapper


def minutes_as_time(minutes):
    """
    Takes an integer number of minutes and returns it
    as a time, starting at midnight.
    """
    return time.strftime("%H:%M", time.gmtime(minutes * 60))


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two coords
    using the haversine formula
    http://en.wikipedia.org/wiki/Haversine_formula
    """
    EARTH_RADIUS = 6371
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS * c


def feels_like(temp, humidity, windspeed):
    # https://blog.metoffice.gov.uk/2012/02/15/what-is-feels-like-temperature/
    # Using these facts we use a formula to adjust the air temperature based
    # on our understanding of wind chill at lower temperatures, heat index at
    # higher temperatures and a combination of the two in between.

    # Inspect temperature and humidity to determine which functions below
    # should be applied.

    # But for now just use the 'simplified' apparent temperature.
    return apparent_temperature_simplified(temp, humidity, windspeed)


def water_vapour_pressure(t, rh):
    # Temperature (t) is a float from 0 to 100 representing a temperature in degrees C.
    # Relative humidity (rh) is a float from 0.00 to 1.00 representing a percentage.
    return rh * 6.105 * math.e ** (17.27 * t / (237.7 + t))


def apparent_temperature_simplified(t, rh, ws):
    # A version of apparent temperature that doesn't need Q factor.
    # From the Land of Oz.
    # https://www.vcalc.com/wiki/rklarsen/Australian+Apparent+Temperature+%28AT%29
    hPa = water_vapour_pressure(t, rh)
    return t + (0.33 * hPa) - (0.70 * ws) - 4.00


def apparent_temperature(t, rh, ws, Q=0):
    # https://calculator.academy/apparent-temperature-calculator/
    # temp in degrees C
    # humidity ...
    # windspeed in metres per second
    # TODO: Q is a fudge factor based on absorbed solar radiation.
    hPa = water_vapour_pressure(t, rh)
    return t + 0.38 * hPa - 0.70 * ws + 0.70 * (Q / (ws + 10)) - 4.25


def wind_chill(temp, windspeed):
    # Use wind chill at lower winter temperatures.
    return (
        13.12
        + 0.6215 * temp
        - 11.37 * windspeed**0.16
        + 0.3965 * temp * windspeed**0.16
    )


def heat_index(t, r):
    # Use heat index for high summer temperatures.
    """
    See: https://en.wikipedia.org/wiki/Heat_index
    The formula below approximates the heat index in degrees Fahrenheit,
    to within ±1.3 °F (0.7 °C). It is the result of a multivariate fit
    (temperature equal to or greater than 80 °F (27 °C)
    """

    # NB!!! rh here is a percentage expressed as 0 - 100!

    c1 = -8.78469475556
    c2 = 1.61139411
    c3 = 2.33854883889
    c4 = -0.14611605
    c5 = -0.012308094
    c6 = -0.0164248277778
    c7 = 0.002211732
    c8 = 0.00072546
    c9 = -0.000003582
    return (
        c1
        + c2 * t
        + c3 * r
        + c4 * t * r
        + c5 * (t**2)
        + c6 * (r**2)
        + c7 * (t**2) * r
        + c8 * t * (r**2)
        + c9 * (t**2) * (r**2)
    )


def rownd(x):
    try:
        return str(round(float(x), 0)).split(".")[0]
    except ValueError:
        return ""


def localised_temperature(t):
    # TODO: This implicitly assumes that temperatures are only either
    # Celsius or Farenheit. This isn't true, Kodi now supports Kelvin
    # and other crazy units. Given that this function is only used
    # for non-standard pages, which require a custom skin, its
    # unlikely that anyone will hit the problem.
    if TEMPERATUREUNITS[-1] == "C":
        return t
    else:
        try:
            return str(int(float(t) * 9 / 5 + 32))
        except ValueError:
            return ""


@f_or_nla
def mph_to_kph(x):
    """
    Convert miles per hour to kilomenters per hour
    Required because Kodi assumes that wind speed is provided in
    kilometers per hour.
    """
    return x * 1.609344


def mph_to_mps(x):
    return x / 2.237


def gettext(s):
    """
    gettext() gets around XBMCs cryptic "Ints For Strings" translation mechanism
    requires the translatable table is kept up to date with the contents of strings.po
    """
    translatable = {
        "Observation Location": 32000,
        "Forecast Location": 32001,
        "Regional Location": 32002,
        "API Key": 32003,
        "Use IP address to determine location": 32004,
        "GeoIP Provider": 32005,
        "Erase Cache": 32006,
        "No API Key.": 32007,
        "Enter your Met Office API Key under settings.": 32008,
        "No Matches": 32009,
        "No locations found containing": 32010,
        "Matching Sites": 32011,
    }
    try:
        translation = addon().getLocalizedString(translatable[s])
        if not translation:
            raise TranslationError
        else:
            return translation
    except (KeyError, TranslationError):
        log('String "{0}" not translated.'.format(s), level=xbmc.LOGWARNING)
        return s


class TranslationError(Exception):
    pass
