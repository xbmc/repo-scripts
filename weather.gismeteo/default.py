# -*- coding: utf-8 -*-
# Module: default
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from builtins import str
from builtins import range
import os
import time

import xbmc
import xbmcgui

from resources.lib.gismeteo import Gismeteo
from resources.lib.utilities import *
from resources.lib.simpleweather import *

weather = Weather()

_ = weather.initialize_gettext()

MAX_DAYS      = 7
MAX_DAILYS    = 7
MAX_LOCATIONS = 5
MAX_HOURLY    = 16
MAX_36HOUR    = 3
MAX_WEEKENDS  = 2

DATEFORMAT     = weather.date_format
TIMEFORMAT     = weather.time_format

WEATHER_ICON   = weather.weather_icon

KODILANGUAGE   = xbmc.getLanguage().lower()

CURRENT_TIME = {'unix': time.time()}

CACHE_DIR = os.path.join(weather.profile_dir, 'cache')

class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)

def get_lang():
    lang_id = weather.get_setting('Language')
    if lang_id == 0: #System interface
        lang = LANG[KODILANGUAGE] if LANG[KODILANGUAGE] is not '' else 'en'
    elif lang_id == 1:
        lang = 'ru'
    elif lang_id == 2:
        lang = 'ua'
    elif lang_id == 3:
        lang = 'lt'
    elif lang_id == 4:
        lang = 'lv'
    elif lang_id == 5:
        lang = 'en'
    elif lang_id == 6:
        lang = 'ro'
    elif lang_id == 7:
        lang = 'de'
    elif lang_id == 8:
        lang = 'pl'

    return lang

def is_weekend(day):
    return (get_weekday(day['date'], 'x') in WEEKENDS)

def get_weekends():
    weekend = weather.get_setting('Weekend')

    if weekend == 2:
        weekends = [4,5]
    elif weekend == 1:
        weekends = [5,6]
    else:
        weekends = [6,0]

    return weekends

def get_timestamp(date):
    if weather.get_setting('TimeZone') == 0:
        stamp = time.localtime(date['unix'])
    else:
        stamp = time.gmtime(date['unix'] + date['offset'] * 60)

    return stamp

def get_location_name(location):
    if location['kind'] == 'A':
        location_name = u'{0} {1}'.format(_('a/p'), location['name'])
    else:
        location_name = location['name']
    return location_name

def get_time(date):
    date_time = get_timestamp(date)

    if TIMEFORMAT != '/':
        local_time = time.strftime('%I:%M%p', date_time)
    else:
        local_time = time.strftime('%H:%M', date_time)
    return local_time

def convert_date(date):
    date_time = get_timestamp(date)

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

def get_weekday(date, form):
    date_time = get_timestamp(date)

    weekday = time.strftime('%w', date_time)
    if form == 's':
        return xbmc.getLocalizedString(WEEK_DAY_SHORT[weekday])
    elif form == 'l':
        return xbmc.getLocalizedString(WEEK_DAY_LONG[weekday])
    else:
        return int(weekday)

def get_month(date, form):
    date_time = get_timestamp(date)

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

def get_wind_direction(value):
    if WIND_DIRECTIONS.get(value) is not None:
        return xbmc.getLocalizedString(WIND_DIRECTIONS.get(value))
    elif value == '0':
        return _('calm')
    else:
        return _('n/a')

def get_weather_code(item):

    weather_code = WEATHER_CODES.get(item['icon'], 'na')
    return weather_code

def get_struct(struct_type):

    if struct_type == 'current':
        struct = { # standart properties
                  'Location':      '',
                  'Condition':     '',
                  'Temperature':   '',
                  'Wind':          '',
                  'WindDirection': '',
                  'Humidity':      '',
                  'FeelsLike':     '',
                  'DewPoint':      '',
                  'OutlookIcon':   '',
                  'FanartCode':    '',

                   # extenden properties
                  'Pressure':        '',
                  'Precipitation':   '',
                  }

    elif struct_type == 'today':
        struct= { # extended properties
                 'Sunrise': '',
                 'Sunset':  '',
                 }

    elif struct_type == 'day':
        struct = { # standart properties
                  'Title': '',
                  'HighTemp': '',
                  'LowTemp': '',
                  'Outlook': '',
                  'OutlookIcon': '',
                  'FanartCode':  '',
                  }

    elif struct_type == 'daily':

        struct = { # extenden properties
                  'LongDay':            '',
                  'ShortDay':           '',
                  'LongDate':           '',
                  'ShortDate':          '',
                  'Outlook':            '',
                  'OutlookIcon':        '',
                  'FanartCode':         '',
                  'WindSpeed':          '',
                  'MaxWind':            '',
                  'WindDirection':      '',
                  'Humidity':           '',
                  'MinHumidity':        '',
                  'MaxHumidity':        '',
                  'HighTemperature':    '',
                  'LowTemperature':     '',
                  'DewPoint':           '',
                  'TempMorn':           '',
                  'TempDay':            '',
                  'TempEve':            '',
                  'TempNight':          '',
                  'Pressure':           '',
                  'Precipitation':      '',
                  }

    elif struct_type == 'hourly':
        struct = { # extenden properties
                  'Time':             '',
                  'LongDate':         '',
                  'ShortDate':        '',
                  'Outlook':          '',
                  'OutlookIcon':      '',
                  'FanartCode':       '',
                  'WindSpeed':        '',
                  'WindDirection':    '',
                  'Humidity':         '',
                  'Temperature':      '',
                  'DewPoint':         '',
                  'FeelsLike':        '',
                  'Pressure':         '',
                  'Precipitation':    '',
                  }

    elif struct_type == '36hour':
        struct = { # extenden properties
                  'Heading':            '',
                  'TemperatureHeading': '',
                  'LongDay':            '',
                  'ShortDay':           '',
                  'LongDate':           '',
                  'ShortDate':          '',
                  'Outlook':            '',
                  'OutlookIcon':        '',
                  'FanartCode':         '',
                  'WindSpeed':          '',
                  'WindDirection':      '',
                  'Humidity':           '',
                  'Temperature':        '',
                  'DewPoint':           '',
                  'FeelsLike':          '',
                  'Pressure':           '',
                  'Precipitation':      '',
                  }

    return struct

def set_item_info(props, item, item_type, icon='%s.png', day_temp=None):
    keys = list(props.keys())

    # Date
    date = item['date']

    if 'Title' in keys:
        props['Title'] = get_weekday(date, 'l')

    if 'Time' in keys:
        props['Time'] = get_time(date)

    if 'LongDay' in keys:
        props['LongDay'] = get_weekday(date, 'l')

    if 'ShortDay' in keys:
        props['ShortDay'] = get_weekday(date, 's')

    if 'LongDate' in keys:
        form = 'dl' if (DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D') else 'ml'
        props['LongDate'] = get_month(date, form)

    if 'ShortDate' in keys:
        form = 'ds' if (DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D') else 'ms'
        props['ShortDate'] = get_month(date, form)


    # Outlook
    weather_code = get_weather_code(item)

    if 'Outlook' in keys:
        props['Outlook'] = item['description']

    if 'Condition' in keys:
        props['Condition'] = item['description']

    if 'OutlookIcon' in keys:
        props['OutlookIcon'] = icon % weather_code

    if 'FanartCode' in keys:
        props['FanartCode']  = weather_code


    # Wind

    wind = item['wind']

    speed = 0
    if isinstance(wind['speed'], dict):
        speed = wind['speed']['avg']
    elif isinstance(wind['speed'], float):
        speed = wind['speed']

    if 'Wind' in keys:
        props['Wind'] = int(round(speed * 3.6))

    if 'WindSpeed' in keys:
        props['WindSpeed'] = u'{0} {1}'.format(SPEED(speed), _(SPEEDUNIT))

    if 'WindDirection' in keys:
        props['WindDirection'] = get_wind_direction(wind['direction'])

    if 'MaxWind' in keys:
        props['MaxWind'] = u'{0} {1}'.format(SPEED(wind['speed']['max']), _(SPEEDUNIT))


    # Temperature

    if 'DewPoint' in keys and item_type == 'day':
        props['DewPoint'] = DEW_POINT(item['temperature']['max'], item['humidity']['avg']) + TEMPUNIT
    elif 'DewPoint' in keys and item_type == 'hour':
        props['DewPoint'] = DEW_POINT(item['temperature']['air'], item['humidity']) + TEMPUNIT
    elif 'DewPoint' in keys and item_type == 'cur':
        props['DewPoint'] = DEW_POINT(item['temperature']['air'], item['humidity'], False)

    if 'HighTemp' in keys:
        props['HighTemp'] = str(item['temperature']['max'])

    if 'LowTemp' in keys:
        props['LowTemp'] = str(item['temperature']['min'])

    if 'HighTemperature' in keys:
        props['HighTemperature'] = TEMP(item['temperature']['max']) + TEMPUNIT

    if 'HighTemperature' in keys:
        props['LowTemperature'] = TEMP(item['temperature']['min']) + TEMPUNIT

    if 'Temperature' in keys and item_type == 'cur':
        props['Temperature'] = item['temperature']['air']
    elif 'Temperature' in keys:
        props['Temperature'] = TEMP(item['temperature']['air']) + TEMPUNIT

    if 'FeelsLike' in keys and item_type == 'cur':
        props['FeelsLike'] = item['temperature']['comfort']
    elif 'FeelsLike' in keys:
        props['FeelsLike'] = TEMP(item['temperature']['comfort']) + TEMPUNIT

    if day_temp is not None:
        if 'TempMorn' in keys:
            props['TempMorn'] = TEMP(day_temp['morn']) + TEMPUNIT
        if 'TempDay' in keys:
            props['TempDay'] = TEMP(day_temp['day']) + TEMPUNIT
        if 'TempEve' in keys:
            props['TempEve'] = TEMP(day_temp['eve']) + TEMPUNIT
        if 'TempNight' in keys:
            props['TempNight'] = TEMP(day_temp['night']) + TEMPUNIT


    # Humidity

    if 'Humidity' in keys:
        humidity =  item['humidity']['avg'] if item_type == 'day' else item['humidity']
        tpl = u'{0}%' if item_type != 'cur' else u'{0}'
        props['Humidity'] = tpl.format(humidity) if humidity is not None else _('n/a')

    if 'MinHumidity' in keys and item_type == 'day':
        humidity =  item['humidity']['min']
        props['MinHumidity'] = u'{0}%'.format(humidity) if humidity is not None else _('n/a')

    if 'MaxHumidity' in keys and item_type == 'day':
        humidity =  item['humidity']['max']
        props['MaxHumidity'] = u'{0}%'.format(humidity) if humidity is not None else _('n/a')


    # Pressure

    if 'Pressure' in keys:
        pressure =  item['pressure']['avg'] if item_type == 'day' else item['pressure']
        props['Pressure'] = u'{0} {1}'.format(PRESSURE(pressure),  _(PRESUNIT)) if pressure is not None else _('n/a')

    # Precipitation

    if 'Precipitation' in keys:
        precip = item['precipitation']['amount']
        props['Precipitation'] = u'{0} {1}'.format(PRECIPITATION(precip), _(PRECIPUNIT)) if precip is not None else _('n/a')

def clear():

    # Current
    weather.set_properties(get_struct('current'), 'Current')

    # Today
    # extenden properties
    weather.set_property('Today.Sunset'  , '')
    weather.set_property('Today.Sunrise' , '')

    # Forecast
    # extenden properties
    weather.set_property('Forecast.City'      , '')
    weather.set_property('Forecast.Country'   , '')
    weather.set_property('Forecast.Latitude'  , '')
    weather.set_property('Forecast.Longitude' , '')
    weather.set_property('Forecast.Updated'   , '')

    # Day
    day_props = get_struct('day')
    for count in range (0, MAX_DAYS + 1):
        weather.set_properties(day_props, 'Day', count, '')

    # Daily
    daily_props = get_struct('daily')
    for count in range (1, MAX_DAILYS + 1):
        weather.set_properties(daily_props, 'Daily', count)

    # Hourly
    hourly_props = get_struct('hourly')
    for count in range (1, MAX_HOURLY + 1):
        weather.set_properties(hourly_props, 'Hourly', count)

    # Weekend
    for count in range (1, MAX_WEEKENDS + 1):
        weather.set_properties(daily_props, 'Weekend', count)

    # 36Hour
    _36hour_props = get_struct('36hour')
    for count in range (1, MAX_36HOUR + 1):
        weather.set_properties(_36hour_props, '36Hour', count)

def refresh_locations():
    locations = 0
    if weather.get_setting('CurrentLocation'):
        location = gismeteo.cities_ip()
        if location is not None:
            loc_name = location['name']
        else:
            loc_name = ''

        if loc_name != '':
            locations += 1
            weather.set_property('Location%s' % locations, loc_name)

    for count in range(1, MAX_LOCATIONS + 1):
        loc_name = weather.get_setting('Location%s' % count)
        loc_id = weather.get_setting('Location%sID' % count)
        if loc_name != '':
            locations += 1
            weather.set_property('Location%s' % locations, loc_name)
        elif loc_id != '':
            weather.set_setting('Location%sID' % count, '')

    weather.set_property('Locations', str(locations))

def set_location_props(forecast_info):
    count_days = 0
    count_hourly = 0
    count_36hour = 0
    count_weekends = 0

    # Current
    current_props = get_struct('current')
    set_item_info(current_props, forecast_info['current'], 'cur')

    current_props['Location'] = get_location_name(forecast_info)

    weather.set_properties(current_props, 'Current')

    # Forecast
    forecast_props = { # extended properties
                      'City':      forecast_info['name'],
                      'Country':   forecast_info['country'],
                      'State':     forecast_info['district'],
                      'Latitude':  forecast_info['lat'],
                      'Longitude': forecast_info['lng'],
                      'Updated':   convert_date(forecast_info['cur_time']),
                      }
    weather.set_properties(forecast_props, 'Forecast')

    # Today
    today_props = get_struct('today')
    if forecast_info['current']['sunrise']['unix'] != forecast_info['current']['sunset']['unix']:
        today_props['Sunrise'] = get_time(forecast_info['current']['sunrise'])
        today_props['Sunset'] = get_time(forecast_info['current']['sunset'])
    weather.set_properties(today_props, 'Today')

    for day in forecast_info['days']:
        day_temp = None
        if day.get('hourly') is not None:
            day_temp = {}

            for hour in day['hourly']:

                if hour['tod'] == 0:
                    day_temp['night'] = hour['temperature']['air']
                elif hour['tod'] == 1:
                    day_temp['morn'] = hour['temperature']['air']
                elif hour['tod'] == 2:
                    day_temp['day'] = hour['temperature']['air']
                elif hour['tod'] == 3:
                    day_temp['eve'] = hour['temperature']['air']

                # Hourly
                if count_hourly < MAX_HOURLY \
                  and hour['date']['unix'] >= CURRENT_TIME['unix']:
                    hourly_props = get_struct('hourly')
                    set_item_info(hourly_props, hour, 'hour', WEATHER_ICON)
                    weather.set_properties(hourly_props, 'Hourly', count_hourly + 1)

                    count_hourly += 1

                # 36Hour
                if count_36hour < MAX_36HOUR \
                  and hour['tod'] in [2, 3]:
                    if hour['tod'] == 2 \
                      and hour['date']['unix'] >= CURRENT_TIME['unix'] \
                      or hour['tod'] == 3:
                        _36hour_props = get_struct('36hour')
                        set_item_info(_36hour_props, hour, 'hour', WEATHER_ICON)

                        if hour['tod'] == 2:
                            _36hour_props['Heading']            = xbmc.getLocalizedString(33006 + count_days)
                            _36hour_props['TemperatureHeading'] = xbmc.getLocalizedString(393)
                        else:
                            _36hour_props['Heading']            = xbmc.getLocalizedString(33018 + count_days)
                            _36hour_props['TemperatureHeading'] = xbmc.getLocalizedString(391)

                        weather.set_properties(_36hour_props, '36Hour', count_36hour + 1)

                        count_36hour += 1

        # Day
        if count_days <= MAX_DAYS:
            day_props = get_struct('day')
            set_item_info(day_props, day, 'day')
            weather.set_properties(day_props, 'Day', count_days, '')

        # Daily
        if count_days <= MAX_DAILYS:
            daily_props = get_struct('daily')
            set_item_info(daily_props, day, 'day', WEATHER_ICON, day_temp)
            weather.set_properties(daily_props, 'Daily', count_days + 1)

        # Weekend
        if is_weekend(day) \
          and count_weekends <= MAX_WEEKENDS:
            weekend_props = get_struct('daily')
            set_item_info(weekend_props, day, 'day', WEATHER_ICON, day_temp)
            weather.set_properties(weekend_props, 'Weekend', count_weekends + 1)

            count_weekends += 1

        count_days += 1

    # Day
    day_props = get_struct('day')
    for count in range (count_days, MAX_DAYS + 1):
        weather.set_properties(day_props, 'Day', count, '')

    # Daily
    daily_props = get_struct('daily')
    for count in range (count_days + 1, MAX_DAILYS + 1):
        weather.set_properties(daily_props, 'Daily', count)

    # Hourly
    hourly_props = get_struct('hourly')
    for count in range (count_hourly + 1, MAX_HOURLY + 1):
        weather.set_properties(hourly_props, 'Hourly', count)

    # Weekend
    for count in range (count_weekends + 1, MAX_WEEKENDS + 1):
        weather.set_properties(daily_props, 'Weekend', count)

    # 36Hour
    _36hour_props = get_struct('36hour')
    for count in range (count_36hour + 1, MAX_36HOUR + 1):
        weather.set_properties(_36hour_props, '36Hour', count)

@weather.action('root')
def forecast(params):
    data = None

    location_name, location_id = get_location(params.id)
    if location_id != '':
        retry = 0
        while (retry < 10) and (not MONITOR.abortRequested()):
            data = gismeteo.forecast(location_id)
            if data is not None:
                retry = 10
            else:
                retry += 1
                xbmc.sleep(1000)

    if data is not None:
        set_location_props(data)
    else:
        clear()

    refresh_locations()

@weather.action()
def location(params):
    labels = []
    locations = []

    keyboard = xbmc.Keyboard('', xbmc.getLocalizedString(14024), False)
    keyboard.doModal()
    if (keyboard.isConfirmed() and keyboard.getText() != ''):
        text = py2_encode(keyboard.getText())
        dialog = xbmcgui.Dialog()

        search_result = gismeteo.cities_search(text)

        if search_result is not None:
            for location in search_result:
                location_name = get_location_name(location)

                if location['district']:
                    labels.append(u'{0} ({1}, {2})'.format(location_name, location['district'], location['country']))
                else:
                    labels.append(u'{0} ({1})'.format(location_name, location['country']))
                locations.append({'id':location['id'], 'name': location_name})

        if locations:
            selected = dialog.select(xbmc.getLocalizedString(396), labels)
            if selected != -1:
                selected_location = locations[selected]
                weather.set_setting('Location%s' % params.id, selected_location['name'])
                weather.set_setting('Location%sID' % params.id, selected_location['id'])
        else:
            dialog.ok(weather.name, xbmc.getLocalizedString(284))

@weather.action()
def clear_cache():

    if os.path.exists(CACHE_DIR):
        files = os.listdir(CACHE_DIR)
        for file_name in files:
            file_path = os.path.join(CACHE_DIR, file_name)
            os.remove(file_path)

def get_location(loc_id):
    if loc_id == '1' and weather.get_setting('CurrentLocation'):
        location = gismeteo.cities_ip()
        if location is not None:
            location_name = get_location_name(location)
            location_id = location['id']
        else:
            location_name = ''
            location_id = ''
    else:
        loc_id = loc_id if not weather.get_setting('CurrentLocation') else str((int(loc_id) - 1))
        location_name = weather.get_setting('Location%s' % loc_id, False)
        location_id = weather.get_setting('Location%sID' % loc_id, False)

        if (location_id == '') and (loc_id != '1'):
            location_name = weather.get_setting('Location1', False)
            location_id = weather.get_setting('Location1ID', False)

    return location_name, location_id

MONITOR = MyMonitor()

if __name__ == '__main__':

    WEEKENDS = get_weekends()

    weather.set_property('Forecast.IsFetched', 'true')
    weather.set_property('Current.IsFetched' , 'true')
    weather.set_property('Today.IsFetched'   , 'true')
    weather.set_property('Daily.IsFetched'   , 'true')
    weather.set_property('Weekend.IsFetched' , 'true')
    weather.set_property('36Hour.IsFetched'  , 'true')
    weather.set_property('Hourly.IsFetched'  , 'true')
    weather.set_property('Alerts.IsFetched'  , '')
    weather.set_property('Map.IsFetched'     , '')

    # WeatherProvider
    # standard properties
    weather.set_property('WeatherProvider'    , weather.name)
    weather.set_property('WeatherProviderLogo', py2_decode(xbmc.translatePath(os.path.join(weather.path, 'resources', 'media', 'banner.png'))))

    conf = {'lang': get_lang(),
            'cache_dir': CACHE_DIR,
            'cache_time': 30, # time in minutes
            }
    gismeteo = Gismeteo(conf)

    weather.run()
