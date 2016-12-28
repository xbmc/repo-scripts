import math
import xbmc, xbmcgui, xbmcaddon

ADDON      = xbmcaddon.Addon()
ADDONID    = ADDON.getAddonInfo('id')
MAINADDON  = xbmcaddon.Addon('weather.openweathermap.extended')

WEATHER_WINDOW = xbmcgui.Window(12600)
DEBUG          = MAINADDON.getSetting('Debug')
TEMPUNIT       = unicode(xbmc.getRegion('tempunit'),encoding='utf-8')
SPEEDUNIT      = xbmc.getRegion('speedunit')
if SPEEDUNIT in ('ft/s', 'ft/min', 'ft/h', 'inch/s', 'yard/s', 'kts', ):
    SPEEDUNIT = 'mph'

def log(txt):
    if DEBUG == 'true':
        if isinstance (txt,str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (ADDONID, txt)
        xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

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

