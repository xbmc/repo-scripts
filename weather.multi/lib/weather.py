import os
import sys
import socket
import requests
import xbmc
import xbmcvfs
from .utils import *

ADDONNAME = ADDON.getAddonInfo('name')
ADDONVERSION = ADDON.getAddonInfo('version')
CWD = ADDON.getAddonInfo('path')
WEATHER_ICON = xbmc.translatePath('%s.png')

LCURL = 'https://www.yahoo.com/news/_tdnews/api/resource/WeatherSearch;text=%s'
FCURL = 'https://www.yahoo.com/news/_tdnews/api/resource/WeatherService;woeids=%%5B%s%%5D'
AURL = 'https://api.weatherbit.io/v2.0/%s'

WADD = ADDON.getSettingBool('WAdd')
APPID = ADDON.getSettingString('API')

MAPS = ADDON.getSettingBool('WMaps')
MAPID = ADDON.getSettingString('MAPAPI')
ZOOM = str(ADDON.getSettingInt('Zoom') + 2)

socket.setdefaulttimeout(10)


class MAIN():
    def __init__(self, *args, **kwargs):
        log('version %s started: %s' % (ADDONVERSION, sys.argv))
        self.MONITOR = MyMonitor()
        mode = kwargs['mode']
        if mode.startswith('loc'):
            value = ADDON.getSettingString(mode)
            keyboard = xbmc.Keyboard(value, xbmc.getLocalizedString(14024), False)
            keyboard.doModal()
            if (keyboard.isConfirmed() and keyboard.getText()):
                text = keyboard.getText()
                locs = self.get_location(text)
                dialog = xbmcgui.Dialog()
                if locs:
                    items = []
                    for item in locs:
                        listitem = xbmcgui.ListItem(item['qualifiedName'], item['city'] + ' - ' + item['country'] + ' [' + str(item['lat']) + '/' + str(item['lon']) + ']')
                        items.append(listitem)
                    selected = dialog.select(xbmc.getLocalizedString(396), items, useDetails=True)
                    if selected != -1:
                        ADDON.setSettingString(mode, locs[selected]['qualifiedName'])
                        ADDON.setSettingInt(mode + 'id', locs[selected]['woeid'])
                        ADDON.setSettingNumber(mode + 'lat', locs[selected]['lat'])
                        ADDON.setSettingNumber(mode + 'lon', locs[selected]['lon'])
                        log('selected location: %s' % str(locs[selected]))
                else:
                    log('no locations found')
                    dialog.ok(ADDONNAME, xbmc.getLocalizedString(284))
        else:
            location = ADDON.getSettingString('loc%s' % mode)
            locationid = ADDON.getSettingInt('loc%sid' % mode)
            locationlat = ADDON.getSettingNumber('loc%slat' % mode)
            locationlon = ADDON.getSettingNumber('loc%slon' % mode)
            if (locationid == -1) and (mode != '1'):
                location = ADDON.getSettingString('loc1')
                locationid = ADDON.getSettingInt('loc1id')
                locationlat = ADDON.getSettingNumber('loc1lat')
                locationlon = ADDON.getSettingNumber('loc1lon')
                log('trying location 1 instead')
            if locationid > 0:
                self.get_forecast(location, locationid, locationlat, locationlon)
            else:
                log('empty location id')
                self.clear_props()
            self.refresh_locations()
        log('finished')

    def refresh_locations(self):
        locations = 0
        for count in range(1, 6):
            loc_name = ADDON.getSettingString('loc%s' % count)
            if loc_name:
                locations += 1
            set_property('Location%s' % count, loc_name)
        set_property('Locations', str(locations))
        log('available locations: %s' % str(locations))
    
    def get_location(self, loc):
        locs = []
        log('searching for location: %s' % loc)
        url = LCURL % loc
        data = self.get_data(url)
        log('location data: %s' % data)
        if data:
            locs = data
        return locs
    
    def get_data(self, url):
        try:
            response = requests.get(url)
            return response.json()
        except:
            return
    
    def get_forecast(self, loc, locid, lat, lon):
        set_property('Forecast.IsFetched' , 'true')
        set_property('Current.IsFetched'  , 'true')
        set_property('Today.IsFetched'    , 'true')
        set_property('Daily.IsFetched'    , 'true')
        set_property('Hourly.IsFetched'   , 'true')
        set_property('WeatherProviderLogo', xbmc.translatePath(os.path.join(CWD, 'resources', 'banner.png')))
        log('weather location: %s' % locid)
        providers = 'provided by Yahoo'
        if MAPS and MAPID and xbmc.getCondVisibility('System.HasAddon(script.openweathermap.maps)'):
            xbmc.executebuiltin('XBMC.RunAddon(script.openweathermap.maps,lat=%s&lon=%s&zoom=%s&api=%s&debug=%s)' % (lat, lon, ZOOM, MAPID, DEBUG))
            providers = providers + ', Openweathermaps'
        else:
            set_property('Map.IsFetched', '')
            for count in range (1, 6):
                set_property('Map.%i.Layer' % count, '')
                set_property('Map.%i.Area' % count, '')
                set_property('Map.%i.Heading' % count, '')
                set_property('Map.%i.Legend' % count, '')
        retry = 0
        while (retry < 6) and (not self.MONITOR.abortRequested()):
            url = FCURL % locid
            data = self.get_data(url)
            if data:
                # response
                retry = 6
            else:
                # no response
                data = ''
                retry += 1
                self.MONITOR.waitForAbort(10)
                log('weather download failed')
        log('yahoo forecast data: %s' % data)
        if not data:
            self.clear_props()
            return
        add_weather = ''
        if WADD and APPID:
            daily_string = 'forecast/daily?key=%s&lat=%s&lon=%s' % (APPID, lat, lon)
            url = AURL % daily_string
            add_weather = self.get_data(url)
            log('weatherbit data: %s' % add_weather)
            if 'error' in add_weather:
                add_weather = ''
        self.set_properties(data, loc, locid)
        if add_weather and add_weather != '':
            self.add_props(add_weather)
            providers = providers + ', Weatherbit.io'
        else:
            self.daily_properties(data, loc, locid)
        set_property('WeatherProvider', providers)
        
    def clear_props(self):
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
    
    def set_properties(self, response, loc, locid):
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
        set_property('Current.WindChill'         , YTEMP(windchill(data['observation']['temperature']['now'], data['observation']['windSpeed'])) + TEMPUNIT)
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
            set_property('Hourly.%i.Temperature'     % (count + 1), YTEMP(item['temperature']['now']) + TEMPUNIT)
            set_property('Hourly.%i.FeelsLike'       % (count + 1), YTEMP(item['temperature']['feelsLike']) + TEMPUNIT)
            set_property('Hourly.%i.Outlook'         % (count + 1), str(item['conditionDescription']))
            set_property('Hourly.%i.OutlookIcon'     % (count + 1), '%s.png' % str(item['conditionCode']))
            set_property('Hourly.%i.FanartCode'      % (count + 1), str(item['conditionCode']))
            set_property('Hourly.%i.Humidity'        % (count + 1), str(item['humidity']) + '%')
            set_property('Hourly.%i.Precipitation'   % (count + 1), str(item['precipitationProbability']) + '%')
            set_property('Hourly.%i.WindDirection'   % (count + 1), xbmc.getLocalizedString(WIND_DIR(item['windDirection'])))
            set_property('Hourly.%i.WindSpeed'       % (count + 1), YSPEED(item['windSpeed']) + SPEEDUNIT)
            set_property('Hourly.%i.WindDegree'      % (count + 1), str(item['windDirection']) + u'°')
            set_property('Hourly.%i.DewPoint'        % (count + 1), YTEMP(dewpoint(int(convert_temp(item['temperature']['now'])), item['humidity']), 'C') + TEMPUNIT)
    
    def daily_properties(self, response, loc, locid):
        data = response['weathers'][0]
    #daily - standard (yahoo)
        for count, item in enumerate(data['forecasts']['daily']):
            set_property('Day%i.Title'           % count, xbmc.getLocalizedString(WEEK_DAY_LONG[str(item['observationTime']['weekday'])]))
            set_property('Day%i.HighTemp'        % count, convert_temp(item['temperature']['high']))
            set_property('Day%i.LowTemp'         % count, convert_temp(item['temperature']['low']))
            set_property('Day%i.Outlook'         % count, item['conditionDescription'])
            set_property('Day%i.OutlookIcon'     % count, '%s.png' % str(item['conditionCode']))
            set_property('Day%i.FanartCode'      % count, str(item['conditionCode']))
            if count == MAXDAYS:
                break
    #daily - extended (yahoo)
        for count, item in enumerate(data['forecasts']['daily']):
            set_property('Daily.%i.ShortDay'        % (count + 1), xbmc.getLocalizedString(WEEK_DAY_SHORT[str(item['observationTime']['weekday'])]))
            set_property('Daily.%i.LongDay'         % (count + 1), xbmc.getLocalizedString(WEEK_DAY_LONG[str(item['observationTime']['weekday'])]))
            set_property('Daily.%i.ShortDate'       % (count + 1), get_date(item['observationTime']['timestamp'], 'short'))
            set_property('Daily.%i.LongDate'        % (count + 1), get_date(item['observationTime']['timestamp'], 'short'))
            set_property('Daily.%i.HighTemperature' % (count + 1), YTEMP(item['temperature']['high']) + TEMPUNIT)
            set_property('Daily.%i.LowTemperature'  % (count + 1), YTEMP(item['temperature']['low']) + TEMPUNIT)
            set_property('Daily.%i.Outlook'         % (count + 1), str(item['conditionDescription']))
            set_property('Daily.%i.OutlookIcon'     % (count + 1), '%s.png' % str(item['conditionCode']))
            set_property('Daily.%i.FanartCode'      % (count + 1), str(item['conditionCode']))
            set_property('Daily.%i.Humidity'        % (count + 1), str(item['humidity']) + '%')
            set_property('Daily.%i.Precipitation'   % (count + 1), str(item['precipitationProbability']) + '%')
            set_property('Daily.%i.DewPoint'        % (count + 1), YTEMP(dewpoint(int(convert_temp(item['temperature']['low'])), item['humidity']), 'C') + TEMPUNIT)
    
    def add_props(self, data):
    #daily - standard (weatherbit)
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
    #daily - extended (weatherbit)
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
                if item['precip']:
                    set_property('Daily.%i.Precipitation' % (count+1), str(round(item['precip'] * 0.04 ,2)) + ' in')
                else:
                    set_property('Daily.%i.Precipitation' % (count+1), '')
                set_property('Daily.%i.Visibility'    % (count+1), str(round(item['vis'] * 0.621371 ,2)) + ' mi')
            else:
                set_property('Daily.%i.Pressure'      % (count+1), str(item['pres']) + ' mb')
                set_property('Daily.%i.SeaLevel'      % (count+1), str(round(item['slp'])) + ' mb')
                set_property('Daily.%i.Snow'          % (count+1), str(round(item['snow'])) + ' mm')
                set_property('Daily.%i.SnowDepth'     % (count+1), str(round(item['snow_depth'])) + ' mm')
                if item['precip']:
                    set_property('Daily.%i.Precipitation' % (count+1), str(round(item['precip'])) + ' mm')
                else:
                    set_property('Daily.%i.Precipitation' % (count+1), '')
                set_property('Daily.%i.Visibility'    % (count+1), str(item['vis']) + ' km')
            set_property('Daily.%i.WindSpeed'         % (count+1), SPEED(item['wind_spd']) + SPEEDUNIT)
            set_property('Daily.%i.WindGust'          % (count+1), SPEED(item['wind_gust_spd']) + SPEEDUNIT)
            set_property('Daily.%i.Cloudiness'        % (count+1), str(item['clouds']) + '%')
            set_property('Daily.%i.CloudsLow'         % (count+1), str(item['clouds_low']) + '%')
            set_property('Daily.%i.CloudsMid'         % (count+1), str(item['clouds_mid']) + '%')
            set_property('Daily.%i.CloudsHigh'        % (count+1), str(item['clouds_hi']) + '%')
            set_property('Daily.%i.Probability'       % (count+1), str(item['pop']) + '%')
            if item['uv']:
                set_property('Daily.%i.UVIndex'       % (count+1), str(int(round(item['uv']))) + '%')
            else:
                set_property('Daily.%i.UVIndex'       % (count+1), '')
            set_property('Daily.%i.Sunrise'           % (count+1), convert_date(item['sunrise_ts']))
            set_property('Daily.%i.Sunset'            % (count+1), convert_date(item['sunset_ts']))
            set_property('Daily.%i.Moonrise'          % (count+1), convert_date(item['moonrise_ts']))
            set_property('Daily.%i.Moonset'           % (count+1), convert_date(item['moonset_ts']))
            set_property('Daily.%i.MoonPhase'         % (count+1), str(item['moon_phase']))
            set_property('Daily.%i.Ozone'             % (count+1), str(int(round(item['ozone']))) + ' DU')

class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
