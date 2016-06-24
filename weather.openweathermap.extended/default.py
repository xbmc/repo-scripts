# -*- coding: utf-8 -*-

import os, sys, time, urllib2, unicodedata
import xbmc, xbmcgui, xbmcaddon
if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

__addon__      = xbmcaddon.Addon()
__addonname__  = __addon__.getAddonInfo('name')
__addonid__    = __addon__.getAddonInfo('id')
__cwd__        = __addon__.getAddonInfo('path').decode("utf-8")
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)

from utils import *

APPID          = '85c6f759f3424557a309da1f875b23d6'
BASE_URL       = 'http://api.openweathermap.org/data/2.5/%s'
LATLON         = __addon__.getSetting('LatLon')
WEEKEND        = __addon__.getSetting('Weekend')
STATION        = __addon__.getSetting('Station')
MAP            = __addon__.getSetting('Map')
WEATHER_ICON   = xbmc.translatePath('special://temp/weather/%s.png').decode("utf-8")
DATEFORMAT     = xbmc.getRegion('dateshort')
TIMEFORMAT     = xbmc.getRegion('meridiem')
LANGUAGE       = xbmc.getLanguage().lower()
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
        loc_name = __addon__.getSetting('Location%s' % count)
        if loc_name != '':
            locations += 1
        else:
            __addon__.setSetting('Location%sID' % count, '')
            __addon__.setSetting('Location%sdeg' % count, '')
        set_property('Location%s' % count, loc_name)
    set_property('Locations', str(locations))
    log('available locations: %s' % str(locations))

def get_data(search_string):
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

def location(string):
    locs    = []
    locids  = []
    locdegs = []
    log('location: %s' % string)
    loc = unicodedata.normalize('NFKD', unicode(string, 'utf-8')).encode('ascii','ignore')
    log('searching for location: %s' % loc)
    search_string = 'find?q=%s&type=like&APPID=%s' % (urllib2.quote(loc), APPID)
    query = get_data(search_string)
    log('location data: %s' % query)
    try:
        data = json.loads(query)
    except:
        log('failed to parse location data')
        data = ''
    if data != '' and data.has_key('list'):
        for item in data['list']:
            if item['name'] == '': # bug? test by searching for california
                location = UPPERCASE(string)
            else:
                location   = item['name']
            locationid = item['id']
            locationlat = item['coord']['lat']
            locationlon = item['coord']['lon']
            locdeg = [locationlat,locationlon]
            locationcountry = item['sys']['country']
            if LATLON == 'true':
                locs.append(location + ' (' + locationcountry + ') - lat/lon:' + str(locationlat) + '/' + str(locationlon))
            else:
                locs.append(location + ' (' + locationcountry + ')')
            locids.append(locationid)
            locdegs.append(locdeg)
    log('locs' % locs)
    log('locids' % locids)
    log('locdegs' % locdegs)
    return locs, locids, locdegs

def forecast(loc,locid,locationdeg):
    log('weather location: %s' % locid)
    if MAP == 'true' and xbmc.getCondVisibility('System.HasAddon(script.openweathermap.maps)'):
        lat = float(eval(locationdeg)[0])
        lon = float(eval(locationdeg)[1])
        xbmc.executebuiltin('XBMC.RunAddon(script.openweathermap.maps,lat=%s&lon=%s)' % (lat, lon))
    else:
        set_property('Map.IsFetched', '')
        for count in range (1, 6):
            set_property('Map.%i.Layer' % count, '')
            set_property('Map.%i.Area' % count, '')
            set_property('Map.%i.Heading' % count, '')
            set_property('Map.%i.Legend' % count, '')
    try:
        lang = LANG[LANGUAGE]
        if lang == '':
            lang = 'en'
    except:
        lang = 'en'
    query = locid
    if not locid.startswith('lat'):
        query = 'id=' + locid
    if STATION == 'true':
        station_id = __addon__.getSetting('StationID')
        station_string = 'station?id=%s&lang=%s&APPID=%s&units=metric' % (station_id, lang, APPID)
    current_string = 'weather?%s&lang=%s&APPID=%s&units=metric' % (query, lang, APPID)
    hourly_string = 'forecast?%s&lang=%s&APPID=%s&units=metric' % (query, lang, APPID)
    daily_string = 'forecast/daily?%s&lang=%s&APPID=%s&units=metric&cnt=16' % (query, lang, APPID)
    retry = 0
    failed = False
    while (retry < 6) and (not MONITOR.abortRequested()):
        current_data = get_data(current_string)
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
    if current_weather != '' and current_weather.has_key('cod') and not current_weather['cod'] == '404':
        current_props(current_weather,loc)
    else:
        clear()
    if STATION == 'true':
        station_data = get_data(station_string)
        log('station data: %s' % station_data)
        try:
            station_weather = json.loads(station_data)
        except:
            log('parsing station data failed')
            station_weather = ''
        if station_weather != '' and not station_weather.has_key('message'):
            station_props(station_weather,loc)
    daily_data = get_data(daily_string)
    log('daily data: %s' % daily_data)
    try:
        daily_weather = json.loads(daily_data)
    except:
        log('parsing daily data failed')
        daily_weather = ''
    daynum = ''
    if daily_weather != '' and daily_weather.has_key('cod') and not daily_weather['cod'] == '404':
        daynum = daily_props(daily_weather)
    hourly_data = get_data(hourly_string)
    log('hourly data: %s' % hourly_data)
    try:
        hourly_weather = json.loads(hourly_data)
    except:
        log('parsing hourly data failed')
        hourly_weather = ''
    if hourly_weather != '' and hourly_weather.has_key('cod') and not hourly_weather['cod'] == '404':
        hourly_props(hourly_weather, daynum)

def station_props(data,loc):
# standard properties
    set_property('Current.Location'             , loc)
    if data.has_key('last') and data['last'].has_key('main') and data['last']['main'].has_key('temp'):
        set_property('Current.Temperature'      , str(int(round(data['last']['main']['temp'])) - 273)) # api values are in K
    if data.has_key('last') and data['last'].has_key('main') and data['last']['main'].has_key('humidity'):
        set_property('Current.Humidity'         , str(data['last']['main']['humidity']))
    if data.has_key('last') and data['last'].has_key('wind') and data['last']['wind'].has_key('speed'):
        set_property('Current.Wind'             , str(int(round(data['last']['wind']['speed'] * 3.6))))
    if data.has_key('last') and data['last'].has_key('wind') and data['last']['wind'].has_key('deg'):
        set_property('Current.WindDirection'    , xbmc.getLocalizedString(WIND_DIR(int(round(data['last']['wind']['deg'])))))
    try:
        set_property('Current.FeelsLike'        , FEELS_LIKE(data['last']['main']['temp'] -273, data['last']['wind']['speed'], False)) # api values are in K
    except:
        pass
    if data.has_key('last') and data['last'].has_key('calc') and data['last']['calc'].has_key('dewpoint'):
        if data['last']['main']['temp'] - data['last']['calc']['dewpoint'] > 100:
            set_property('Current.DewPoint'     , str(int(round(data['last']['calc']['dewpoint'])))) # api values are in C
        else:
            set_property('Current.DewPoint'     , str(int(round(data['last']['calc']['dewpoint'])) - 273)) # api values are in K
    else:
        try:
            set_property('Current.DewPoint'     , DEW_POINT(data['last']['main']['temp'] -273, data['last']['main']['humidity'], False)) # api values are in K
        except:
            pass
    #set_property('Current.UVIndex'              , '') # no idea how the api returns it, use data from current_props()
# extended properties
    if data.has_key('last') and data['last'].has_key('clouds') and data['last']['clouds'][0] != '':
        set_property('Current.Cloudiness'       , data['last']['clouds'][0]['condition'])
    if data.has_key('last') and data['last'].has_key('wind') and data['last']['wind'].has_key('gust'):
        set_property('Current.WindGust'         , SPEED(data['last']['wind']['gust']) + SPEEDUNIT)
    if data.has_key('last') and data['last'].has_key('rain') and data['last']['rain'].has_key('1h'):
        if 'F' in TEMPUNIT:
            set_property('Current.Precipitation', str(round(data['last']['rain']['1h'] *  0.04 ,2)) + ' in')
        else:
            set_property('Current.Precipitation', str(int(round(data['last']['rain']['1h']))) + ' mm')
    if data.has_key('last') and data['last'].has_key('main') and data['last']['main'].has_key('pressure'):
        if 'F' in TEMPUNIT:
            set_property('Current.Pressure'     , str(round(data['last']['main']['pressure'] / 33.86 ,2)) + ' in')
        else:
            set_property('Current.Pressure'     , str(data['last']['main']['pressure']) + ' mb')

def current_props(data,loc):
# standard properties
    code = str(data['weather'][0]['id'])
    icon = data['weather'][0]['icon']
    if icon.endswith('n'):
        code = code + 'n'
    weathercode = WEATHER_CODES[code]
    set_property('Current.Location'             , loc)
    set_property('Current.Condition'            , CAPITALIZE(data['weather'][0]['description']))
    set_property('Current.Temperature'          , str(int(round(data['main']['temp']))))
    if data['wind'].has_key('speed'):
        set_property('Current.Wind'             , str(int(round(data['wind']['speed'] * 3.6))))
        set_property('Current.FeelsLike'        , FEELS_LIKE(data['main']['temp'], data['wind']['speed'], False))
    else:
        set_property('Current.Wind'             , '')
        set_property('Current.FeelsLike'        , '')
    if data['wind'].has_key('deg'):
        set_property('Current.WindDirection'    , xbmc.getLocalizedString(WIND_DIR(int(round(data['wind']['deg'])))))
    else:
        set_property('Current.WindDirection'    , '')
    set_property('Current.Humidity'             , str(data['main']['humidity']))
    set_property('Current.DewPoint'             , DEW_POINT(data['main']['temp'], data['main']['humidity'], False))
    set_property('Current.UVIndex'              , '') # not supported by openweathermap
    set_property('Current.OutlookIcon'          , '%s.png' % weathercode) # xbmc translates it to Current.ConditionIcon
    set_property('Current.FanartCode'           , weathercode)
# extended properties
    set_property('Current.Cloudiness'           , str(data['clouds']['all']) + '%')
    set_property('Current.ShortOutlook'         , data['weather'][0]['main'])
    if data['main'].has_key('temp_min'):
        set_property('Current.LowTemperature'   , TEMP(data['main']['temp_min']) + TEMPUNIT)
    else:
        set_property('Current.LowTemperature'   , '')
    if data['main'].has_key('temp_max'):
        set_property('Current.HighTemperature'  , TEMP(data['main']['temp_max']) + TEMPUNIT)
    else:
        set_property('Current.HighTemperature'  , '')
    if 'F' in TEMPUNIT:
        set_property('Current.Pressure'         , str(round(data['main']['pressure'] / 33.86 ,2)) + ' in')
        if data['main'].has_key('sea_level'):
            set_property('Current.SeaLevel'     , str(round(data['main']['sea_level'] / 33.86 ,2)) + ' in')
        else:
            set_property('Current.SeaLevel'     , '')
        if data['main'].has_key('grnd_level'):
            set_property('Current.GroundLevel'  , str(round(data['main']['grnd_level'] / 33.86 ,2)) + ' in')
        else:
            set_property('Current.GroundLevel'  , '')
        rain = 0
        snow = 0
        if data.has_key('rain'):
            if data['rain'].has_key('1h'):
                rain = data['rain']['1h']
            elif data['rain'].has_key('3h'):
                rain = data['rain']['3h']
            set_property('Current.Rain'         , str(round(rain *  0.04 ,2)) + ' in')
        else:
            set_property('Current.Rain'         , '')
        if data.has_key('snow'):
            if data['snow'].has_key('1h'):
                snow = data['snow']['1h']
            elif data['snow'].has_key('3h'):
                snow = data['snow']['3h']
            set_property('Current.Snow'         , str(round(snow *  0.04 ,2)) + ' in')
        else:
            set_property('Current.Snow'         , '')
        precip = rain + snow
        set_property('Current.Precipitation'    , str(round(precip *  0.04 ,2)) + ' in')
    else:
        set_property('Current.Pressure'         , str(data['main']['pressure']) + ' mb')
        if data['main'].has_key('sea_level'):
            set_property('Current.SeaLevel'     , str(data['main']['sea_level']) + ' mb')
        else:
            set_property('Current.SeaLevelSnow' , '')
        if data['main'].has_key('grnd_level'):
            set_property('Current.GroundLevel'  , str(data['main']['grnd_level']) + ' mb')
        else:
            set_property('Current.GroundLevel'  , '')
        rain = 0
        snow = 0
        if data.has_key('rain'):
            if data['rain'].has_key('1h'):
                rain = data['rain']['1h']
            elif data['rain'].has_key('3h'):
                rain = data['rain']['3h']
            set_property('Current.Rain'         , str(int(round(rain))) + ' mm')
        else:
            set_property('Current.Rain'         , '')
        if data.has_key('snow'):
            if data['snow'].has_key('1h'):
                snow = data['snow']['1h']
            elif data['snow'].has_key('3h'):
                snow = data['snow']['3h']
            set_property('Current.Snow'         , str(int(round(snow))) + ' mm')
        else:
            set_property('Current.Snow'         , '')
        precip = rain + snow
        set_property('Current.Precipitation'    , str(int(round(precip))) + ' mm')
    if data['wind'].has_key('gust'):
        set_property('Current.WindGust'         , SPEED(data['wind']['gust']) + SPEEDUNIT)
    else:
        set_property('Current.WindGust'         , '')
    if data['wind'].has_key('var_beg'):
        set_property('Current.WindDirStart'     , xbmc.getLocalizedString(WIND_DIR(data['wind']['var_beg'])))
    else:
        set_property('Current.WindDirStart'     , '')
    if data['wind'].has_key('var_end'):
        set_property('Current.WindDirEnd'       , xbmc.getLocalizedString(WIND_DIR(data['wind']['var_end'])))
    else:
        set_property('Current.WindDirEnd'       , '')
    set_property('Forecast.City'                , data['name'])
    set_property('Forecast.Country'             , data['sys']['country'])
    set_property('Forecast.Latitude'            , str(data['coord']['lat']))
    set_property('Forecast.Longitude'           , str(data['coord']['lon']))
    set_property('Forecast.Updated'             , convert_date(data['dt']))
    set_property('Today.Sunrise'                , convert_date(data['sys']['sunrise']).split('  ')[0])
    set_property('Today.Sunset'                 , convert_date(data['sys']['sunset']).split('  ')[0])

def daily_props(data):
# standard properties
    for count, item in enumerate(data['list']):
        code = str(item['weather'][0]['id'])
        icon = item['weather'][0]['icon']
        if icon.endswith('n'):
            code = code + 'n'
        weathercode = WEATHER_CODES[code]
        set_property('Day%i.Title'              % count, get_weekday(item['dt'], 's'))
        set_property('Day%i.HighTemp'           % count, str(int(round(item['temp']['max']))))
        set_property('Day%i.LowTemp'            % count, str(int(round(item['temp']['min']))))
        set_property('Day%i.Outlook'            % count, CAPITALIZE(item['weather'][0]['description']))
        set_property('Day%i.OutlookIcon'        % count, '%s.png' % weathercode)
        set_property('Day%i.FanartCode'         % count, weathercode)
        if count == MAXDAYS:
            break
# extended properties
    for count, item in enumerate(data['list']):
        code = str(item['weather'][0]['id'])
        icon = item['weather'][0]['icon']
        if icon.endswith('n'):
            code = code + 'n'
        weathercode = WEATHER_CODES[code]
        set_property('Daily.%i.LongDay'         % (count+1), get_weekday(item['dt'], 'l'))
        set_property('Daily.%i.ShortDay'        % (count+1), get_weekday(item['dt'], 's'))
        if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
            set_property('Daily.%i.LongDate'    % (count+1), get_month(item['dt'], 'dl'))
            set_property('Daily.%i.ShortDate'   % (count+1), get_month(item['dt'], 'ds'))
        else:
            set_property('Daily.%i.LongDate'    % (count+1), get_month(item['dt'], 'ml'))
            set_property('Daily.%i.ShortDate'   % (count+1), get_month(item['dt'], 'ms'))
        set_property('Daily.%i.Outlook'         % (count+1), CAPITALIZE(item['weather'][0]['description']))
        set_property('Daily.%i.ShortOutlook'    % (count+1), item['weather'][0]['main'])
        set_property('Daily.%i.OutlookIcon'     % (count+1), WEATHER_ICON % weathercode)
        set_property('Daily.%i.FanartCode'      % (count+1), weathercode)
        set_property('Daily.%i.WindDirection'   % (count+1), xbmc.getLocalizedString(int(round(WIND_DIR(item['deg'])))))
        set_property('Daily.%i.WindDegree'      % (count+1), str(item['deg']) + u'°')
        set_property('Daily.%i.Humidity'        % (count+1), str(item['humidity']) + '%')
        set_property('Daily.%i.TempMorn'        % (count+1), TEMP(item['temp']['morn']) + TEMPUNIT)
        set_property('Daily.%i.TempDay'         % (count+1), TEMP(item['temp']['day']) + TEMPUNIT)
        set_property('Daily.%i.TempEve'         % (count+1), TEMP(item['temp']['eve']) + TEMPUNIT)
        set_property('Daily.%i.TempNight'       % (count+1), TEMP(item['temp']['night']) + TEMPUNIT)
        set_property('Daily.%i.HighTemperature' % (count+1), TEMP(item['temp']['max']) + TEMPUNIT)
        set_property('Daily.%i.LowTemperature'  % (count+1), TEMP(item['temp']['min']) + TEMPUNIT)
        set_property('Daily.%i.FeelsLike'       % (count+1), FEELS_LIKE(item['temp']['day'], item['speed']) + TEMPUNIT)
        set_property('Daily.%i.DewPoint'        % (count+1), DEW_POINT(item['temp']['day'], item['humidity']) + TEMPUNIT)
        if 'F' in TEMPUNIT:
            set_property('Daily.%i.Pressure'        % (count+1), str(round(item['pressure'] / 33.86 ,2)) + ' in')
            rain = 0
            snow = 0
            if item.has_key('rain'):
                rain = item['rain']
                set_property('Daily.%i.Rain'        % (count+1), str(round(rain * 0.04 ,2)) + ' in')
            else:
                set_property('Daily.%i.Rain'        % (count+1), '')
            if item.has_key('snow'):
                snow = item['snow']
                set_property('Daily.%i.Snow'        % (count+1), str(round(snow * 0.04 ,2)) + ' in')
            else:
                set_property('Daily.%i.Snow'        % (count+1), '')
            precip = rain + snow
            set_property('Daily.%i.Precipitation'   % (count+1), str(round(precip * 0.04 ,2)) + ' in')
        else:
            set_property('Daily.%i.Pressure'        % (count+1), str(item['pressure']) + ' mb')
            rain = 0
            snow = 0
            if item.has_key('rain'):
                rain = item['rain']
                set_property('Daily.%i.Rain'        % (count+1), str(int(round(rain))) + ' mm')
            else:
                set_property('Daily.%i.Rain'        % (count+1), '')
            if item.has_key('snow'):
                snow = item['snow']
                set_property('Daily.%i.Snow'        % (count+1), str(int(round(snow))) + ' mm')
            else:
                set_property('Daily.%i.Snow'        % (count+1), '')
            precip = rain + snow
            set_property('Daily.%i.Precipitation'   % (count+1), str(int(round(precip))) + ' mm')
        set_property('Daily.%i.WindSpeed'           % (count+1), SPEED(item['speed']) + SPEEDUNIT)
        if item.has_key('gust'): 
            set_property('Daily.%i.WindGust'        % (count+1), SPEED(item['gust']) + SPEEDUNIT)
        else:
            set_property('Daily.%i.WindGust'        % (count+1), '')
        set_property('Daily.%i.Cloudiness'          % (count+1), str(item['clouds']) + '%')
    if WEEKEND == '2':
        weekend = [4,5]
    elif WEEKEND == '1':
        weekend = [5,6]
    else:
        weekend = [6,0]
    count = 0
    for item in (data['list']):
        if get_weekday(item['dt'], 'x') in weekend:
            code = str(item['weather'][0]['id'])
            icon = item['weather'][0]['icon']
            if icon.endswith('n'):
                code = code + 'n'
            weathercode = WEATHER_CODES[code]
            set_property('Weekend.%i.LongDay'         % (count+1), get_weekday(item['dt'], 'l'))
            set_property('Weekend.%i.ShortDay'        % (count+1), get_weekday(item['dt'], 's'))
            if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
                set_property('Weekend.%i.LongDate'    % (count+1), get_month(item['dt'], 'dl'))
                set_property('Weekend.%i.ShortDate'   % (count+1), get_month(item['dt'], 'ds'))
            else:
                set_property('Weekend.%i.LongDate'    % (count+1), get_month(item['dt'], 'ml'))
                set_property('Weekend.%i.ShortDate'   % (count+1), get_month(item['dt'], 'ms'))
            set_property('Weekend.%i.Outlook'         % (count+1), CAPITALIZE(item['weather'][0]['description']))
            set_property('Weekend.%i.ShortOutlook'    % (count+1), item['weather'][0]['main'])
            set_property('Weekend.%i.OutlookIcon'     % (count+1), WEATHER_ICON % weathercode)
            set_property('Weekend.%i.FanartCode'      % (count+1), weathercode)
            set_property('Weekend.%i.WindDirection'   % (count+1), xbmc.getLocalizedString(int(round(WIND_DIR(item['deg'])))))
            set_property('Weekend.%i.WindDegree'      % (count+1), str(item['deg']) + u'°')
            set_property('Weekend.%i.Humidity'        % (count+1), str(item['humidity']) + '%')
            set_property('Weekend.%i.Cloudiness'      % (count+1), str(item['clouds']) + '%')
            set_property('Weekend.%i.TempMorn'        % (count+1), TEMP(item['temp']['morn']) + TEMPUNIT)
            set_property('Weekend.%i.TempDay'         % (count+1), TEMP(item['temp']['day']) + TEMPUNIT)
            set_property('Weekend.%i.TempEve'         % (count+1), TEMP(item['temp']['eve']) + TEMPUNIT)
            set_property('Weekend.%i.TempNight'       % (count+1), TEMP(item['temp']['night']) + TEMPUNIT)
            set_property('Weekend.%i.HighTemperature' % (count+1), TEMP(item['temp']['max']) + TEMPUNIT)
            set_property('Weekend.%i.LowTemperature'  % (count+1), TEMP(item['temp']['min']) + TEMPUNIT)
            set_property('Weekend.%i.DewPoint'        % (count+1), DEW_POINT(item['temp']['day'], item['humidity']) + TEMPUNIT)
            set_property('Weekend.%i.FeelsLike'       % (count+1), FEELS_LIKE(item['temp']['day'], item['speed']) + TEMPUNIT)
            if 'F' in TEMPUNIT:
                set_property('Weekend.%i.Pressure'        % (count+1), str(round(item['pressure'] / 33.86 ,2)) + ' in')
                rain = 0
                snow = 0
                if item.has_key('rain'):
                    rain = item['rain']
                    set_property('Weekend.%i.Rain'        % (count+1), str(round(rain * 0.04 ,2)) + ' in')
                else:
                    set_property('Weekend.%i.Rain'        % (count+1), '')
                if item.has_key('snow'):
                    snow = item['snow']
                    set_property('Weekend.%i.Snow'        % (count+1), str(round(snow * 0.04 ,2)) + ' in')
                else:
                    set_property('Weekend.%i.Snow'        % (count+1), '')
                precip = rain + snow
                set_property('Weekend.%i.Precipitation'   % (count+1), str(round(precip * 0.04 ,2)) + ' in')
            else:
                set_property('Weekend.%i.Pressure'        % (count+1), str(item['pressure']) + ' mb')
                rain = 0
                snow = 0
                if item.has_key('rain'):
                    rain = item['rain']
                    set_property('Weekend.%i.Rain'        % (count+1), str(int(round(rain))) + ' mm')
                else:
                    set_property('Weekend.%i.Rain'        % (count+1), '')
                if item.has_key('snow'):
                    snow = item['snow']
                    set_property('Weekend.%i.Snow'        % (count+1), str(int(round(snow))) + ' mm')
                else:
                    set_property('Weekend.%i.Snow'        % (count+1), '')
                precip = rain + snow
                set_property('Weekend.%i.Precipitation'   % (count+1), str(int(round(precip))) + ' mm')
            set_property('Weekend.%i.WindSpeed'           % (count+1), SPEED(item['speed']) + SPEEDUNIT)
            if item.has_key('gust'): 
                set_property('Weekend.%i.WindGust'        % (count+1), SPEED(item['gust']) + SPEEDUNIT)
            else:
                set_property('Weekend.%i.WindGust'        % (count+1), '')
            count += 1
            if count == 2:
                break
    count = 0
    for item in (data['list']):
        if count == 1:
           count = 2
        code = str(item['weather'][0]['id'])
        icon = item['weather'][0]['icon']
        if icon.endswith('n'):
            code = code + 'n'
        weathercode = WEATHER_CODES[code]
        set_property('36Hour.%i.LongDay'         % (count+1), get_weekday(item['dt'], 'l'))
        set_property('36Hour.%i.ShortDay'        % (count+1), get_weekday(item['dt'], 's'))
        if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
            set_property('36Hour.%i.LongDate'    % (count+1), get_month(item['dt'], 'dl'))
            set_property('36Hour.%i.ShortDate'   % (count+1), get_month(item['dt'], 'ds'))
        else:
            set_property('36Hour.%i.LongDate'    % (count+1), get_month(item['dt'], 'ml'))
            set_property('36Hour.%i.ShortDate'   % (count+1), get_month(item['dt'], 'ms'))
        set_property('36Hour.%i.Outlook'         % (count+1), CAPITALIZE(item['weather'][0]['description']))
        set_property('36Hour.%i.ShortOutlook'    % (count+1), item['weather'][0]['main'])
        set_property('36Hour.%i.OutlookIcon'     % (count+1), WEATHER_ICON % weathercode)
        set_property('36Hour.%i.FanartCode'      % (count+1), weathercode)
        set_property('36Hour.%i.WindDirection'   % (count+1), xbmc.getLocalizedString(int(round(WIND_DIR(item['deg'])))))
        set_property('36Hour.%i.WindDegree'      % (count+1), str(item['deg']) + u'°')
        set_property('36Hour.%i.Humidity'        % (count+1), str(item['humidity']) + '%')
        set_property('36Hour.%i.Temperature'     % (count+1), TEMP(item['temp']['day']) + TEMPUNIT)
        set_property('36Hour.%i.HighTemperature' % (count+1), TEMP(item['temp']['max']) + TEMPUNIT)
        set_property('36Hour.%i.LowTemperature'  % (count+1), TEMP(item['temp']['min']) + TEMPUNIT)
        set_property('36Hour.%i.FeelsLike'       % (count+1), FEELS_LIKE(item['temp']['day'], item['speed']) + TEMPUNIT)
        set_property('36Hour.%i.DewPoint'        % (count+1), DEW_POINT(item['temp']['day'], item['humidity']) + TEMPUNIT)
        if 'F' in TEMPUNIT:
            set_property('36Hour.%i.Pressure'        % (count+1), str(round(item['pressure'] / 33.86 ,2)) + ' in')
            rain = 0
            snow = 0
            if item.has_key('rain'):
                rain = item['rain']
                set_property('36Hour.%i.Rain'        % (count+1), str(round(rain * 0.04 ,2)) + ' in')
            else:
                set_property('36Hour.%i.Rain'        % (count+1), '')
            if item.has_key('snow'):
                snow = item['snow']
                set_property('36Hour.%i.Snow'        % (count+1), str(round(snow * 0.04 ,2)) + ' in')
            else:
                set_property('36Hour.%i.Snow'        % (count+1), '')
            precip = rain + snow
            set_property('36Hour.%i.Precipitation'   % (count+1), str(round(precip * 0.04 ,2)) + ' in')
        else:
            set_property('36Hour.%i.Pressure'        % (count+1), str(item['pressure']) + ' mb')
            rain = 0
            snow = 0
            if item.has_key('rain'):
                rain = item['rain']
                set_property('36Hour.%i.Rain'        % (count+1), str(int(round(rain))) + ' mm')
            else:
                set_property('36Hour.%i.Rain'        % (count+1), '')
            if item.has_key('snow'):
                snow = item['snow']
                set_property('36Hour.%i.Snow'        % (count+1), str(int(round(snow))) + ' mm')
            else:
                set_property('36Hour.%i.Snow'        % (count+1), '')
            precip = rain + snow
            set_property('36Hour.%i.Precipitation'   % (count+1), str(int(round(precip))) + ' mm')
        set_property('36Hour.%i.WindSpeed'           % (count+1), SPEED(item['speed']) + SPEEDUNIT)
        if item.has_key('gust'): 
            set_property('36Hour.%i.WindGust'        % (count+1), SPEED(item['gust']) + SPEEDUNIT)
        else:
            set_property('36Hour.%i.WindGust'        % (count+1), '')
        set_property('36Hour.%i.Cloudiness'          % (count+1), str(item['clouds']) + '%')
        if count == 0:
            set_property('36Hour.%i.Heading'         % (count+1), xbmc.getLocalizedString(33006))
        else:
            set_property('36Hour.%i.Heading'         % (count+1), xbmc.getLocalizedString(33007))
        set_property('36Hour.%i.TemperatureHeading'  % (count+1), xbmc.getLocalizedString(393))
        count += 1
        if count >= 2:
            daynum = get_month(item['dt'], 'ds').split(' ')[0]
            return daynum

def hourly_props(data, daynum):
# extended properties
    for count, item in enumerate(data['list']):
        code = str(item['weather'][0]['id'])
        icon = item['weather'][0]['icon']
        if icon.endswith('n'):
            code = code + 'n'
        weathercode = WEATHER_CODES[code]
        set_property('Hourly.%i.Time'            % (count+1), get_time(item['dt']))
        if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
            set_property('Hourly.%i.LongDate'    % (count+1), get_month(item['dt'], 'dl'))
            set_property('Hourly.%i.ShortDate'   % (count+1), get_month(item['dt'], 'ds'))
        else:
            set_property('Hourly.%i.LongDate'    % (count+1), get_month(item['dt'], 'ml'))
            set_property('Hourly.%i.ShortDate'   % (count+1), get_month(item['dt'], 'ms'))
        set_property('Hourly.%i.Outlook'         % (count+1), CAPITALIZE(item['weather'][0]['description']))
        set_property('Hourly.%i.ShortOutlook'    % (count+1), item['weather'][0]['main'])
        set_property('Hourly.%i.OutlookIcon'     % (count+1), WEATHER_ICON % weathercode)
        set_property('Hourly.%i.FanartCode'      % (count+1), weathercode)
        set_property('Hourly.%i.Humidity'        % (count+1), str(item['main']['humidity']) + '%')
        if item['wind']:
            if item['wind'].has_key('deg'):
                set_property('Hourly.%i.WindDirection'   % (count+1), xbmc.getLocalizedString(WIND_DIR(int(round(item['wind']['deg'])))))
                set_property('Hourly.%i.WindDegree'      % (count+1), str(item['wind']['deg']) + u'°')
            else:
                set_property('Hourly.%i.WindDirection'   % (count+1), '')
                set_property('Hourly.%i.WindDegree'      % (count+1), '')
            if item['wind'].has_key('speed'):
                set_property('Hourly.%i.WindSpeed'       % (count+1), SPEED(item['wind']['speed']) + SPEEDUNIT)
                set_property('Hourly.%i.FeelsLike'       % (count+1), FEELS_LIKE(item['main']['temp'], item['wind']['speed']) + TEMPUNIT)
            else:
                set_property('Hourly.%i.WindSpeed'       % (count+1), '')
                set_property('Hourly.%i.FeelsLike'       % (count+1), '')
            if item['wind'].has_key('gust'):
                set_property('Hourly.%i.WindGust'        % (count+1), SPEED(item['wind']['gust']) + SPEEDUNIT)
            else:
                set_property('Hourly.%i.WindGust'        % (count+1), '')
        set_property('Hourly.%i.Cloudiness'          % (count+1), str(item['clouds']['all']) + '%')
        set_property('Hourly.%i.Temperature'         % (count+1), TEMP(item['main']['temp']) + TEMPUNIT)
        set_property('Hourly.%i.HighTemperature'     % (count+1), TEMP(item['main']['temp_max']) + TEMPUNIT)
        set_property('Hourly.%i.LowTemperature'      % (count+1), TEMP(item['main']['temp_min']) + TEMPUNIT)
        set_property('Hourly.%i.DewPoint'            % (count+1), DEW_POINT(item['main']['temp'], item['main']['humidity']) + TEMPUNIT)
        if 'F' in TEMPUNIT:
            set_property('Hourly.%i.Pressure'        % (count+1), str(round(item['main']['pressure'] / 33.86 ,2)) + ' in')
            if item['main'].has_key('sea_level'):
                set_property('Hourly.%i.SeaLevel'    % (count+1), str(round(item['main']['sea_level'] / 33.86 ,2)) + ' in')
            else:
                set_property('Hourly.%i.SeaLevel'    % (count+1), '')
            if item['main'].has_key('grnd_level'):
                set_property('Hourly.%i.GroundLevel' % (count+1), str(round(item['main']['grnd_level'] / 33.86 ,2)) + ' in')
            else:
                set_property('Hourly.%i.GroundLevel' % (count+1), '')
            rain = 0
            snow = 0
            if item.has_key('rain') and item['rain'].has_key('3h'):
                rain = item['rain']['3h']
                set_property('Hourly.%i.Rain'        % (count+1), str(round(rain *  0.04 ,2)) + ' in')
            else:
                set_property('Hourly.%i.Rain'        % (count+1), '')
            if item.has_key('snow') and item['snow'].has_key('3h'):
                snow = item['snow']['3h']
                set_property('Hourly.%i.Snow'        % (count+1), str(round(snow *  0.04 ,2)) + ' in')
            else:
                set_property('Hourly.%i.Snow'        % (count+1), '')
            precip = rain + snow
            set_property('Hourly.%i.Precipitation'   % (count+1), str(round(precip *  0.04 ,2)) + ' in')
        else:
            set_property('Hourly.%i.Pressure'        % (count+1), str(item['main']['pressure']) + ' mb')
            if item['main'].has_key('sea_level'):
                set_property('Hourly.%i.SeaLevel'    % (count+1), str(item['main']['sea_level']) + ' mb')
            else:
                set_property('Hourly.%i.SeaLevel'    % (count+1), '')
            if item['main'].has_key('grnd_level'):
                set_property('Hourly.%i.GroundLevel' % (count+1), str(item['main']['grnd_level']) + ' mb')
            else:
                set_property('Hourly.%i.GroundLevel' % (count+1), '')
            rain = 0
            snow = 0
            if item.has_key('rain') and item['rain'].has_key('3h'):
                rain = item['rain']['3h']
                set_property('Hourly.%i.Rain'        % (count+1), str(int(round(rain))) + ' mm')
            else:
                set_property('Hourly.%i.Rain'        % (count+1), '')
            if item.has_key('snow') and item['snow'].has_key('3h'):
                snow = item['snow']['3h']
                set_property('Hourly.%i.Snow'        % (count+1), str(int(round(snow))) + ' mm')
            else:
                set_property('Hourly.%i.Snow'        % (count+1), '')
            precip = rain + snow
            set_property('Hourly.%i.Precipitation'   % (count+1), str(int(round(precip))) + ' mm')
    count = 1
    if daynum == '':
        return
    for item in (data['list']):
        day_num = get_month(item['dt'], 'ds').split(' ')[0]
        if day_num == daynum:
            day_time = get_time(item['dt'])[0:2].lstrip('0').rstrip(':')
            if day_time == '':
                day_time = 0
            if int(day_time) > 2:
                code = str(item['weather'][0]['id'])
                icon = item['weather'][0]['icon']
                if icon.endswith('n'):
                    code = code + 'n'
                weathercode = WEATHER_CODES[code]
                set_property('36Hour.%i.Time'            % (count+1), get_time(item['dt']))
                if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
                    set_property('36Hour.%i.LongDate'    % (count+1), get_month(item['dt'], 'dl'))
                    set_property('36Hour.%i.ShortDate'   % (count+1), get_month(item['dt'], 'ds'))
                else:
                    set_property('36Hour.%i.LongDate'    % (count+1), get_month(item['dt'], 'ml'))
                    set_property('36Hour.%i.ShortDate'   % (count+1), get_month(item['dt'], 'ms'))
                set_property('36Hour.%i.Outlook'         % (count+1), CAPITALIZE(item['weather'][0]['description']))
                set_property('36Hour.%i.ShortOutlook'    % (count+1), item['weather'][0]['main'])
                set_property('36Hour.%i.OutlookIcon'     % (count+1), WEATHER_ICON % weathercode)
                set_property('36Hour.%i.FanartCode'      % (count+1), weathercode)
                set_property('36Hour.%i.Humidity'        % (count+1), str(item['main']['humidity']) + '%')
                set_property('36Hour.%i.Cloudiness'      % (count+1), str(item['clouds']['all']) + '%')
                set_property('36Hour.%i.Temperature'     % (count+1), TEMP(item['main']['temp']) + TEMPUNIT)
                set_property('36Hour.%i.HighTemperature' % (count+1), TEMP(item['main']['temp_max']) + TEMPUNIT)
                set_property('36Hour.%i.LowTemperature'  % (count+1), TEMP(item['main']['temp_min']) + TEMPUNIT)
                set_property('36Hour.%i.DewPoint'        % (count+1), DEW_POINT(item['main']['temp'], item['main']['humidity']) + TEMPUNIT)
                if item['wind'].has_key('deg'):
                    set_property('36Hour.%i.WindDirection'   % (count+1), xbmc.getLocalizedString(WIND_DIR(int(round(item['wind']['deg'])))))
                    set_property('36Hour.%i.WindDegree'      % (count+1), str(item['wind']['deg']) + u'°')
                else:
                    set_property('36Hour.%i.WindDegree'      % (count+1), '')
                if item['wind'].has_key('speed'):
                    set_property('36Hour.%i.WindSpeed'       % (count+1), SPEED(item['wind']['speed']) + SPEEDUNIT)
                    set_property('36Hour.%i.FeelsLike'       % (count+1), FEELS_LIKE(item['main']['temp'], item['wind']['speed']) + TEMPUNIT)
                else:
                    set_property('36Hour.%i.WindSpeed'       % (count+1), '')
                    set_property('36Hour.%i.FeelsLike'       % (count+1), '')
                if item['wind'].has_key('gust'):
                    set_property('36Hour.%i.WindGust'        % (count+1), SPEED(item['wind']['gust']) + SPEEDUNIT)
                else:
                    set_property('36Hour.%i.WindGust'        % (count+1), '')
                if 'F' in TEMPUNIT:
                    set_property('36Hour.%i.Pressure'        % (count+1), str(round(item['main']['pressure'] / 33.86 ,2)) + ' in')
                    rain = 0
                    snow = 0
                    if item.has_key('rain') and item['rain'].has_key('3h'):
                        rain = item['rain']['3h']
                        set_property('36Hour.%i.Rain'        % (count+1), str(round(rain *  0.04 ,2)) + ' in')
                    else:
                        set_property('36Hour.%i.Rain'        % (count+1), '')
                    if item.has_key('snow') and item['snow'].has_key('3h'):
                        snow = item['snow']['3h']
                        set_property('36Hour.%i.Snow'        % (count+1), str(round(snow *  0.04 ,2)) + ' in')
                    else:
                        set_property('36Hour.%i.Snow'        % (count+1), '')
                    precip = rain + snow
                    set_property('36Hour.%i.Precipitation'   % (count+1), str(round(precip *  0.04 ,2)) + ' in')
                else:
                    set_property('36Hour.%i.Pressure'        % (count+1), str(item['main']['pressure']) + ' mb')
                    rain = 0
                    snow = 0
                    if item.has_key('rain') and item['rain'].has_key('3h'):
                        rain = item['rain']['3h']
                        set_property('36Hour.%i.Rain'        % (count+1), str(int(round(rain))) + ' mm')
                    else:
                        set_property('36Hour.%i.Rain'        % (count+1), '')
                    if item.has_key('snow') and item['snow'].has_key('3h'):
                        snow = item['snow']['3h']
                        set_property('36Hour.%i.Snow'        % (count+1), str(int(round(snow))) + ' mm')
                    else:
                        set_property('36Hour.%i.Snow'        % (count+1), '')
                    precip = rain + snow
                    set_property('36Hour.%i.Precipitation'   % (count+1), str(int(round(precip))) + ' mm')
                set_property('36Hour.%i.Heading'             % (count+1), xbmc.getLocalizedString(33018))
                set_property('36Hour.%i.TemperatureHeading'  % (count+1), xbmc.getLocalizedString(391))
                break

class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)

log('version %s started: %s' % (__version__, sys.argv[1]))

MONITOR = MyMonitor()
set_property('Forecast.IsFetched' , 'true')
set_property('Current.IsFetched'  , 'true')
set_property('Today.IsFetched'    , 'true')
set_property('Daily.IsFetched'    , 'true')
set_property('Weekend.IsFetched'  , 'true')
set_property('36Hour.IsFetched'   , 'true')
set_property('Hourly.IsFetched'   , 'true')
set_property('Alerts.IsFetched'   , '')
set_property('WeatherProvider'    , __language__(32000))
set_property('WeatherProviderLogo', xbmc.translatePath(os.path.join(__cwd__, 'resources', 'graphics', 'banner.png')))

if sys.argv[1].startswith('Location'):
    keyboard = xbmc.Keyboard('', xbmc.getLocalizedString(14024), False)
    keyboard.doModal()
    if (keyboard.isConfirmed() and keyboard.getText() != ''):
        text = keyboard.getText()
        locations, locationids, locationdeg = location(text)
        dialog = xbmcgui.Dialog()
        if locations != []:
            selected = dialog.select(xbmc.getLocalizedString(396), locations)
            if selected != -1:
                __addon__.setSetting(sys.argv[1], locations[selected].split(' - ')[0])
                __addon__.setSetting(sys.argv[1] + 'ID', str(locationids[selected]))
                __addon__.setSetting(sys.argv[1] + 'deg', str(locationdeg[selected]))
                log('selected location: %s' % locations[selected])
                log('selected location id: %s' % locationids[selected])
                log('selected location lat/lon: %s' % locationdeg[selected])
        else:
            dialog.ok(__addonname__, xbmc.getLocalizedString(284))
else:
    location = __addon__.getSetting('Location%s' % sys.argv[1])
    locationid = __addon__.getSetting('Location%sID' % sys.argv[1])
    locationdeg = __addon__.getSetting('Location%sdeg' % sys.argv[1])
    if (locationid == '') and (sys.argv[1] != '1'):
        location = __addon__.getSetting('Location1')
        locationid = __addon__.getSetting('Location1ID')
        locationdeg = __addon__.getSetting('Location1deg')
        log('trying location 1 instead')
    if not locationid == '':
        forecast(location, locationid, locationdeg)
    else:
        log('no location provided')
        clear()
    refresh_locations()

log('finished')
