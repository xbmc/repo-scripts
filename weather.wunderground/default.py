# -*- coding: utf-8 -*-

# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with Kodi; see the file COPYING. If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html


import os, sys, socket, unicodedata, urllib2, time, gzip
from datetime import date
from StringIO import StringIO
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import json

ADDON      = xbmcaddon.Addon()
ADDONNAME  = ADDON.getAddonInfo('name')
ADDONID    = ADDON.getAddonInfo('id')
CWD        = ADDON.getAddonInfo('path').decode("utf-8")
VERSION    = ADDON.getAddonInfo('version')
LANGUAGE   = ADDON.getLocalizedString
RESOURCE   = xbmc.translatePath( os.path.join( CWD, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")
PROFILE    = xbmc.translatePath(ADDON.getAddonInfo('profile')).decode('utf-8')
API        = ADDON.getSetting('API')

sys.path.append(RESOURCE)

from utilities import *
from wunderground import wundergroundapi

WUNDERGROUND_LOC = 'http://autocomplete.wunderground.com/aq?query=%s&format=JSON'
WEATHER_FEATURES = 'hourly/conditions/forecast10day/astronomy/almanac/alerts/satellite'
FORMAT           = 'json'
DEBUG            = ADDON.getSetting('Debug')
XBMC_PYTHON      = xbmcaddon.Addon(id='xbmc.python').getAddonInfo('version')
WEATHER_ICON     = '%s.png'
WEATHER_WINDOW   = xbmcgui.Window(12600)
LOCALIZE         = xbmc.getLanguage().lower()
SPEEDUNIT        = xbmc.getRegion('speedunit')
TEMPUNIT         = unicode(xbmc.getRegion('tempunit'),encoding='utf-8')
TIMEFORMAT       = xbmc.getRegion('meridiem')
DATEFORMAT       = xbmc.getRegion('dateshort')
MAXDAYS          = 6

socket.setdefaulttimeout(10)

def mk_int(s):
    s = s.strip()
    return int(s) if s else 0

def recode(alert): # workaround: wunderground provides a corrupt alerts message
    try:
        alert = alert.encode("latin-1").rstrip('&nbsp)').decode("utf-8")
    except:
        pass
    return alert

def log(txt):
    if DEBUG == 'true':
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
        if loc_name != '':
            locations += 1
        else:
            ADDON.setSetting('Location%sid' % count, '')
        set_property('Location%s' % count, loc_name)
    set_property('Locations', str(locations))
    log('available locations: %s' % str(locations))

def get_data(url):
    try:
        req = urllib2.urlopen(url)
        response = req.read()
        req.close()
    except:
        response = ''
    return response

def location(string):
    locs   = []
    locids = []
    log('location: %s' % string)
    loc = unicodedata.normalize('NFKD', unicode(string, 'utf-8')).encode('ascii','ignore')
    log('searching for location: %s' % loc)
    url = WUNDERGROUND_LOC % urllib2.quote(loc)
    query = get_data(url)
    log('location data: %s' % query)
    data = parse_data(query)
    if data != '' and data.has_key('RESULTS'):
        for item in data['RESULTS']:
            location   = item['name']
            locationid = item['l'][3:]
            locs.append(location)
            locids.append(locationid)
    return locs, locids

def geoip():
    retry = 0
    while (retry < 6) and (not xbmc.abortRequested):
        query = wundergroundapi('geolookup', 'lang:EN', 'autoip', FORMAT)
        if query != '':
            retry = 6
        else:
            retry += 1
            xbmc.sleep(10000)
            log('geoip download failed')
    log('geoip data: %s' % query)
    data = parse_data(query)
    if data != '' and data.has_key('location'):
        location   = data['location']['city']
        locationid = data['location']['l'][3:]
        ADDON.setSetting('Location1', location)
        ADDON.setSetting('Location1id', locationid)
        log('geoip location: %s' % location)
    else:
        location = ''
        locationid = ''
    return location, locationid

def forecast(loc,locid):
    try:
        lang = LANG[LOCALIZE]
    except:
        lang = 'EN'
    opt = 'lang:' + lang
    log('weather location: %s' % locid)
    retry = 0
    while (retry < 6) and (not xbmc.abortRequested):
        query = wundergroundapi(WEATHER_FEATURES, opt, locid, FORMAT)
        if query != '':
            retry = 6
        else:
            retry += 1
            xbmc.sleep(10000)
            log('weather download failed')
    log('forecast data: %s' % query)
    data = parse_data(query)
    if data != '' and data.has_key('response') and not data['response'].has_key('error'):
        properties(data,loc,locid)
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

def parse_data(response):
    try:
        raw = response.replace('<br>',' ').replace('&auml;','ä') # wu api bugs
        reply = raw.replace('"-999%"','""').replace('"-9999.00"','""').replace('"-9998"','""').replace('"NA"','""').replace('"--"','""') # wu will change these to null responses in the future
        data = json.loads(reply)
    except:
        log('failed to parse weather data')
        data = ''
    return data

def properties(data,loc,locid):
# standard properties
    weathercode = WEATHER_CODES[os.path.splitext(os.path.basename(data['current_observation']['icon_url']))[0]]
    set_property('Current.Location'      , loc)
    set_property('Current.Condition'     , data['current_observation']['weather'])
    set_property('Current.Temperature'   , str(data['current_observation']['temp_c']))
    set_property('Current.Wind'          , str(data['current_observation']['wind_kph']))
    set_property('Current.WindDirection' , data['current_observation']['wind_dir'])
    set_property('Current.Humidity'      , data['current_observation']['relative_humidity'].rstrip('%'))
    set_property('Current.FeelsLike'     , data['current_observation']['feelslike_c'])
    set_property('Current.UVIndex'       , data['current_observation']['UV'])
    set_property('Current.DewPoint'      , str(data['current_observation']['dewpoint_c']))
    set_property('Current.OutlookIcon'   , '%s.png' % weathercode) # xbmc translates it to Current.ConditionIcon
    set_property('Current.FanartCode'    , weathercode)
    for count, item in enumerate(data['forecast']['simpleforecast']['forecastday']):
        weathercode = WEATHER_CODES[os.path.splitext(os.path.basename(item['icon_url']))[0]]
        set_property('Day%i.Title'       % count, item['date']['weekday'])
        set_property('Day%i.HighTemp'    % count, str(item['high']['celsius']))
        set_property('Day%i.LowTemp'     % count, str(item['low']['celsius']))
        set_property('Day%i.Outlook'     % count, item['conditions'])
        set_property('Day%i.OutlookIcon' % count, '%s.png' % weathercode)
        set_property('Day%i.FanartCode'  % count, weathercode)
        if count == MAXDAYS:
            break
# forecast properties
    set_property('Forecast.IsFetched'        , 'true')
    set_property('Forecast.City'             , data['current_observation']['display_location']['city'])
    set_property('Forecast.State'            , data['current_observation']['display_location']['state_name'])
    set_property('Forecast.Country'          , data['current_observation']['display_location']['country'])
    if data['current_observation']['observation_epoch']:
        update = time.localtime(float(data['current_observation']['observation_epoch']))
        local = time.localtime(float(data['current_observation']['local_epoch']))
        if DATEFORMAT[1] == 'd':
            updatedate = WEEKDAY[update[6]] + ' ' + str(update[2]) + ' ' + MONTH[update[1]] + ' ' + str(update[0])
            localdate = WEEKDAY[local[6]] + ' ' + str(local[2]) + ' ' + MONTH[local[1]] + ' ' + str(local[0])
        elif DATEFORMAT[1] == 'm':
            updatedate = WEEKDAY[update[6]] + ' ' + MONTH[update[1]] + ' ' + str(update[2]) + ', ' + str(update[0])
            localdate = WEEKDAY[local[6]] + ' ' + str(local[2]) + ' ' + MONTH[local[1]] + ' ' + str(local[0])
        else:
            updatedate = WEEKDAY[update[6]] + ' ' + str(update[0]) + ' ' + MONTH[update[1]] + ' ' + str(update[2])
            localdate = WEEKDAY[local[6]] + ' ' + str(local[0]) + ' ' + MONTH[local[1]] + ' ' + str(local[2])
        if TIMEFORMAT != '/':
            updatetime = time.strftime('%I:%M%p', update)
            localtime = time.strftime('%I:%M%p', local)
        else:
            updatetime = time.strftime('%H:%M', update)
            localtime = time.strftime('%H:%M', local)
        set_property('Forecast.Updated'          , updatedate + ' - ' + updatetime)
# current properties
        set_property('Current.LocalTime'         , localtime)
        set_property('Current.LocalDate'         , localdate)
    set_property('Current.IsFetched'         , 'true')
    set_property('Current.WindDegree'        , str(data['current_observation']['wind_degrees']) + u'°')
    set_property('Current.SolarRadiation'    , str(data['current_observation']['solarradiation']))
    if 'F' in TEMPUNIT:
        set_property('Current.Pressure'      , data['current_observation']['pressure_in'] + ' inHg')
        set_property('Current.Precipitation' , data['current_observation']['precip_1hr_in'] + ' in')
        set_property('Current.HeatIndex'     , str(data['current_observation']['heat_index_f']) + TEMPUNIT)
        set_property('Current.WindChill'     , str(data['current_observation']['windchill_f']) + TEMPUNIT)
    else:
        set_property('Current.Pressure'      , data['current_observation']['pressure_mb'] + ' mb')
        set_property('Current.Precipitation' , data['current_observation']['precip_1hr_metric'] + ' mm')
        set_property('Current.HeatIndex'     , str(data['current_observation']['heat_index_c']) + TEMPUNIT)
        set_property('Current.WindChill'     , str(data['current_observation']['windchill_c']) + TEMPUNIT)
    if SPEEDUNIT == 'mph':
        set_property('Current.Visibility'    , data['current_observation']['visibility_mi'] + ' mi')
        set_property('Current.WindGust'      , str(data['current_observation']['wind_gust_mph']) + ' ' + SPEEDUNIT)
    else:
        set_property('Current.Visibility'    , data['current_observation']['visibility_km'] + ' km')
        set_property('Current.WindGust'      , str(data['current_observation']['wind_gust_kph']) + ' ' + SPEEDUNIT)
# today properties
    set_property('Today.IsFetched'                     , 'true')
    if TIMEFORMAT != '/':
        AM = unicode(TIMEFORMAT.split('/')[0],encoding='utf-8')
        PM = unicode(TIMEFORMAT.split('/')[1],encoding='utf-8')
        hour = int(data['moon_phase']['sunrise']['hour']) % 24
        isam = (hour >= 0) and (hour < 12)
        if isam:
            hour = ('12' if (hour == 0) else '%02d' % (hour))
            set_property('Today.Sunrise'               , hour.lstrip('0') + ':' + data['moon_phase']['sunrise']['minute'] + ' ' + AM)
        else:
            hour = ('12' if (hour == 12) else '%02d' % (hour-12))
            set_property('Today.Sunrise'               , hour.lstrip('0') + ':' + data['moon_phase']['sunrise']['minute'] + ' ' + PM)
        hour = int(data['moon_phase']['sunset']['hour']) % 24
        isam = (hour >= 0) and (hour < 12)
        if isam:
            hour = ('12' if (hour == 0) else '%02d' % (hour))
            set_property('Today.Sunset'                , hour.lstrip('0') + ':' + data['moon_phase']['sunset']['minute'] + ' ' + AM)
        else:
            hour = ('12' if (hour == 12) else '%02d' % (hour-12))
            set_property('Today.Sunset'                , hour.lstrip('0') + ':' + data['moon_phase']['sunset']['minute'] + ' ' + PM)
    else:
        set_property('Today.Sunrise'                   , data['moon_phase']['sunrise']['hour'] + ':' + data['moon_phase']['sunrise']['minute'])
        set_property('Today.Sunset'                    , data['moon_phase']['sunset']['hour'] + ':' + data['moon_phase']['sunset']['minute'])
    set_property('Today.moonphase'                     , MOONPHASE(mk_int(data['moon_phase']['ageOfMoon']), mk_int(data['moon_phase']['percentIlluminated'])))
    if 'F' in TEMPUNIT:
        set_property('Today.AvgHighTemperature'        , data['almanac']['temp_high']['normal']['F'] + TEMPUNIT)
        set_property('Today.AvgLowTemperature'         , data['almanac']['temp_low']['normal']['F'] + TEMPUNIT)
        try:
            set_property('Today.RecordHighTemperature' , data['almanac']['temp_high']['record']['F'] + TEMPUNIT)
            set_property('Today.RecordLowTemperature'  , data['almanac']['temp_low']['record']['F'] + TEMPUNIT)
        except:
            set_property('Today.RecordHighTemperature' , '')
            set_property('Today.RecordLowTemperature'  , '')
    else:
        set_property('Today.AvgHighTemperature'        , data['almanac']['temp_high']['normal']['C'] + TEMPUNIT)
        set_property('Today.AvgLowTemperature'         , data['almanac']['temp_low']['normal']['C'] + TEMPUNIT)
        try:
            set_property('Today.RecordHighTemperature' , data['almanac']['temp_high']['record']['C'] + TEMPUNIT)
            set_property('Today.RecordLowTemperature'  , data['almanac']['temp_low']['record']['C'] + TEMPUNIT)
        except:
            set_property('Today.RecordHighTemperature' , '')
            set_property('Today.RecordLowTemperature'  , '')
    try:
        set_property('Today.RecordHighYear'            , data['almanac']['temp_high']['recordyear'])
        set_property('Today.RecordLowYear'             , data['almanac']['temp_low']['recordyear'])
    except:
        set_property('Today.RecordHighYear'            , '')
        set_property('Today.RecordLowYear'             , '')
# daily properties
    set_property('Daily.IsFetched', 'true')
    for count, item in enumerate(data['forecast']['simpleforecast']['forecastday']):
        weathercode = WEATHER_CODES[os.path.splitext(os.path.basename(item['icon_url']))[0]]
        set_property('Daily.%i.LongDay'              % (count+1), item['date']['weekday'])
        set_property('Daily.%i.ShortDay'             % (count+1), item['date']['weekday_short'])
        if DATEFORMAT[1] == 'd':
            set_property('Daily.%i.LongDate'         % (count+1), str(item['date']['day']) + ' ' + item['date']['monthname'])
            set_property('Daily.%i.ShortDate'        % (count+1), str(item['date']['day']) + ' ' + MONTH[item['date']['month']])
        else:
            set_property('Daily.%i.LongDate'         % (count+1), item['date']['monthname'] + ' ' + str(item['date']['day']))
            set_property('Daily.%i.ShortDate'        % (count+1), MONTH[item['date']['month']] + ' ' + str(item['date']['day']))
        set_property('Daily.%i.Outlook'              % (count+1), item['conditions'])
        set_property('Daily.%i.OutlookIcon'          % (count+1), WEATHER_ICON % weathercode)
        set_property('Daily.%i.FanartCode'           % (count+1), weathercode)
        if SPEEDUNIT == 'mph':
            set_property('Daily.%i.WindSpeed'        % (count+1), str(item['avewind']['mph']) + ' ' + SPEEDUNIT)
            set_property('Daily.%i.MaxWind'          % (count+1), str(item['maxwind']['mph']) + ' ' + SPEEDUNIT)
        elif SPEEDUNIT == 'Beaufort':
            set_property('Daily.%i.WindSpeed'        % (count+1), KPHTOBFT(item['avewind']['kph']))
            set_property('Daily.%i.MaxWind'          % (count+1), KPHTOBFT(item['maxwind']['kph']))
        else:
            set_property('Daily.%i.WindSpeed'        % (count+1), str(item['avewind']['kph']) + ' ' + SPEEDUNIT)
            set_property('Daily.%i.MaxWind'          % (count+1), str(item['maxwind']['kph']) + ' ' + SPEEDUNIT)
        set_property('Daily.%i.WindDirection'        % (count+1), item['avewind']['dir'])
        set_property('Daily.%i.ShortWindDirection'   % (count+1), item['avewind']['dir'])
        set_property('Daily.%i.WindDegree'           % (count+1), str(item['avewind']['degrees']) + u'°')
        set_property('Daily.%i.Humidity'             % (count+1), str(item['avehumidity']) + '%')
        set_property('Daily.%i.MinHumidity'          % (count+1), str(item['minhumidity']) + '%')
        set_property('Daily.%i.MaxHumidity'          % (count+1), str(item['maxhumidity']) + '%')
        if 'F' in TEMPUNIT:
            set_property('Daily.%i.HighTemperature'  % (count+1), str(item['high']['fahrenheit']) + TEMPUNIT)
            set_property('Daily.%i.LowTemperature'   % (count+1), str(item['low']['fahrenheit']) + TEMPUNIT)
            set_property('Daily.%i.LongOutlookDay'   % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count]['fcttext'])
            set_property('Daily.%i.LongOutlookNight' % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count+1]['fcttext'])
            set_property('Daily.%i.Precipitation'    % (count+1), str(item['qpf_day']['in']) + ' in')
            set_property('Daily.%i.Snow'             % (count+1), str(item['snow_day']['in']) + ' in')
        else:
            set_property('Daily.%i.HighTemperature'  % (count+1), str(item['high']['celsius']) + TEMPUNIT)
            set_property('Daily.%i.LowTemperature'   % (count+1), str(item['low']['celsius']) + TEMPUNIT)
            set_property('Daily.%i.LongOutlookDay'   % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count]['fcttext_metric'])
            set_property('Daily.%i.LongOutlookNight' % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count+1]['fcttext_metric'])
            set_property('Daily.%i.Precipitation'    % (count+1), str(item['qpf_day']['mm']) + ' mm')
            set_property('Daily.%i.Snow'             % (count+1), str(item['snow_day']['cm']) + ' mm')
        set_property('Daily.%i.ChancePrecipitation'  % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count]['pop'] + '%')
# weekend properties
    set_property('Weekend.IsFetched', 'true')
    if ADDON.getSetting('Weekend') == '2':
        weekend = [4,5]
    elif ADDON.getSetting('Weekend') == '1':
        weekend = [5,6]
    else:
        weekend = [6,7]
    count = 0
    for item in data['forecast']['simpleforecast']['forecastday']:
        if date(item['date']['year'], item['date']['month'], item['date']['day']).isoweekday() in weekend:
            weathercode = WEATHER_CODES[os.path.splitext(os.path.basename(item['icon_url']))[0]]
            set_property('Weekend.%i.LongDay'                  % (count+1), item['date']['weekday'])
            set_property('Weekend.%i.ShortDay'                 % (count+1), item['date']['weekday_short'])
            if DATEFORMAT[1] == 'd':
                set_property('Weekend.%i.LongDate'             % (count+1), str(item['date']['day']) + ' ' + item['date']['monthname'])
                set_property('Weekend.%i.ShortDate'            % (count+1), str(item['date']['day']) + ' ' + MONTH[item['date']['month']])
            else:
                set_property('Weekend.%i.LongDate'             % (count+1), item['date']['monthname'] + ' ' + str(item['date']['day']))
                set_property('Weekend.%i.ShortDate'            % (count+1), MONTH[item['date']['month']] + ' ' + str(item['date']['day']))
            set_property('Weekend.%i.Outlook'                  % (count+1), item['conditions'])
            set_property('Weekend.%i.OutlookIcon'              % (count+1), WEATHER_ICON % weathercode)
            set_property('Weekend.%i.FanartCode'               % (count+1), weathercode)
            if SPEEDUNIT == 'mph':
                set_property('Weekend.%i.WindSpeed'            % (count+1), str(item['avewind']['mph']) + ' ' + SPEEDUNIT)
                set_property('Weekend.%i.MaxWind'              % (count+1), str(item['maxwind']['mph']) + ' ' + SPEEDUNIT)
            elif SPEEDUNIT == 'Beaufort':
                set_property('Weekend.%i.WindSpeed'            % (count+1), KPHTOBFT(item['avewind']['kph']))
                set_property('Weekend.%i.MaxWind'              % (count+1), KPHTOBFT(item['maxwind']['kph']))
            else:
                set_property('Weekend.%i.WindSpeed'            % (count+1), str(item['avewind']['kph']) + ' ' + SPEEDUNIT)
                set_property('Weekend.%i.MaxWind'              % (count+1), str(item['maxwind']['kph']) + ' ' + SPEEDUNIT)
            set_property('Weekend.%i.WindDirection'            % (count+1), item['avewind']['dir'])
            set_property('Weekend.%i.ShortWindDirection'       % (count+1), item['avewind']['dir'])
            set_property('Weekend.%i.WindDegree'               % (count+1), str(item['avewind']['degrees']) + u'°')
            set_property('Weekend.%i.Humidity'                 % (count+1), str(item['avehumidity']) + '%')
            set_property('Weekend.%i.MinHumidity'              % (count+1), str(item['minhumidity']) + '%')
            set_property('Weekend.%i.MaxHumidity'              % (count+1), str(item['maxhumidity']) + '%')
            set_property('Weekend.%i.ChancePrecipitation'      % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count]['pop'] + '%')
            if 'F' in TEMPUNIT:
                set_property('Weekend.%i.HighTemperature'      % (count+1), str(item['high']['fahrenheit']) + TEMPUNIT)
                set_property('Weekend.%i.LowTemperature'       % (count+1), str(item['low']['fahrenheit']) + TEMPUNIT)
                set_property('Weekend.%i.FeelsLike'            % (count+1), FEELS_LIKE(int(item['high']['celsius']), item['avewind']['kph'], item['avehumidity'], 'F') + TEMPUNIT)
                set_property('Weekend.%i.DewPoint'             % (count+1), DEW_POINT(int(item['high']['celsius']), item['avehumidity'], 'F') + TEMPUNIT)
                set_property('Weekend.%i.Precipitation'        % (count+1), str(item['qpf_day']['in']) + ' in')
                set_property('Weekend.%i.Snow'                 % (count+1), str(item['snow_day']['in']) + ' in')
                set_property('Weekend.%i.LongOutlookDay'       % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count]['fcttext'])
                set_property('Weekend.%i.LongOutlookNight'     % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count+1]['fcttext'])
            else:
                set_property('Weekend.%i.HighTemperature'      % (count+1), str(item['high']['celsius']) + TEMPUNIT)
                set_property('Weekend.%i.LowTemperature'       % (count+1), str(item['low']['celsius']) + TEMPUNIT)
                set_property('Weekend.%i.FeelsLike'            % (count+1), FEELS_LIKE(int(item['high']['celsius']), item['avewind']['kph'], item['avehumidity'], 'C') + TEMPUNIT)
                set_property('Weekend.%i.DewPoint'             % (count+1), DEW_POINT(int(item['high']['celsius']), item['avehumidity'], 'C') + TEMPUNIT)
                set_property('Weekend.%i.Precipitation'        % (count+1), str(item['qpf_day']['mm']) + ' mm')
                set_property('Weekend.%i.Snow'                 % (count+1), str(item['snow_day']['cm']) + ' mm')
                if data['current_observation']['display_location']['country'] == 'UK': # for the brits
                    dfcast_e = data['forecast']['txt_forecast']['forecastday'][2*count]['fcttext'].split('.')
                    dfcast_m = data['forecast']['txt_forecast']['forecastday'][2*count]['fcttext_metric'].split('.')
                    nfcast_e = data['forecast']['txt_forecast']['forecastday'][2*count+1]['fcttext'].split('.')
                    nfcast_m = data['forecast']['txt_forecast']['forecastday'][2*count+1]['fcttext_metric'].split('.')
                    for field in dfcast_e:
                        wind = ''
                        if field.endswith('mph'): # find windspeed in mph
                            wind = field
                            break
                    for field in dfcast_m:
                        if field.endswith('km/h'): # find windspeed in km/h
                            dfcast_m[dfcast_m.index(field)] = wind # replace windspeed in km/h with windspeed in mph
                            break
                    for field in nfcast_e:
                        wind = ''
                        if field.endswith('mph'): # find windspeed in mph
                            wind = field
                            break
                    for field in nfcast_m:
                        if field.endswith('km/h'): # find windspeed in km/h
                            nfcast_m[nfcast_m.index(field)] = wind # replace windspeed in km/h with windspeed in mph
                            break
                    set_property('Weekend.%i.LongOutlookDay'   % (count+1), '. '.join(dfcast_m))
                    set_property('Weekend.%i.LongOutlookNight' % (count+1), '. '.join(nfcast_m))
                else:
                    set_property('Weekend.%i.LongOutlookDay'   % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count]['fcttext_metric'])
                    set_property('Weekend.%i.LongOutlookNight' % (count+1), data['forecast']['txt_forecast']['forecastday'][2*count+1]['fcttext_metric'])
            count += 1
            if count == 2:
                break
# 36 hour properties
    set_property('36Hour.IsFetched', 'true')
    for count, item in enumerate(data['forecast']['txt_forecast']['forecastday']):
        weathercode = WEATHER_CODES[os.path.splitext(os.path.basename(item['icon_url']))[0]]
        if 'F' in TEMPUNIT:
            try:
                fcast = item['fcttext'].split('.')
                for line in fcast:
                    if line.endswith('F'):
                        set_property('36Hour.%i.TemperatureHeading' % (count+1), line.rsplit(' ',1)[0])
                        set_property('36Hour.%i.Temperature'        % (count+1), line.rsplit(' ',1)[1])
                        break
            except:
                set_property('36Hour.%i.TemperatureHeading'         % (count+1), '')
                set_property('36Hour.%i.Temperature'                % (count+1), '')
            try:
                set_property('36Hour.%i.Outlook'                    % (count+1), item['fcttext'].split('.')[0])
            except:
                set_property('36Hour.%i.Outlook'                    % (count+1), item['fcttext'])
        else:
            try:
                fcast = item['fcttext_metric'].split('.')
                for line in fcast:
                    if line.endswith('C'):
                        set_property('36Hour.%i.TemperatureHeading' % (count+1), line.rsplit(' ',1)[0])
                        set_property('36Hour.%i.Temperature'        % (count+1), line.rsplit(' ',1)[1])
                        break
            except:
                set_property('36Hour.%i.TemperatureHeading'         % (count+1), '')
                set_property('36Hour.%i.Temperature'                % (count+1), '')
            try:
                set_property('36Hour.%i.Outlook'                    % (count+1), item['fcttext_metric'].split('.')[0])
            except:
                set_property('36Hour.%i.Outlook'                    % (count+1), item['fcttext_metric'])
        if SPEEDUNIT == 'mph':
            try:
                set_property('36Hour.%i.WindSpeed'                  % (count+1), item['fcttext'].split('.')[2])
            except:
                set_property('36Hour.%i.WindSpeed'                  % (count+1), '')
        else:
            try:
                set_property('36Hour.%i.WindSpeed'                  % (count+1), item['fcttext_metric'].split('.')[2])
            except:
                set_property('36Hour.%i.WindSpeed'                  % (count+1), '')
        set_property('36Hour.%i.Heading'                            % (count+1), item['title'])
        set_property('36Hour.%i.Precipitation'                      % (count+1), item['pop']  + '%')
        set_property('36Hour.%i.ChancePrecipitation'                % (count+1), item['pop']  + '%')
        set_property('36Hour.%i.OutlookIcon'                        % (count+1), WEATHER_ICON % weathercode)
        set_property('36Hour.%i.FanartCode'                         % (count+1), weathercode)
        if count == 2:
            break
# hourly properties
    set_property('Hourly.IsFetched', 'true')
    for count, item in enumerate(data['hourly_forecast']):
        weathercode = WEATHER_CODES[os.path.splitext(os.path.basename(item['icon_url']))[0]]
        if TIMEFORMAT != '/':
            set_property('Hourly.%i.Time'            % (count+1), item['FCTTIME']['civil'])
        else:
            set_property('Hourly.%i.Time'            % (count+1), item['FCTTIME']['hour_padded'] + ':' + item['FCTTIME']['min'])
        if DATEFORMAT[1] == 'd':
            set_property('Hourly.%i.ShortDate'       % (count+1), item['FCTTIME']['mday_padded'] + ' ' + item['FCTTIME']['month_name_abbrev'])
            set_property('Hourly.%i.LongDate'        % (count+1), item['FCTTIME']['mday_padded'] + ' ' + item['FCTTIME']['month_name'])
        else:
            set_property('Hourly.%i.ShortDate'       % (count+1), item['FCTTIME']['month_name_abbrev'] + ' ' + item['FCTTIME']['mday_padded'])
            set_property('Hourly.%i.LongDate'        % (count+1), item['FCTTIME']['month_name'] + ' ' + item['FCTTIME']['mday_padded'])
        if 'F' in TEMPUNIT:
            set_property('Hourly.%i.Temperature'     % (count+1), item['temp']['english'] + TEMPUNIT)
            set_property('Hourly.%i.DewPoint'        % (count+1), item['dewpoint']['english'] + TEMPUNIT)
            set_property('Hourly.%i.FeelsLike'       % (count+1), item['feelslike']['english'] + TEMPUNIT)
            set_property('Hourly.%i.Precipitation'   % (count+1), item['qpf']['english'] + ' in')
            set_property('Hourly.%i.Snow'            % (count+1), item['snow']['english'] + ' in')
            set_property('Hourly.%i.HeatIndex'       % (count+1), item['heatindex']['english'] + TEMPUNIT)
            set_property('Hourly.%i.WindChill'       % (count+1), item['windchill']['english'] + TEMPUNIT)
            set_property('Hourly.%i.Mslp'            % (count+1), item['mslp']['english'] + ' inHg')
        else:
            set_property('Hourly.%i.Temperature'     % (count+1), item['temp']['metric'] + TEMPUNIT)
            set_property('Hourly.%i.DewPoint'        % (count+1), item['dewpoint']['metric'] + TEMPUNIT)
            set_property('Hourly.%i.FeelsLike'       % (count+1), item['feelslike']['metric'] + TEMPUNIT)
            set_property('Hourly.%i.Precipitation'   % (count+1), item['qpf']['metric'] + ' mm')
            set_property('Hourly.%i.Snow'            % (count+1), item['snow']['metric'] + ' mm')
            set_property('Hourly.%i.HeatIndex'       % (count+1), item['heatindex']['metric'] + TEMPUNIT)
            set_property('Hourly.%i.WindChill'       % (count+1), item['windchill']['metric'] + TEMPUNIT)
            set_property('Hourly.%i.Mslp'            % (count+1), item['mslp']['metric'] + ' inHg')
        if SPEEDUNIT == 'mph':
            set_property('Hourly.%i.WindSpeed'       % (count+1), item['wspd']['english'] + ' ' + SPEEDUNIT)
        elif SPEEDUNIT == 'Beaufort':
            set_property('Hourly.%i.WindSpeed'       % (count+1), KPHTOBFT(int(item['wspd']['metric'])))
        else:
            set_property('Hourly.%i.WindSpeed'       % (count+1), item['wspd']['metric'] + ' ' + SPEEDUNIT)
        set_property('Hourly.%i.WindDirection'       % (count+1), item['wdir']['dir'])
        set_property('Hourly.%i.ShortWindDirection'  % (count+1), item['wdir']['dir'])
        set_property('Hourly.%i.WindDegree'          % (count+1), item['wdir']['degrees'] + u'°')
        set_property('Hourly.%i.Humidity'            % (count+1), item['humidity'] + '%')
        set_property('Hourly.%i.UVIndex'             % (count+1), item['uvi'])
        set_property('Hourly.%i.ChancePrecipitation' % (count+1), item['pop'] + '%')
        set_property('Hourly.%i.Outlook'             % (count+1), item['condition'])
        set_property('Hourly.%i.OutlookIcon'         % (count+1), WEATHER_ICON % weathercode)
        set_property('Hourly.%i.FanartCode'          % (count+1), weathercode)
# alert properties
    set_property('Alerts.IsFetched', 'true')
    if str(data['alerts']) != '[]':
        rss = ''
        alerts = ''
        for count, item in enumerate(data['alerts']):
            description = recode(item['description']) # workaround: wunderground provides a corrupt alerts message
            message = recode(item['message']) # workaround: wunderground provides a corrupt alerts message
            set_property('Alerts.%i.Description'     % (count+1), description)
            set_property('Alerts.%i.Message'         % (count+1), message)
            set_property('Alerts.%i.StartDate'       % (count+1), item['date'])
            set_property('Alerts.%i.EndDate'         % (count+1), item['expires'])
            set_property('Alerts.%i.Significance'    % (count+1), SEVERITY[item['significance']])
            rss    = rss + description.replace('\n','') + ' - '
            alerts = alerts + message + '[CR][CR]'
        set_property('Alerts.RSS'   , rss.rstrip(' - '))
        set_property('Alerts'       , alerts.rstrip('[CR][CR]'))
        set_property('Alerts.Count' , str(count+1))
    else:
        set_property('Alerts.RSS'   , '')
        set_property('Alerts'       , '')
        set_property('Alerts.Count' , '0')
# map properties
    set_property('Map.IsFetched', 'true')
    mapdir = xbmc.translatePath(os.path.join(PROFILE, 'maps'))
    if not xbmcvfs.exists(mapdir):
        xbmcvfs.mkdir(mapdir)
    dirs,items = xbmcvfs.listdir(mapdir)
    for item in items:
        xbmcvfs.delete(os.path.join(mapdir,item))
    lat = data['current_observation']['display_location']['latitude']
    lon = data['current_observation']['display_location']['longitude']
    zoom = int(ADDON.getSetting('Zoom'))
    rad = int(1000/zoom)
    animate = ADDON.getSetting('Animated')
    num = 1
    ext = '.png'
    if animate == 'true':
        num = 8
        ext = '.gif'
    url1 = 'http://api.wunderground.com/api/%s/animatedsatellite/image%s?lat=%s&lon=%s&radius=%i&width=768&height=768&key=sat_ir4&basemap=1&timelabel.x=20&timelabel.y=20&num=%i&delay=50&borders=1&gtt=107&smooth=1' % (API, ext, lat, lon, rad, num)
    url2 = 'http://api.wunderground.com/api/%s/animatedsatellite/image%s?lat=%s&lon=%s&radius=%i&width=768&height=768&key=sat_vis&basemap=1&timelabel.x=20&timelabel.y=20&num=%i&delay=50&borders=1&gtt=107&smooth=1' % (API, ext, lat, lon, rad, num)
    url3 = 'http://api.wunderground.com/api/%s/animatedradar/image%s?centerlat=%s&centerlon=%s&radius=%i&width=768&height=768&newmaps=1&timelabel=1&timelabel.y=20&num=%i&delay=50&smooth=1&noclutter=1' % (API, ext, lat, lon, rad, num)
    log('map url1: %s' % url1)
    log('map url2: %s' % url2)
    log('map url3: %s' % url3)
    data1 = get_data(url1)
    data2 = get_data(url2)
    data3 = get_data(url3)
    stamp = int(time.time())
    map1 = os.path.join(mapdir,str(stamp + 1) + ext)
    map2 = os.path.join(mapdir,str(stamp + 2) + ext)
    map3 = os.path.join(mapdir,str(stamp + 3) + ext)
    xbmcvfs.File(map1, 'w').write(data1)
    xbmcvfs.File(map2, 'w').write(data2)
    xbmcvfs.File(map3, 'w').write(data3)
    set_property('Map.1.Heading', LANGUAGE(32521))
    set_property('Map.1.Area', map1)
    set_property('Map.1.Layer', map1)
    set_property('Map.2.Heading', LANGUAGE(32522))
    set_property('Map.2.Area', map2)
    set_property('Map.2.Layer', map2)
    set_property('Map.3.Heading', LANGUAGE(32523))
    set_property('Map.3.Area', map3)
    set_property('Map.3.Layer', map3)

log('version %s started: %s' % (VERSION, sys.argv))
log('lang: %s'    % LOCALIZE)
log('speed: %s'   % SPEEDUNIT)
log('temp: %s'    % TEMPUNIT[1])
log('time: %s'    % TIMEFORMAT)
log('date: %s'    % DATEFORMAT)

set_property('WeatherProvider', ADDONNAME)
set_property('WeatherProviderLogo', xbmc.translatePath(os.path.join(CWD, 'resources', 'banner.png')))

if not API:
    log('no api key provided')
elif sys.argv[1].startswith('Location'):
    keyboard = xbmc.Keyboard('', xbmc.getLocalizedString(14024), False)
    keyboard.doModal()
    if (keyboard.isConfirmed() and keyboard.getText() != ''):
        text = keyboard.getText()
        locations, locationids = location(text)
        dialog = xbmcgui.Dialog()
        if locations != []:
            selected = dialog.select(xbmc.getLocalizedString(396), locations)
            if selected != -1:
                ADDON.setSetting(sys.argv[1], locations[selected])
                ADDON.setSetting(sys.argv[1] + 'id', locationids[selected])
                log('selected location: %s' % locations[selected])
                log('selected location id: %s' % locationids[selected])
        else:
            dialog.ok(ADDONNAME, xbmc.getLocalizedString(284))
else:
    location = ADDON.getSetting('Location%s' % sys.argv[1])
    locationid = ADDON.getSetting('Location%sid' % sys.argv[1])
    if (locationid == '') and (sys.argv[1] != '1'):
        location = ADDON.getSetting('Location1')
        locationid = ADDON.getSetting('Location1id')
        log('trying location 1 instead')
    if locationid == '':
        log('fallback to geoip')
        location, locationid = geoip()
    if not locationid == '':
        forecast(location, locationid)
    else:
        log('no location found')
        clear()
    refresh_locations()

log('finished')
