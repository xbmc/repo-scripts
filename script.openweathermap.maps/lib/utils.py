import math
import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')

WEATHER_WINDOW = xbmcgui.Window(12600)
TEMPUNIT = xbmc.getRegion('tempunit')
SPEEDUNIT = xbmc.getRegion('speedunit')

if SPEEDUNIT in ('ft/s', 'ft/min', 'ft/h', 'inch/s', 'yard/s', 'kts', ):
    SPEEDUNIT = 'mph'

def log(txt, DEBUG):
    if DEBUG:
        message = '%s: %s' % (ADDONID, txt)
        xbmc.log(msg=message, level=xbmc.LOGDEBUG)

def set_property(name, value):
    WEATHER_WINDOW.setProperty(name, value)

def clear_property(name):
    WEATHER_WINDOW.clearProperty(name)

# http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Lon..2Flat._to_tile_numbers
def GET_TILE(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return (xtile, ytile)

