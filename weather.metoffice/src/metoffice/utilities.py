from functools import wraps
from datetime import datetime
import time
import traceback
import math
import xbmc #@UnresolvedImport
import xbmcgui #@UnresolvedImport

from constants import WEATHER_WINDOW_ID, SETTINGS_WINDOW_ID, DIALOG, WINDOW, TEMPERATUREUNITS, ADDON
#by importing utilities all messages in xbmc log will be prepended with LOGPREFIX
def log(msg, level=xbmc.LOGNOTICE):
    xbmc.log('weather.metoffice: {0}'.format(msg), level)

#python datetime.strptime is not thread safe: sometimes causes 'NoneType is not callable' error
def strptime(dt, fmt):
    return datetime.fromtimestamp(time.mktime(time.strptime(dt, fmt)))

def failgracefully(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        try:
            return f(*args, **kwds)
        except Exception as e:
            e.args = map(str, e.args)
            log(traceback.format_exc(), xbmc.LOGSEVERE)
            if len(e.args) == 0 or e.args[0] == '':
                e.args = ('Error',)
            if len(e.args) == 1:
                e.args = e.args + ('See log file for details',)
            if xbmcgui.getCurrentWindowId() == WEATHER_WINDOW_ID or xbmcgui.getCurrentWindowId() == SETTINGS_WINDOW_ID:
                args = (e.args[0].title(),) + e.args[1:4]
                DIALOG.ok(*args)#@UndefinedVariable
    return wrapper

def xbmcbusy(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        if xbmcgui.getCurrentWindowId() == WEATHER_WINDOW_ID or xbmcgui.getCurrentWindowId() == SETTINGS_WINDOW_ID:
            xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        try:
            return f(*args, **kwds)
        finally:
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    return wrapper

def panelbusy(pane):
    def decorate(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            WINDOW.setProperty('{0}.IsBusy'.format(pane), 'true')#@UndefinedVariable
            try:
                return f(*args, **kwargs)
            finally:
                WINDOW.clearProperty('{0}.IsBusy'.format(pane))#@UndefinedVariable
        return wrapper
    return decorate

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
        return str(round(float(x))).split('.')[0]
    except ValueError:
        return ''

def localised_temperature(t):
    if TEMPERATUREUNITS[-1] == 'C':
        return t
    else:
        try:
            return str(int(float(t)*9)/5+32)
        except ValueError:
            return ''

def gettext(s):
    """
    gettext() gets around XBMCs cryptic "Ints For Strings" translation mechanism
    requires the translatable table is kept up to date with the contents of strings.po
    """
    translatable = {"Observation Location" : 32000,
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
        translation = ADDON.getLocalizedString(translatable[s]) #@UndefinedVariable
        if not translation:
            raise TranslationError
        else:
            return translation
    except (KeyError, TranslationError):
        log('String "{0}" not translated.'.format(s), level=xbmc.LOGWARNING)
        return s

class TranslationError(Exception):
    pass
