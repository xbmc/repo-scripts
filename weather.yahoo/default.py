import os, sys, socket, urllib2, time
from xml.dom import minidom
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import json
import _strptime

ADDON        = xbmcaddon.Addon()
ADDONNAME    = ADDON.getAddonInfo('name')
ADDONID      = ADDON.getAddonInfo('id')
ADDONVERSION = ADDON.getAddonInfo('version')
CWD          = ADDON.getAddonInfo('path').decode("utf-8")
RESOURCE     = xbmc.translatePath( os.path.join( CWD, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")
DATAPATH     = xbmc.translatePath(ADDON.getAddonInfo('profile')).decode('utf-8')

sys.path.append(RESOURCE)

from utilities import *

YQL_URL          = 'https://query.yahooapis.com/v1/public/yql?q=%s&format=json'
LOC_QUERY        = 'select * from geo.places where text="%s"'
FORECAST_QUERY   = 'select * from weather.forecast where woeid=%s and u="c"'
WEATHER_WINDOW   = xbmcgui.Window(12600)

socket.setdefaulttimeout(10)

def log(txt):
    if isinstance (txt, str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (ADDONID, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

def set_property(name, value):
    WEATHER_WINDOW.setProperty(name, value)

def refresh_locations():
    locations = 0
    for count in range(1, 6):
        loc_name = ADDON.getSetting('Location%s' % count)
        if loc_name:
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
    if data and data.get('query',None) and data['query'].get('results',None) and data['query']['results'].get('place',None):
        results = data['query']['results']['place']
        if isinstance (results, list):
            for item in results:
                listitem = item['name'] + ' (' + (item['admin1']['content'] + ' - ' if item['admin1'] is not None else '') + item['country']['code'] + ')'
                location   = item['name'] + ' (' + item['country']['code'] + ')'
                locationid = item['woeid']
                items.append(listitem)
                locs.append(location)
                locids.append(locationid)
        else:
            listitem   = results['name'] + ' (' + results['admin1']['content'] + ' - ' + results['country']['code'] + ')'
            location   = results['name'] + ' (' + results['country']['code'] + ')'
            locationid = results['woeid']
            items.append(listitem)
            locs.append(location)
            locids.append(locationid)
    return items, locs, locids

def find_location(loc):
    query = urllib2.quote(LOC_QUERY % loc)
    url = YQL_URL % query
    try:
        req = urllib2.urlopen(url)
        response = req.read()
        req.close()
    except:
        return
    return response

def parse_data(reply):
    try:
        response = json.loads(reply)
    except:
        response = ''
        log('failed to parse weather data')
    return response

def forecast(loc, locid):
    log('weather location: %s' % locid)
    retry = 0
    while (retry < 10) and (not MONITOR.abortRequested()):
        query = get_weather(locid)
        if query:
            # response
            data = parse_data(query)
            if data['query']['results']:
                retry = 10
            else:
                # response = null
                retry += 1
                xbmc.sleep(1000)
                log('no weather data, retry')
        else:
            # no response
            retry += 1
            xbmc.sleep(10000)
            log('weather download failed')
    log('forecast data: %s' % query)
    if query:
        data = parse_data(query)
        if data:
            properties(data, loc, locid)
        else:
            clear()
    else:
        clear()

def get_weather(locid):
    query = urllib2.quote(FORECAST_QUERY % locid)
    url = YQL_URL % query
    try:
        req = urllib2.urlopen(url)
        response = req.read()
        req.close()
    except:
        return
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
    for count in range (0, 7):
        set_property('Day%i.Title'       % count, 'N/A')
        set_property('Day%i.HighTemp'    % count, '0')
        set_property('Day%i.LowTemp'     % count, '0')
        set_property('Day%i.Outlook'     % count, 'N/A')
        set_property('Day%i.OutlookIcon' % count, 'na.png')
        set_property('Day%i.FanartCode'  % count, 'na')
    for count in range (1, 11):
        set_property('Daily%i.Title'       % count, 'N/A')
        set_property('Daily%i.HighTemp'    % count, '0')
        set_property('Daily%i.LowTemp'     % count, '0')
        set_property('Daily%i.Outlook'     % count, 'N/A')
        set_property('Daily%i.OutlookIcon' % count, 'na.png')
        set_property('Daily%i.FanartCode'  % count, 'na')

def properties(response, loc, locid):
    data = ''
    if response and response.get('query',None) and response['query'].get('results',None) and response['query']['results'].get('channel',None):
        data = response['query']['results']['channel']
        data['age'] = time.time()
        datafile = xbmcvfs.File(os.path.join(DATAPATH, 'Location' + locid + '.dat'), 'w')
        datafile.write(str(data))
        datafile.close()
    else:
        if xbmcvfs.exists(os.path.join(DATAPATH, 'Location' + locid + '.dat')):
            datafile = xbmcvfs.File(os.path.join(DATAPATH, 'Location' + locid + '.dat'))
            data = eval(datafile.read())
            datafile.close()
            if data and (time.time() - data.get('age', 0) > 7200):
                data = ''
    if data:
        condition = ''
        wind = ''
        atmosphere = ''
        if 'wind' in data:
            wind = data['wind']
            props_wind(wind)
        if 'atmosphere' in data:
            atmosphere = data['atmosphere']
            props_atmosphere(atmosphere)
        if 'astronomy' in data:
            astronomy = data['astronomy']
            props_astronomy(astronomy)
        if 'item' in data:
            if 'condition' in data['item']:
                condition = data['item']['condition']
                props_condition(condition,loc)
                if wind:
                    props_feelslike(condition, wind)
                if atmosphere:
                    props_dewpoint(condition, atmosphere)
            if 'forecast' in data['item']:
                forecast = data['item']['forecast']
                props_forecast(forecast)        
    else:
        clear()

def props_condition(condition, loc):
    set_property('Current.Location'          , loc)
    set_property('Current.Condition'         , condition['text'].replace('/', ' / '))
    set_property('Current.Temperature'       , condition['temp'])
    set_property('Current.UVIndex'           , '')
    set_property('Current.OutlookIcon'       , '%s.png' % condition['code']) # Kodi translates it to Current.ConditionIcon
    set_property('Current.FanartCode'        , condition['code'])

def props_wind(wind):
    set_property('Current.Wind'              , wind['speed'])
    if (wind['direction']):
        set_property('Current.WindDirection' , winddir(int(wind['direction'])))
    else:
        set_property('Current.WindDirection' , '')
    set_property('Current.WindChill'         , TEMP(int(wind['chill'])) + TEMPUNIT)

def props_atmosphere(atmosphere):
    set_property('Current.Humidity'          , atmosphere['humidity'])
    set_property('Current.Visibility'        , atmosphere['visibility'] + '%')
    set_property('Current.Pressure'          , atmosphere['pressure'] + ' Pa')

def props_feelslike(condition, wind):
    if (wind['speed']):
        set_property('Current.FeelsLike'     , feelslike(int(condition['temp']), int(round(float(wind['speed']) + 0.5))))
    else:
        set_property('Current.FeelsLike'     , '')

def props_dewpoint(condition, atmosphere):
    if (condition['temp']) and (atmosphere['humidity']):
        set_property('Current.DewPoint'      , dewpoint(int(condition['temp']), int(atmosphere['humidity'])))
    else:
        set_property('Current.DewPoint'      , '')

def props_astronomy(astronomy):
    ftime   = xbmc.getRegion('time').replace(":%S","").replace("%H%H","%H")
    sunrise = time.strptime(astronomy['sunrise'], "%I:%M %p")
    sunset  = time.strptime(astronomy['sunset'], "%I:%M %p")
    set_property('Today.Sunrise'             , time.strftime(ftime, sunrise))
    set_property('Today.Sunset'              , time.strftime(ftime, sunset))

def props_forecast(forecast):
    for count, item in enumerate(forecast):
        set_property('Day%i.Title'           % count, DAYS[item['day']])
        set_property('Day%i.HighTemp'        % count, item['high'])
        set_property('Day%i.LowTemp'         % count, item['low'])
        set_property('Day%i.Outlook'         % count, item['text'].replace('/', ' / '))
        set_property('Day%i.OutlookIcon'     % count, '%s.png' % item['code'])
        set_property('Day%i.FanartCode'      % count, item['code'])
        set_property('Daily.%i.ShortDay'        % (count + 1), DAYS[item['day']])
        set_property('Daily.%i.LongDay'         % (count + 1), LDAYS[item['day']])
        set_property('Daily.%i.ShortDate'       % (count + 1), DATE(item['date']))
        set_property('Daily.%i.HighTemperature' % (count + 1), TEMP(int(item['high'])) + TEMPUNIT)
        set_property('Daily.%i.LowTemperature'  % (count + 1), TEMP(int(item['low'])) + TEMPUNIT)
        set_property('Daily.%i.Outlook'         % (count + 1), item['text'].replace('/', ' / '))
        set_property('Daily.%i.OutlookIcon'     % (count + 1), '%s.png' % item['code'])
        set_property('Daily.%i.FanartCode'      % (count + 1), item['code'])

class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)


log('version %s started: %s' % (ADDONVERSION, sys.argv))

MONITOR = MyMonitor()
set_property('Forecast.IsFetched' , '')
set_property('Current.IsFetched'  , 'true')
set_property('Today.IsFetched'    , 'true')
set_property('Daily.IsFetched'    , 'true')
set_property('Weekend.IsFetched'  , '')
set_property('36Hour.IsFetched'   , '')
set_property('Hourly.IsFetched'   , '')
set_property('Alerts.IsFetched'   , '')
set_property('Map.IsFetched'      , '')
set_property('WeatherProvider'    , ADDONNAME)
set_property('WeatherProviderLogo', xbmc.translatePath(os.path.join(CWD, 'resources', 'banner.png')))

# Create data path if it doesn't exist
if not xbmcvfs.exists(DATAPATH):
    xbmcvfs.mkdir(DATAPATH)

if sys.argv[1].startswith('Location'):
    keyboard = xbmc.Keyboard('', xbmc.getLocalizedString(14024), False)
    keyboard.doModal()
    if (keyboard.isConfirmed() and keyboard.getText()):
        text = keyboard.getText()
        items, locs, locids = location(text)
        dialog = xbmcgui.Dialog()
        if locs != []:
            selected = dialog.select(xbmc.getLocalizedString(396), items)
            if selected != -1:
                ADDON.setSetting(sys.argv[1], locs[selected])
                ADDON.setSetting(sys.argv[1] + 'id', locids[selected])
                log('selected location: %s' % locs[selected])
        else:
            log('no locations found')
            dialog.ok(ADDONNAME, xbmc.getLocalizedString(284))
else:
    location = ADDON.getSetting('Location%s' % sys.argv[1])
    locationid = ADDON.getSetting('Location%sid' % sys.argv[1])
    if (not locationid) and (sys.argv[1] != '1'):
        location = ADDON.getSetting('Location1')
        locationid = ADDON.getSetting('Location1id')
        log('trying location 1 instead')
    if locationid:
        forecast(location, locationid)
    else:
        log('empty location id')
        clear()
    refresh_locations()

log('finished')
