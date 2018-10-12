# -*- coding: utf-8 -*-

import os
import sys
import time
from datetime import datetime
import urllib2
import unicodedata
import xbmc
import xbmcgui
import xbmcaddon
import json

ADDON        = xbmcaddon.Addon()
ADDONNAME    = ADDON.getAddonInfo('name')
ADDONID      = ADDON.getAddonInfo('id')
CWD          = ADDON.getAddonInfo('path').decode("utf-8")
ADDONVERSION = ADDON.getAddonInfo('version')
LANGUAGE     = ADDON.getLocalizedString
RESOURCE     = xbmc.translatePath( os.path.join( CWD, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")
PROFILE      = xbmc.translatePath(ADDON.getAddonInfo('profile')).decode('utf-8')

sys.path.append(RESOURCE)

from dateutil import tz
from utils import *

APPID          = ADDON.getSetting('API')
MAPID          = ADDON.getSetting('MAPAPI')
LOCATION_URL   = 'https://openweathermap.org/data/2.5/find?q=%s&type=like&sort=population&cnt=30&appid=b6907d289e10d714a6e88b30761fae22'
BASE_URL       = 'https://api.weatherbit.io/v2.0/%s'
LATLON         = ADDON.getSetting('LatLon')
MAPS           = ADDON.getSetting('WMaps')
ZOOM           = str(int(ADDON.getSetting('Zoom')) + 2)
WEATHER_ICON   = xbmc.translatePath('%s.png').decode("utf-8")
DATEFORMAT     = xbmc.getRegion('dateshort')
TIMEFORMAT     = xbmc.getRegion('meridiem')
MAXDAYS        = 6


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

def refresh_locations():
    locations = 0
    for count in range(1, 6):
        loc_name = ADDON.getSetting('Location%s' % count)
        if loc_name != '':
            locations += 1
        else:
            ADDON.setSetting('Location%sID' % count, '')
            ADDON.setSetting('Location%sdeg' % count, '')
        set_property('Location%s' % count, loc_name)
    set_property('Locations', str(locations))
    log('available locations: %s' % str(locations))

def get_data(search_string, item):
    if item == 'location':
        url = LOCATION_URL % search_string
    else:
        url = BASE_URL % search_string
    try:
        req = urllib2.urlopen(url)
        response = req.read()
        req.close()
    except:
        response = ''
    return response

def convert_date(stamp):
    date_time = time.localtime(stamp)
    if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
        localdate = time.strftime('%d-%m-%Y', date_time)
    elif DATEFORMAT[1] == 'm' or DATEFORMAT[0] == 'M':
        localdate = time.strftime('%m-%d-%Y', date_time)
    else:
        localdate = time.strftime('%Y-%m-%d', date_time)
    if TIMEFORMAT != '/':
        localtime = time.strftime('%I:%M%p', date_time)
    else:
        localtime = time.strftime('%H:%M', date_time)
    return localtime + '  ' + localdate

def get_time(stamp):
    date_time = time.localtime(stamp)
    if TIMEFORMAT != '/':
        localtime = time.strftime('%I:%M%p', date_time)
    else:
        localtime = time.strftime('%H:%M', date_time)
    return localtime

def convert_time(utc_time):
    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()
    try:
        utc = datetime.strptime(utc_time, '%Y-%m-%d %H:%M')
    except:
        utc = datetime(*(time.strptime(utc_time, '%Y-%m-%d %H:%M')[0:6]))
    utc = utc.replace(tzinfo=from_zone)
    date_time = utc.astimezone(to_zone)
    date_time = time.strptime(str(date_time)[0:16], '%Y-%m-%d %H:%M')
    if TIMEFORMAT != '/':
        localtime = time.strftime('%I:%M%p', date_time)
    else:
        localtime = time.strftime('%H:%M', date_time)
    return localtime

def get_weekday(stamp, form):
    date_time = time.localtime(stamp)
    weekday = time.strftime('%w', date_time)
    if form == 's':
        return xbmc.getLocalizedString(WEEK_DAY_SHORT[weekday])
    elif form == 'l':
        return xbmc.getLocalizedString(WEEK_DAY_LONG[weekday])
    else:
        return int(weekday)

def get_month(stamp, form):
    date_time = time.localtime(stamp)
    month = time.strftime('%m', date_time)
    day = time.strftime('%d', date_time)
    if form == 'ds':
        label = day + ' ' + xbmc.getLocalizedString(MONTH_NAME_SHORT[month])
    elif form == 'dl':
        label = day + ' ' + xbmc.getLocalizedString(MONTH_NAME_LONG[month])
    elif form == 'ms':
        label = xbmc.getLocalizedString(MONTH_NAME_SHORT[month]) + ' ' + day
    elif form == 'ml':
        label = xbmc.getLocalizedString(MONTH_NAME_LONG[month]) + ' ' + day
    return label

def geoip():
    try:
        req = urllib2.urlopen('http://geoip.nekudo.com/api')
        response = req.read()
        req.close()
    except:
        response = ''
        log('failed to retrieve geoip location')
    if response:
        data = json.loads(response)
        if data and 'city' in data and 'country' in data and 'code' in data['country']:
            city, country = data['city'], data['country']['code']
            return '%s, %s' % (city, country)

def location(locstr):
    locs    = []
    locdegs = []
    log('location: %s' % locstr)
    loc = unicodedata.normalize('NFKD', unicode(locstr, 'utf-8')).encode('ascii','ignore')
    log('searching for location: %s' % loc)
    search_string = urllib2.quote(loc)
    query = get_data(search_string, 'location')
    log('location data: %s' % query)
    if not query:
        log('failed to retrieve location data')
        return None, None, None
    try:
        data = json.loads(query)
    except:
        log('failed to parse location data')
        return None, None, None
    if data != '' and 'list' in data:
        for item in data['list']:
            location   = item['name']
            locationlat = str(item['coord']['lat'])
            locationlon = str(item['coord']['lon'])
            locdeg = [locationlat,locationlon]
            locationcountry = item['sys']['country']
            if LATLON == 'true':
                locs.append(location + ' (' + locationcountry + ') - lat/lon:' + locationlat + '/' + locationlon)
            else:
                locs.append(location + ' (' + locationcountry + ')')
            locdegs.append(locdeg)
    log('locs: %s' % str(locs))
    log('locdegs: %s' % str(locdegs))
    return locs, locdegs

def forecast(loc, locationdeg):
    log('weather location name: %s' % loc)
    log('weather location deg: %s' % locationdeg)
    lat = eval(locationdeg)[0]
    lon = eval(locationdeg)[1]
    if MAPS == 'true' and xbmc.getCondVisibility('System.HasAddon(script.openweathermap.maps)'):
        xbmc.executebuiltin('XBMC.RunAddon(script.openweathermap.maps,lat=%s&lon=%s&zoom=%s&api=%s&debug=%s)' % (lat, lon, ZOOM, MAPID, DEBUG))
    else:
        set_property('Map.IsFetched', '')
        for count in range (1, 6):
            set_property('Map.%i.Layer' % count, '')
            set_property('Map.%i.Area' % count, '')
            set_property('Map.%i.Heading' % count, '')
            set_property('Map.%i.Legend' % count, '')
    current_string = 'current?key=%s&lat=%s&lon=%s' % (APPID, lat, lon)
    hourly_string = 'forecast/hourly?key=%s&lat=%s&lon=%s' % (APPID, lat, lon)
    daily_string = 'forecast/daily?key=%s&lat=%s&lon=%s' % (APPID, lat, lon)
    retry = 0
    failed = False
    while (retry < 6) and (not MONITOR.abortRequested()):
        current_data = get_data(current_string, 'current')
        log('current data: %s' % current_data)
        if current_data != '':
            retry = 6
            try:
                current_weather = json.loads(current_data)
            except:
                clear()
                log('parsing current data failed')
                return
        else:
            retry += 1
            MONITOR.waitForAbort(10)
            log('weather download failed')
            if retry == 6:
                log('fatal, giving up')
                clear()
                return
    if current_weather and current_weather != '':
        current_props(current_weather,loc)
    else:
        clear()
    daily_data = get_data(daily_string, 'daily')
    log('daily data: %s' % daily_data)
    try:
        daily_weather = json.loads(daily_data)
    except:
        log('parsing daily data failed')
        daily_weather = ''
    daynum = ''
    if daily_weather and daily_weather != '':
        daily_props(daily_weather)
    hourly_data = get_data(hourly_string, 'hourly')
    log('hourly data: %s' % hourly_data)
    try:
        hourly_weather = json.loads(hourly_data)
    except:
        log('parsing hourly data failed')
        hourly_weather = ''
    if hourly_weather and hourly_weather != '':
        hourly_props(hourly_weather)

def current_props(data,loc):
# standard properties
    code = str(data['data'][0]['weather']['code'])
    pod = data['data'][0]['pod']
    code = code + pod
    weathercode = WEATHER_CODES[code]
    set_property('Current.Location'     , loc)
    set_property('Current.Condition'    , FORECAST.get(data['data'][0]['weather']['code'], data['data'][0]['weather']['description']))
    set_property('Current.Temperature'  , str(int(round(data['data'][0]['temp']))))
    set_property('Current.FeelsLike'    , str(int(round(data['data'][0]['app_temp']))))
    set_property('Current.Wind'         , str(int(round(data['data'][0]['wind_spd'] * 3.6))))
    set_property('Current.WindDirection', xbmc.getLocalizedString(WIND_DIR(int(round(data['data'][0]['wind_dir'])))))
    set_property('Current.DewPoint'     , str(data['data'][0]['dewpt']))
    set_property('Current.Humidity'     , str(data['data'][0]['rh']))
    set_property('Current.UVIndex'      , str(int(round(data['data'][0]['uv']))))
    set_property('Current.OutlookIcon'  , '%s.png' % weathercode) # kodi translates it to Current.ConditionIcon
    set_property('Current.FanartCode'   , weathercode)
    set_property('Location'             , loc)
    set_property('Updated'              , convert_date(data['data'][0]['ts']))
# extended properties
    set_property('Current.Cloudiness'       , str(data['data'][0]['clouds']) + '%')
    precip = data['data'][0]['precip']
    if not precip:
        precip = 0
    if 'F' in TEMPUNIT:
        set_property('Current.Visibility'   , str(round(data['data'][0]['vis'] * 0.621371 ,2)) + 'mi')
        set_property('Current.Pressure'     , str(round(data['data'][0]['pres'] / 33.86 ,2)) + ' in')
        set_property('Current.SeaLevel'     , str(round(data['data'][0]['slp'] / 33.86 ,2)) + ' in')
        set_property('Current.Precipitation', str(int(round(precip *  0.04 ,2))) + ' in')
        set_property('Current.Snow'         , str(int(round(data['data'][0].get('snow',0) *  0.04 ,2))) + ' in')
    else:
        set_property('Current.Visibility'   , str(data['data'][0]['vis']) + 'km')
        set_property('Current.Pressure'     , str(data['data'][0]['pres']) + ' mb')
        set_property('Current.SeaLevel'     , str(data['data'][0]['slp']) + ' mb')
        set_property('Current.Precipitation', str(int(round(precip))) + ' mm')
        set_property('Current.Snow'         , str(int(round(data['data'][0].get('snow',0)))) + ' mm')
    set_property('Forecast.City'            , data['data'][0]['city_name'])
    set_property('Forecast.Country'         , data['data'][0]['country_code'])
    set_property('Forecast.Latitude'        , str(data['data'][0]['lat']))
    set_property('Forecast.Longitude'       , str(data['data'][0]['lon']))
    set_property('Forecast.Updated'         , convert_date(data['data'][0]['ts']))
    set_property('Today.Sunrise'            , convert_time('%s %s' % (data['data'][0]['ob_time'][0:10], data['data'][0]['sunrise'])))
    set_property('Today.Sunset'             , convert_time('%s %s' % (data['data'][0]['ob_time'][0:10], data['data'][0]['sunset'])))

def daily_props(data):
# standard properties
    for count, item in enumerate(data['data']):
        code = str(item['weather']['code'])
        code = code + 'd'
        weathercode = WEATHER_CODES[code]
        set_property('Day%i.Title'              % count, get_weekday(item['ts'], 'l'))
        set_property('Day%i.HighTemp'           % count, str(int(round(item['max_temp']))))
        set_property('Day%i.LowTemp'            % count, str(int(round(item['min_temp']))))
        set_property('Day%i.Outlook'            % count, FORECAST.get(item['weather']['code'], item['weather']['description']))
        set_property('Day%i.OutlookIcon'        % count, '%s.png' % weathercode)
        set_property('Day%i.FanartCode'         % count, weathercode)
        if count == MAXDAYS:
            break
# extended properties
    for count, item in enumerate(data['data']):
        code = str(item['weather']['code'])
        code = code + 'd'
        weathercode = WEATHER_CODES[code]
        set_property('Daily.%i.LongDay'         % (count+1), get_weekday(item['ts'], 'l'))
        set_property('Daily.%i.ShortDay'        % (count+1), get_weekday(item['ts'], 's'))
        if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
            set_property('Daily.%i.LongDate'    % (count+1), get_month(item['ts'], 'dl'))
            set_property('Daily.%i.ShortDate'   % (count+1), get_month(item['ts'], 'ds'))
        else:
            set_property('Daily.%i.LongDate'    % (count+1), get_month(item['ts'], 'ml'))
            set_property('Daily.%i.ShortDate'   % (count+1), get_month(item['ts'], 'ms'))
        set_property('Daily.%i.Outlook'         % (count+1), FORECAST.get(item['weather']['code'], item['weather']['description']))
        set_property('Daily.%i.OutlookIcon'     % (count+1), WEATHER_ICON % weathercode)
        set_property('Daily.%i.FanartCode'      % (count+1), weathercode)
        set_property('Daily.%i.WindDirection'   % (count+1), xbmc.getLocalizedString(int(round(WIND_DIR(item['wind_dir'])))))
        set_property('Daily.%i.WindDegree'      % (count+1), str(item['wind_dir']) + u'°')
        set_property('Daily.%i.Humidity'        % (count+1), str(item['rh']) + '%')
        set_property('Daily.%i.Temperature'     % (count+1), TEMP(item['temp']) + TEMPUNIT)
        set_property('Daily.%i.HighTemperature' % (count+1), TEMP(item['max_temp']) + TEMPUNIT)
        set_property('Daily.%i.LowTemperature'  % (count+1), TEMP(item['min_temp']) + TEMPUNIT)
        set_property('Daily.%i.FeelsLike'       % (count+1), TEMP(int(round(item['app_max_temp']))) + TEMPUNIT)
        set_property('Daily.%i.HighFeelsLike'   % (count+1), TEMP(int(round(item['app_max_temp']))) + TEMPUNIT)
        set_property('Daily.%i.LowFeelsLike'    % (count+1), TEMP(int(round(item['app_min_temp']))) + TEMPUNIT)
        set_property('Daily.%i.DewPoint'        % (count+1), TEMP(int(round(item['dewpt']))) + TEMPUNIT)
        if 'F' in TEMPUNIT:
            set_property('Daily.%i.Pressure'      % (count+1), str(round(item['pres'] / 33.86 ,2)) + ' in')
            set_property('Daily.%i.SeaLevel'      % (count+1), str(round(item['slp'] / 33.86 ,2)) + ' in')
            set_property('Daily.%i.Snow'          % (count+1), str(round(item['snow'] * 0.04 ,2)) + ' in')
            set_property('Daily.%i.SnowDepth'     % (count+1), str(round(item['snow_depth'] * 0.04 ,2)) + ' in')
            set_property('Daily.%i.Precipitation' % (count+1), str(round(item['precip'] * 0.04 ,2)) + ' in')
            set_property('Daily.%i.Visibility'    % (count+1), str(round(item['vis'] * 0.621371 ,2)) + ' mi')
        else:
            set_property('Daily.%i.Pressure'      % (count+1), str(item['pres']) + ' mb')
            set_property('Daily.%i.SeaLevel'      % (count+1), str(round(item['slp'])) + ' mb')
            set_property('Daily.%i.Snow'          % (count+1), str(round(item['snow'])) + ' mm')
            set_property('Daily.%i.SnowDepth'     % (count+1), str(round(item['snow_depth'])) + ' mm')
            set_property('Daily.%i.Precipitation' % (count+1), str(round(item['precip'])) + ' mm')
            set_property('Daily.%i.Visibility'    % (count+1), str(item['vis']) + ' km')
        set_property('Daily.%i.WindSpeed'         % (count+1), SPEED(item['wind_spd']) + SPEEDUNIT)
        set_property('Daily.%i.WindGust'          % (count+1), SPEED(item['wind_gust_spd']) + SPEEDUNIT)
        set_property('Daily.%i.Cloudiness'        % (count+1), str(item['clouds']) + '%')
        set_property('Daily.%i.CloudsLow'         % (count+1), str(item['clouds_low']) + '%')
        set_property('Daily.%i.CloudsMid'         % (count+1), str(item['clouds_mid']) + '%')
        set_property('Daily.%i.CloudsHigh'        % (count+1), str(item['clouds_hi']) + '%')
        set_property('Daily.%i.Probability'       % (count+1), str(item['pop']) + '%')
        set_property('Daily.%i.UVIndex'           % (count+1), str(int(round(item['uv']))) + '%')
        set_property('Daily.%i.Sunrise'           % (count+1), convert_date(item['sunrise_ts']))
        set_property('Daily.%i.Sunset'            % (count+1), convert_date(item['sunset_ts']))
        set_property('Daily.%i.Moonrise'          % (count+1), convert_date(item['moonrise_ts']))
        set_property('Daily.%i.Moonset'           % (count+1), convert_date(item['moonset_ts']))
        set_property('Daily.%i.MoonPhase'         % (count+1), str(item['moon_phase']))
        set_property('Daily.%i.Ozone'             % (count+1), str(int(round(item['ozone']))) + ' DU')

def hourly_props(data):
# extended properties
    for count, item in enumerate(data['data']):
        code = str(item['weather']['code'])
        pod = data['data'][0]['pod']
        code = code + pod
        weathercode = WEATHER_CODES[code]
        set_property('Hourly.%i.Time'            % (count+1), get_time(item['ts']))
        if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
            set_property('Hourly.%i.LongDate'    % (count+1), get_month(item['ts'], 'dl'))
            set_property('Hourly.%i.ShortDate'   % (count+1), get_month(item['ts'], 'ds'))
        else:
            set_property('Hourly.%i.LongDate'    % (count+1), get_month(item['ts'], 'ml'))
            set_property('Hourly.%i.ShortDate'   % (count+1), get_month(item['ts'], 'ms'))
        set_property('Hourly.%i.Outlook'         % (count+1), FORECAST.get(item['weather']['code'], item['weather']['description']))
        set_property('Hourly.%i.OutlookIcon'     % (count+1), WEATHER_ICON % weathercode)
        set_property('Hourly.%i.FanartCode'      % (count+1), weathercode)
        set_property('Hourly.%i.WindDirection'   % (count+1), xbmc.getLocalizedString(int(round(WIND_DIR(item['wind_dir'])))))
        set_property('Hourly.%i.WindDegree'      % (count+1), str(item['wind_dir']) + u'°')
        set_property('Hourly.%i.Humidity'        % (count+1), str(item['rh']) + '%')
        set_property('Hourly.%i.Temperature'     % (count+1), TEMP(item['temp']) + TEMPUNIT)
        set_property('Hourly.%i.FeelsLike'       % (count+1), TEMP(int(round(item['app_temp']))) + TEMPUNIT)
        set_property('Hourly.%i.DewPoint'        % (count+1), TEMP(int(round(item['dewpt']))) + TEMPUNIT)
        if 'F' in TEMPUNIT:
            set_property('Hourly.%i.Pressure'      % (count+1), str(round(item['pres'] / 33.86 ,2)) + ' in')
            set_property('Hourly.%i.SeaLevel'      % (count+1), str(round(item['slp'] / 33.86 ,2)) + ' in')
            set_property('Hourly.%i.Snow'          % (count+1), str(round(item['snow'] * 0.04 ,2)) + ' in')
            set_property('Hourly.%i.SnowDepth'     % (count+1), str(round(item['snow_depth'] * 0.04 ,2)) + ' in')
            set_property('Hourly.%i.Precipitation' % (count+1), str(round(item['precip'] * 0.04 ,2)) + ' in')
            set_property('Hourly.%i.Visibility'    % (count+1), str(round(item['vis'] * 0.621371 ,2)) + ' mi')
        else:
            set_property('Hourly.%i.Pressure'      % (count+1), str(item['pres']) + ' mb')
            set_property('Hourly.%i.SeaLevel'      % (count+1), str(round(item['slp'])) + ' mb')
            set_property('Hourly.%i.Snow'          % (count+1), str(round(item['snow'])) + ' mm')
            set_property('Hourly.%i.SnowDepth'     % (count+1), str(round(item['snow_depth'])) + ' mm')
            set_property('Hourly.%i.Precipitation' % (count+1), str(round(item['precip'])) + ' mm')
            set_property('Hourly.%i.Visibility'    % (count+1), str(item['vis']) + ' km')
        set_property('Hourly.%i.WindSpeed'         % (count+1), SPEED(item['wind_spd']) + SPEEDUNIT)
        set_property('Hourly.%i.WindGust'          % (count+1), SPEED(item['wind_gust_spd']) + SPEEDUNIT)
        set_property('Hourly.%i.Cloudiness'        % (count+1), str(item['clouds']) + '%')
        set_property('Hourly.%i.CloudsLow'         % (count+1), str(item['clouds_low']) + '%')
        set_property('Hourly.%i.CloudsMid'         % (count+1), str(item['clouds_mid']) + '%')
        set_property('Hourly.%i.CloudsHigh'        % (count+1), str(item['clouds_hi']) + '%')
        set_property('Hourly.%i.Probability'       % (count+1), str(item['pop']) + '%')
        set_property('Hourly.%i.UVIndex'           % (count+1), str(int(round(item['uv']))) + '%')
        set_property('Hourly.%i.Ozone'             % (count+1), str(int(round(item['ozone']))) + ' DU')

class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)

log('version %s started with argv: %s' % (ADDONVERSION, sys.argv[1]))

MONITOR = MyMonitor()
set_property('Forecast.IsFetched' , 'true')
set_property('Current.IsFetched'  , 'true')
set_property('Today.IsFetched'    , 'true')
set_property('Daily.IsFetched'    , 'true')
set_property('Hourly.IsFetched'   , 'true')
set_property('WeatherProvider'    , LANGUAGE(32000))
set_property('WeatherProviderLogo', xbmc.translatePath(os.path.join(CWD, 'resources', 'graphics', 'banner.png')))

if not APPID:
    log('no api key provided')
elif sys.argv[1].startswith('Location'):
    keyboard = xbmc.Keyboard('', xbmc.getLocalizedString(14024), False)
    keyboard.doModal()
    if (keyboard.isConfirmed() and keyboard.getText() != ''):
        text = keyboard.getText()
        locations, locationdeg = location(text)
        dialog = xbmcgui.Dialog()
        if locations and locations != []:
            selected = dialog.select(xbmc.getLocalizedString(396), locations)
            if selected != -1:
                ADDON.setSetting(sys.argv[1], locations[selected].split(' - ')[0])
                ADDON.setSetting(sys.argv[1] + 'deg', str(locationdeg[selected]))
                log('selected location: %s' % locations[selected])
                log('selected location lat/lon: %s' % locationdeg[selected])
        else:
            dialog.ok(ADDONNAME, xbmc.getLocalizedString(284))
else:
    locationname = ADDON.getSetting('Location%s' % sys.argv[1])
    locationdeg = ADDON.getSetting('Location%sdeg' % sys.argv[1])
    if (locationdeg == '') and (sys.argv[1] != '1'):
        locationname = ADDON.getSetting('Location1')
        locationdeg = ADDON.getSetting('Location1deg')
        log('trying location 1 instead')
    if locationdeg == '':
        log('fallback to geoip')
        locationstring = geoip()
        if locationstring:
            locations, locationdeg = location(locationstring.encode("utf-8"))
            if locations:
                ADDON.setSetting('Location1', locations[0].split(' - ')[0])
                ADDON.setSetting('Location1deg', str(locationdeg[0]))
                locationname = locations[0]
                locationdeg = str(locationdeg[0])
    if not locationdeg == '':
        forecast(locationname, locationdeg)
    else:
        log('no location provided')
        clear()
    refresh_locations()

log('finished')
