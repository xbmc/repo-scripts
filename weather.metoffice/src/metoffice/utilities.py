from functools import wraps
from datetime import datetime
import time
import traceback
import math
import xbmc
import xbmcgui

from .constants import WEATHER_WINDOW_ID, ADDON_BROWSER_WINDOW_ID, DIALOG, TEMPERATUREUNITS, ADDON


def log(msg, level=xbmc.LOGINFO):
    # by importing utilities all messages in xbmc log will be prepended with LOGPREFIX
    xbmc.log('weather.metoffice: {0}'.format(msg), level)


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
            if len(e.args) == 0 or e.args[0] == '':
                e.args = ('Error',)
            if len(e.args) == 1:
                e.args = e.args + ('See log file for details',)
            if (xbmcgui.getCurrentWindowId() == WEATHER_WINDOW_ID or
                    xbmcgui.getCurrentWindowId() == ADDON_BROWSER_WINDOW_ID):
                args = (e.args[0].title(),) + e.args[1:4]
                DIALOG.ok(*args)  # @UndefinedVariable
    return wrapper


def xbmcbusy(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        if xbmcgui.getCurrentWindowId() == WEATHER_WINDOW_ID or xbmcgui.getCurrentWindowId() == ADDON_BROWSER_WINDOW_ID:
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
            return 'n/a'
    return wrapper


def f_or_na(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        try:
            return f(*args, **kwds)
        except KeyError:
            return 'na'
    return wrapper


def minutes_as_time(minutes):
    """
    Takes an integer number of minutes and returns it
    as a time, starting at midnight.
    """
    return time.strftime('%H:%M', time.gmtime(minutes*60))


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two coords
    using the haversine formula
    http://en.wikipedia.org/wiki/Haversine_formula
    """
    EARTH_RADIUS = 6371
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlat = lat2-lat1
    dlon = lon2-lon1
    a = math.sin(dlat/2)**2 + \
        math.cos(lat1) * math.cos(lat2) * \
        math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS * c


def rownd(x):
    try:
        return str(round(float(x), 0)).split('.')[0]
    except ValueError:
        return ''


def localised_temperature(t):
    # TODO: This implicitly assumes that temperatures are only either
    # Celsius or Farenheit. This isn't true, Kodi now supports Kelvin
    # and other crazy units. Given that this function is only used
    # for non-standard pages, which require a custom skin, its
    # unlikely that anyone will hit the problem.
    if TEMPERATUREUNITS[-1] == 'C':
        return t
    else:
        try:
            return str(int(float(t)*9/5+32))
        except ValueError:
            return ''


@f_or_nla
def mph_to_kmph(obj, key):
    """
    Convert miles per hour to kilomenters per hour
    Required because Kodi assumes that wind speed is provided in
    kilometers per hour.
    """
    return str(round(float(obj[key]) * 1.609344, 0))


def gettext(s):
    """
    gettext() gets around XBMCs cryptic "Ints For Strings" translation mechanism
    requires the translatable table is kept up to date with the contents of strings.po
    """
    translatable = {"Observation Location": 32000,
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
                    "Matching Sites": 32011}
    try:
        translation = ADDON.getLocalizedString(translatable[s])
        if not translation:
            raise TranslationError
        else:
            return translation
    except (KeyError, TranslationError):
        log('String "{0}" not translated.'.format(s), level=xbmc.LOGWARNING)
        return s


class TranslationError(Exception):
    pass
