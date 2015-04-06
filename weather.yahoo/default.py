import os, sys, socket, urllib2
from xml.dom import minidom
import xbmc, xbmcgui, xbmcaddon
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__      = xbmcaddon.Addon()
__addonname__  = __addon__.getAddonInfo('name')
__addonid__    = __addon__.getAddonInfo('id')
__version__    = __addon__.getAddonInfo('version')
__cwd__        = __addon__.getAddonInfo('path').decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)

from utilities import *

LOC_URL          = 'http://query.yahooapis.com/v1/public/yql?q=%s&format=json'
LOC_QUERY        = 'select * from geo.places where text="%s"'
API_URL          = 'http://weather.yahooapis.com/forecastrss?w=%s&u=c'
WEATHER_ICON     = xbmc.translatePath('special://temp/weather/%s.png').decode("utf-8")
WEATHER_WINDOW   = xbmcgui.Window(12600)

socket.setdefaulttimeout(10)

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

def set_property(name, value):
    WEATHER_WINDOW.setProperty(name, value)

def refresh_locations():
    locations = 0
    for count in range(1, 4):
        loc_name = __addon__.getSetting('Location%s' % count)
        if loc_name != '':
            locations += 1
        set_property('Location%s' % count, loc_name)
    set_property('Locations', str(locations))
    log('available locations: %s' % str(locations))

def location(loc):
    items  = []
    locs   = []
    locids = []
    log('searching for location: %s' % loc)
    query = find_location(loc)
    log('location data: %s' % query)
    data = parse_data(query)
    if data != '' and data.has_key('query') and data['query'].has_key('results') and data['query']['results'].has_key('place'):
        if isinstance (data['query']['results']['place'],list):
            for item in data['query']['results']['place']:
                listitem = item['name'] + ' (' + (item['admin1']['content'] + ' - ' if item['admin1'] is not None else '') + item['country']['code'] + ')'
                location   = item['name'] + ' (' + item['country']['code'] + ')'
                locationid = item['woeid']
                items.append(listitem)
                locs.append(location)
                locids.append(locationid)
        else:
            listitem   = data['query']['results']['place']['name'] + ' (' + data['query']['results']['place']['admin1']['content'] + ' - ' + data['query']['results']['place']['country']['code'] + ')'
            location   = data['query']['results']['place']['name'] + ' (' + data['query']['results']['place']['country']['code'] + ')'
            locationid = data['query']['results']['place']['woeid']
            items.append(listitem)
            locs.append(location)
            locids.append(locationid)
    return items, locs, locids

def find_location(loc):
    query = urllib2.quote(LOC_QUERY % loc)
    url = LOC_URL % query
    try:
        req = urllib2.urlopen(url)
        response = req.read()
        req.close()
    except:
        response = ''
    return response

def parse_data(reply):
    try:
        data = simplejson.loads(reply)
    except:
        log('failed to parse weather data')
        data = ''
    return data

def forecast(loc,locid):
    log('weather location: %s' % locid)
    retry = 0
    while (retry < 6) and (not MONITOR.abortRequested()):
        query = get_weather(locid)
        if query != '':
            retry = 6
        else:
            retry += 1
            xbmc.sleep(10000)
            log('weather download failed')
    log('forecast data: %s' % query)
    if query != '':
        properties(query,loc)
    else:
        clear()

def get_weather(locid):
    url = API_URL % locid
    try:
        req = urllib2.urlopen(url)
        response = req.read()
        req.close()
    except:
        response = ''
    return response

def clear():
    set_property('Current.Condition'     , 'N/A')
    set_property('Current.Temperature'   , '0')
    set_property('Current.Wind'          , '0')
    set_property('Current.WindDirection' , 'N/A')
    set_property('Current.Humidity'      , '0')
    set_property('Current.FeelsLike'     , '0')
    set_property('Current.UVIndex'       , '0')
    set_property('Current.DewPoint'      , '0')
    set_property('Current.OutlookIcon'   , 'na.png')
    set_property('Current.FanartCode'    , 'na')
    for count in range (0, 5):
        set_property('Day%i.Title'       % count, 'N/A')
        set_property('Day%i.HighTemp'    % count, '0')
        set_property('Day%i.LowTemp'     % count, '0')
        set_property('Day%i.Outlook'     % count, 'N/A')
        set_property('Day%i.OutlookIcon' % count, 'na.png')
        set_property('Day%i.FanartCode'  % count, 'na')

def properties(data,loc):
    xml = minidom.parseString(data)
    wind = xml.getElementsByTagName('yweather:wind')
    atmosphere = xml.getElementsByTagName('yweather:atmosphere')
    astronomy = xml.getElementsByTagName('yweather:astronomy')
    condition = xml.getElementsByTagName('yweather:condition')
    forecast = xml.getElementsByTagName('yweather:forecast')
    set_property('Current.Location'      , loc)
    set_property('Current.Condition'     , condition[0].attributes['text'].value.replace('/', ' / '))
    set_property('Current.Temperature'   , condition[0].attributes['temp'].value)
    set_property('Current.Wind'          , wind[0].attributes['speed'].value)
    if (wind[0].attributes['direction'].value != ''):
        set_property('Current.WindDirection' , winddir(int(wind[0].attributes['direction'].value)))
    else:
        set_property('Current.WindDirection' , '')
    set_property('Current.WindChill'     , wind[0].attributes['chill'].value)
    set_property('Current.Humidity'      , atmosphere[0].attributes['humidity'].value)
    set_property('Current.Visibility'    , atmosphere[0].attributes['visibility'].value)
    set_property('Current.Pressure'      , atmosphere[0].attributes['pressure'].value)
    if (wind[0].attributes['speed'].value != ''):
        set_property('Current.FeelsLike'     , feelslike(int(condition[0].attributes['temp'].value), int(round(float(wind[0].attributes['speed'].value) + 0.5))))
    else:
        set_property('Current.FeelsLike' , '')
    if (condition[0].attributes['temp'].value != '') and (atmosphere[0].attributes['humidity'].value != ''):
        set_property('Current.DewPoint'      , dewpoint(int(condition[0].attributes['temp'].value), int(atmosphere[0].attributes['humidity'].value)))
    else:
        set_property('Current.DewPoint' , '')
    set_property('Current.UVIndex'       , '')
    set_property('Current.OutlookIcon'   , '%s.png' % condition[0].attributes['code'].value) # Kodi translates it to Current.ConditionIcon
    set_property('Current.FanartCode'    , condition[0].attributes['code'].value)
    set_property('Today.Sunrise'         , astronomy[0].attributes['sunrise'].value)
    set_property('Today.Sunset'          , astronomy[0].attributes['sunset'].value)
    for count, item in enumerate(forecast):
        set_property('Day%i.Title'       % count, DAYS[item.attributes['day'].value])
        set_property('Day%i.HighTemp'    % count, item.attributes['high'].value)
        set_property('Day%i.LowTemp'     % count, item.attributes['low'].value)
        set_property('Day%i.Outlook'     % count, item.attributes['text'].value.replace('/', ' / '))
        set_property('Day%i.OutlookIcon' % count, '%s.png' % item.attributes['code'].value)
        set_property('Day%i.FanartCode'  % count, item.attributes['code'].value)

class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)

log('version %s started: %s' % (__version__, sys.argv))

MONITOR = MyMonitor()
set_property('Forecast.IsFetched' , '')
set_property('Current.IsFetched'  , '')
set_property('Today.IsFetched'    , '')
set_property('Daily.IsFetched'    , '')
set_property('Weekend.IsFetched'  , '')
set_property('36Hour.IsFetched'   , '')
set_property('Hourly.IsFetched'   , '')
set_property('Alerts.IsFetched'   , '')
set_property('Map.IsFetched'      , '')
set_property('WeatherProvider'    , __addonname__)
set_property('WeatherProviderLogo', xbmc.translatePath(os.path.join(__cwd__, 'resources', 'banner.png')))

if sys.argv[1].startswith('Location'):
    keyboard = xbmc.Keyboard('', xbmc.getLocalizedString(14024), False)
    keyboard.doModal()
    if (keyboard.isConfirmed() and keyboard.getText() != ''):
        text = keyboard.getText()
        items, locs, locids = location(text)
        dialog = xbmcgui.Dialog()
        if locs != []:
            selected = dialog.select(xbmc.getLocalizedString(396), items)
            if selected != -1:
                __addon__.setSetting(sys.argv[1], locs[selected])
                __addon__.setSetting(sys.argv[1] + 'id', locids[selected])
                log('selected location: %s' % locs[selected])
        else:
            log('no locations found')
            dialog.ok(__addonname__, xbmc.getLocalizedString(284))
else:
    location = __addon__.getSetting('Location%s' % sys.argv[1])
    locationid = __addon__.getSetting('Location%sid' % sys.argv[1])
    if (locationid == '') and (sys.argv[1] != '1'):
        location = __addon__.getSetting('Location1')
        locationid = __addon__.getSetting('Location1id')
        log('trying location 1 instead')
    if not locationid == '':
        forecast(location, locationid)
    else:
        log('empty location id')
        clear()
    refresh_locations()

log('finished')
