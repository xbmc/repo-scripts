# -*- coding: utf-8 -*-
import os
import sys
import socket
import time
import _strptime
import requests
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDONNAME = ADDON.getAddonInfo('name')
ADDONID = ADDON.getAddonInfo('id')
ADDONVERSION = ADDON.getAddonInfo('version')
CWD = ADDON.getAddonInfo('path').decode("utf-8")
RESOURCE = xbmc.translatePath( os.path.join( CWD, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")
DATAPATH = xbmc.translatePath(ADDON.getAddonInfo('profile')).decode('utf-8')
WEATHER_WINDOW = xbmcgui.Window(12600)

sys.path.append(RESOURCE)

from utils import *

LCURL = 'https://www.yahoo.com/news/_tdnews/api/resource/WeatherSearch;text=%s'
FCURL = 'https://www.yahoo.com/news/_tdnews/api/resource/WeatherService;woeids=[%s]'

socket.setdefaulttimeout(10)

def convert_datetime(stamp):
    timestruct = time.strptime(stamp[:-5], "%Y-%m-%dT%H:%M:%S")
    if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
        localdate = time.strftime('%d-%m-%Y', timestruct)
    elif DATEFORMAT[1] == 'm' or DATEFORMAT[0] == 'M':
        localdate = time.strftime('%m-%d-%Y', timestruct)
    else:
        localdate = time.strftime('%Y-%m-%d', timestruct)
    if TIMEFORMAT != '/':
        localtime = time.strftime('%I:%M %p', timestruct)
    else:
        localtime = time.strftime('%H:%M', timestruct)
    return localtime + '  ' + localdate

def get_date(stamp, form):
    timestruct = time.strptime(stamp[:-5], "%Y-%m-%dT%H:%M:%S")
    month = time.strftime('%m', timestruct)
    day = time.strftime('%d', timestruct)
    if form == 'short':
        if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
            label = day + ' ' + xbmc.getLocalizedString(MONTHS[month])
        else:
            label = xbmc.getLocalizedString(MONTHS[month]) + ' ' + day
    elif form == 'long':
        if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
            label = day + ' ' + xbmc.getLocalizedString(LMONTHS[month])
        else:
            label = xbmc.getLocalizedString(LMONTHS[month]) + ' ' + day
    return label

def get_time(stamp):
    timestruct = time.strptime(stamp[:-5], "%Y-%m-%dT%H:%M:%S")
    if TIMEFORMAT != '/':
        localtime = time.strftime('%I:%M %p', timestruct)
    else:
        localtime = time.strftime('%H:%M', timestruct)
    return localtime

def convert_temp(temp):
    celc = (float(temp)-32) * 5/9
    return str(int(round(celc)))

def convert_speed(speed):
    kmh = float(speed) * 1.609
    return str(int(round(kmh)))

def convert_seconds(sec):
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    hm = "%02d:%02d" % (h, m)
    if TIMEFORMAT != '/':
        timestruct = time.strptime(hm, "%H:%M")
        hm = time.strftime('%I:%M %p', timestruct)
    return hm

def log(txt):
    if ADDON.getSetting('Debug') == 'true':
        if isinstance (txt,str):
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
    locs   = []
    locids = []
    log('searching for location: %s' % loc)
    data = get_data(LCURL, loc)
    log('location data: %s' % data)
    if data:
        for item in data:
            print str(item)
            locs.append(item['qualifiedName'])
            locids.append(str(item['woeid']))
    return locs, locids

def get_data(api, search):
    url = api % search
    try:
        response = requests.get(url)
        return response.json()
    except:
        return

def forecast(loc, locid):
    log('weather location: %s' % locid)
    retry = 0
    while (retry < 10) and (not MONITOR.abortRequested()):
        data = get_data(FCURL, locid)
        if data:
            # response
            retry = 10
        else:
            # no response
            retry += 1
            xbmc.sleep(10000)
            log('weather download failed')
    log('forecast data: %s' % data)
    if data:
        properties(data, loc, locid)
    else:
        clear()
    
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
    for count in range (0, MAXDAYS+1):
        set_property('Day%i.Title'       % count, 'N/A')
        set_property('Day%i.HighTemp'    % count, '0')
        set_property('Day%i.LowTemp'     % count, '0')
        set_property('Day%i.Outlook'     % count, 'N/A')
        set_property('Day%i.OutlookIcon' % count, 'na.png')
        set_property('Day%i.FanartCode'  % count, 'na')

def properties(response, loc, locid):
    data = response['weathers'][0]
#current - standard
    set_property('Location'                  , loc)
    set_property('Updated'                   , convert_datetime(data['observation']['observationTime']['timestamp']))
    set_property('Current.Location'          , data['location']['displayName'])
    set_property('Current.Condition'         , data['observation']['conditionDescription'])
    set_property('Current.Temperature'       , convert_temp(data['observation']['temperature']['now']))
    set_property('Current.UVIndex'           , str(data['observation']['uvIndex']))
    set_property('Current.OutlookIcon'       , '%s.png' % str(data['observation']['conditionCode'])) # Kodi translates it to Current.ConditionIcon
    set_property('Current.FanartCode'        , str(data['observation']['conditionCode']))
    set_property('Current.Wind'              , convert_speed(data['observation']['windSpeed']))
    set_property('Current.WindDirection'     , xbmc.getLocalizedString(WIND_DIR(data['observation']['windDirection'])))
    set_property('Current.Humidity'          , str(data['observation']['humidity']))
    set_property('Current.DewPoint'          , dewpoint(int(convert_temp(data['observation']['temperature']['now'])), data['observation']['humidity']))
    set_property('Current.FeelsLike'         , convert_temp(data['observation']['temperature']['feelsLike']))
#current - extended
    set_property('Current.WindChill'         , TEMP(windchill(data['observation']['temperature']['now'], data['observation']['windSpeed'])) + TEMPUNIT)
    if 'F' in TEMPUNIT:
        set_property('Current.Visibility'    , str(round(data['observation']['visibility'],2)) + ' mi')
        set_property('Current.Pressure'      , str(round(data['observation']['barometricPressure'],2)) + ' inHg')
    else:
        set_property('Current.Visibility'        , str(round(1.60934 * data['observation']['visibility'],2)) + ' km')
        set_property('Current.Pressure'      , str(int(round((33.864 * data['observation']['barometricPressure'])))) + ' mbar')
    set_property('Current.Precipitation'     , str(data['observation']['precipitationProbability']) + '%')
#forecast - extended
    set_property('Forecast.City'            , data['location']['displayName'])
    set_property('Forecast.Country'         , data['location']['countryName'])
    set_property('Forecast.Latitude'        , str(data['location']['latitude']))
    set_property('Forecast.Longitude'       , str(data['location']['longitude']))
    set_property('Forecast.Updated'         , convert_datetime(data['observation']['observationTime']['timestamp']))
#today - extended
    set_property('Today.Sunrise'             , convert_seconds(data['sunAndMoon']['sunrise']))
    set_property('Today.Sunset'              , convert_seconds(data['sunAndMoon']['sunset']))
    set_property('Today.Moonphase'           , MOONPHASE[data['sunAndMoon']['moonPhase']])
#hourly - extended
    for count, item in enumerate(data['forecasts']['hourly']):
        set_property('Hourly.%i.Time'            % (count + 1), get_time(item['observationTime']['timestamp']))
        set_property('Hourly.%i.LongDate'        % (count + 1), get_date(item['observationTime']['timestamp'], 'long'))
        set_property('Hourly.%i.ShortDate'       % (count + 1), get_date(item['observationTime']['timestamp'], 'short'))
        set_property('Hourly.%i.Temperature'     % (count + 1), TEMP(item['temperature']['now']) + TEMPUNIT)
        set_property('Hourly.%i.FeelsLike'       % (count + 1), TEMP(item['temperature']['feelsLike']) + TEMPUNIT)
        set_property('Hourly.%i.Outlook'         % (count + 1), str(item['conditionDescription']))
        set_property('Hourly.%i.OutlookIcon'     % (count + 1), '%s.png' % str(item['conditionCode']))
        set_property('Hourly.%i.FanartCode'      % (count + 1), str(item['conditionCode']))
        set_property('Hourly.%i.Humidity'        % (count + 1), str(item['humidity']) + '%')
        set_property('Hourly.%i.Precipitation'   % (count + 1), str(item['precipitationProbability']) + '%')
        set_property('Hourly.%i.WindDirection'   % (count + 1), xbmc.getLocalizedString(WIND_DIR(item['windDirection'])))
        set_property('Hourly.%i.WindSpeed'       % (count + 1), SPEED(item['windSpeed']) + SPEEDUNIT)
        set_property('Hourly.%i.WindDegree'      % (count + 1), str(item['windDirection']) + u'°')
        set_property('Hourly.%i.DewPoint'        % (count + 1), TEMP(dewpoint(int(convert_temp(item['temperature']['now'])), item['humidity']), 'C') + TEMPUNIT)
#daily - standard
    for count, item in enumerate(data['forecasts']['daily']):
        set_property('Day%i.Title'           % count, LDAYS[item['observationTime']['weekday']])
        set_property('Day%i.HighTemp'        % count, convert_temp(item['temperature']['high']))
        set_property('Day%i.LowTemp'         % count, convert_temp(item['temperature']['low']))
        set_property('Day%i.Outlook'         % count, item['conditionDescription'])
        set_property('Day%i.OutlookIcon'     % count, '%s.png' % str(item['conditionCode']))
        set_property('Day%i.FanartCode'      % count, str(item['conditionCode']))
        if count == MAXDAYS:
            break
#daily - extended
    for count, item in enumerate(data['forecasts']['daily']):
        set_property('Daily.%i.ShortDay'        % (count + 1), DAYS[item['observationTime']['weekday']])
        set_property('Daily.%i.LongDay'         % (count + 1), LDAYS[item['observationTime']['weekday']])
        set_property('Daily.%i.ShortDate'       % (count + 1), get_date(item['observationTime']['timestamp'], 'short'))
        set_property('Daily.%i.LongDate'        % (count + 1), get_date(item['observationTime']['timestamp'], 'short'))
        set_property('Daily.%i.HighTemperature' % (count + 1), TEMP(item['temperature']['high']) + TEMPUNIT)
        set_property('Daily.%i.LowTemperature'  % (count + 1), TEMP(item['temperature']['low']) + TEMPUNIT)
        set_property('Daily.%i.Outlook'         % (count + 1), str(item['conditionDescription']))
        set_property('Daily.%i.OutlookIcon'     % (count + 1), '%s.png' % str(item['conditionCode']))
        set_property('Daily.%i.FanartCode'      % (count + 1), str(item['conditionCode']))
        set_property('Daily.%i.Humidity'        % (count + 1), str(item['humidity']) + '%')
        set_property('Daily.%i.Precipitation'   % (count + 1), str(item['precipitationProbability']) + '%')
        set_property('Daily.%i.DewPoint'        % (count + 1), TEMP(dewpoint(int(convert_temp(item['temperature']['low'])), item['humidity']), 'C') + TEMPUNIT)

class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)


log('version %s started: %s' % (ADDONVERSION, sys.argv))

MONITOR = MyMonitor()
set_property('Forecast.IsFetched' , 'true')
set_property('Current.IsFetched'  , 'true')
set_property('Today.IsFetched'    , 'true')
set_property('Daily.IsFetched'    , 'true')
set_property('Hourly.IsFetched'   , 'true')
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
        locs, locids = location(text)
        dialog = xbmcgui.Dialog()
        if locs != []:
            selected = dialog.select(xbmc.getLocalizedString(396), locs)
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
