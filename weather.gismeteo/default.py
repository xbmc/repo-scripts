# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals

from builtins import range
import os
import time

import xbmc

from resources.libs import Gismeteo, GismeteoError, Location, Weather, WebClientError

weather = Weather()
_ = weather.initialize_gettext()

MAX_DAYS = 7
MAX_DAILYS = 7
MAX_LOCATIONS = 5
MAX_HOURLY = 16
MAX_36HOUR = 3
MAX_WEEKENDS = 2

WEATHER_ICON = weather.weather_icon

CURRENT_TIME = {'unix': time.time()}


def set_item_info(props, item, item_type, icon='%s.png', day_temp=None):
    keys = list(props.keys())

    # Date
    date = item['date']

    if 'Title' in keys:
        props['Title'] = weather.get_weekday(date, 'l')

    if 'Time' in keys:
        props['Time'] = weather.get_time(date)

    if 'LongDay' in keys:
        props['LongDay'] = weather.get_weekday(date, 'l')

    if 'ShortDay' in keys:
        props['ShortDay'] = weather.get_weekday(date, 's')

    if 'LongDate' in keys:
        form = 'dl' if (weather.DATEFORMAT[1] == 'd' or weather.DATEFORMAT[0] == 'D') else 'ml'
        props['LongDate'] = weather.get_month(date, form)

    if 'ShortDate' in keys:
        form = 'ds' if (weather.DATEFORMAT[1] == 'd' or weather.DATEFORMAT[0] == 'D') else 'ms'
        props['ShortDate'] = weather.get_month(date, form)

    # Outlook
    weather_code = weather.get_weather_code(item)

    if 'Outlook' in keys:
        props['Outlook'] = item['description']

    if 'Condition' in keys:
        props['Condition'] = item['description']

    if 'OutlookIcon' in keys:
        props['OutlookIcon'] = icon % weather_code

    if 'FanartCode' in keys:
        props['FanartCode'] = weather_code

    if 'ProviderIcon' in keys\
        and weather.use_provider_icon:
        props['ProviderIcon'] = 'resource://resource.images.weatherprovidericons.gismeteo/{0}.png'.format(item['icon'])

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
        props['WindSpeed'] = '{0} {1}'.format(weather.SPEED(speed), _(weather.SPEEDUNIT))

    if 'WindDirection' in keys:
        props['WindDirection'] = weather.get_wind_direction(wind['direction'])

    if 'MaxWind' in keys:
        props['MaxWind'] = '{0} {1}'.format(weather.SPEED(wind['speed']['max']), _(weather.SPEEDUNIT))

    # Temperature

    if 'DewPoint' in keys and item_type == 'day':
        props['DewPoint'] = weather.DEW_POINT(item['temperature']['max'], item['humidity']['avg']) + weather.TEMPUNIT
    elif 'DewPoint' in keys and item_type == 'hour':
        props['DewPoint'] = weather.DEW_POINT(item['temperature']['air'], item['humidity']) + weather.TEMPUNIT
    elif 'DewPoint' in keys and item_type == 'cur':
        props['DewPoint'] = weather.DEW_POINT(item['temperature']['air'], item['humidity'], False)

    if 'HighTemp' in keys:
        props['HighTemp'] = '{0}'.format(item['temperature']['max'])

    if 'LowTemp' in keys:
        props['LowTemp'] = '{0}'.format(item['temperature']['min'])

    if 'HighTemperature' in keys:
        props['HighTemperature'] = weather.TEMP(item['temperature']['max']) + weather.TEMPUNIT

    if 'HighTemperature' in keys:
        props['LowTemperature'] = weather.TEMP(item['temperature']['min']) + weather.TEMPUNIT

    if 'Temperature' in keys and item_type == 'cur':
        props['Temperature'] = item['temperature']['air']
    elif 'Temperature' in keys:
        props['Temperature'] = weather.TEMP(item['temperature']['air']) + weather.TEMPUNIT

    if 'FeelsLike' in keys and item_type == 'cur':
        props['FeelsLike'] = item['temperature']['comfort']
    elif 'FeelsLike' in keys:
        props['FeelsLike'] = weather.TEMP(item['temperature']['comfort']) + weather.TEMPUNIT

    if day_temp is not None:
        if 'TempMorn' in keys:
            props['TempMorn'] = weather.TEMP(day_temp['morn']) + weather.TEMPUNIT
        if 'TempDay' in keys:
            props['TempDay'] = weather.TEMP(day_temp['day']) + weather.TEMPUNIT
        if 'TempEve' in keys:
            props['TempEve'] = weather.TEMP(day_temp['eve']) + weather.TEMPUNIT
        if 'TempNight' in keys:
            props['TempNight'] = weather.TEMP(day_temp['night']) + weather.TEMPUNIT

    # Humidity

    if 'Humidity' in keys:
        humidity = item['humidity']['avg'] if item_type == 'day' else item['humidity']
        tpl = '{0}%' if item_type != 'cur' else '{0}'
        props['Humidity'] = tpl.format(humidity) if humidity is not None else _('n/a')

    if 'MinHumidity' in keys and item_type == 'day':
        humidity = item['humidity']['min']
        props['MinHumidity'] = '{0}%'.format(humidity) if humidity is not None else _('n/a')

    if 'MaxHumidity' in keys and item_type == 'day':
        humidity = item['humidity']['max']
        props['MaxHumidity'] = '{0}%'.format(humidity) if humidity is not None else _('n/a')

    # Pressure

    if 'Pressure' in keys:
        pressure = item['pressure']['avg'] if item_type == 'day' else item['pressure']
        props['Pressure'] = '{0} {1}'.format(weather.PRESSURE(pressure), _(weather.PRESUNIT)) if pressure is not None else _('n/a')

    # Precipitation

    if 'Precipitation' in keys:
        precip = item['precipitation']['amount']
        props['Precipitation'] = '{0} {1}'.format(weather.PRECIPITATION(precip), _(weather.PRECIPUNIT)) if precip is not None else _('n/a')


def clear():

    # Current
    weather.set_properties(weather.prop_current(), 'Current')

    # Today
    weather.set_properties(weather.prop_today(), 'Today')

    # Forecast
    weather.set_properties(weather.prop_forecast(), 'Forecast')

    # Day
    day_props = weather.prop_day()
    for count in range(0, MAX_DAYS + 1):
        weather.set_properties(day_props, 'Day', count, '')

    # Daily
    daily_props = weather.prop_daily()
    for count in range(1, MAX_DAILYS + 1):
        weather.set_properties(daily_props, 'Daily', count)

    # Hourly
    hourly_props = weather.prop_hourly()
    for count in range(1, MAX_HOURLY + 1):
        weather.set_properties(hourly_props, 'Hourly', count)

    # Weekend
    for count in range(1, MAX_WEEKENDS + 1):
        weather.set_properties(daily_props, 'Weekend', count)

    # 36Hour
    _36hour_props = weather.prop_36hour()
    for count in range(1, MAX_36HOUR + 1):
        weather.set_properties(_36hour_props, '36Hour', count)


def refresh_locations():
    locations = 0
    if weather.get_setting('CurrentLocation'):
        try:
            lang = weather.gismeteo_lang()
            ip_locations = _ip_locations(lang)
        except (GismeteoError, WebClientError) as e:
            weather.notify_error(e)
            location = Location()
        else:
            for ip_location in ip_locations:
                location = Location(ip_location)
                break

        locations += 1
        weather.set_property('Location{0}'.format(locations), location.name)

    for count in range(1, MAX_LOCATIONS + 1):
        loc_name = weather.get_setting('Location{0}'.format(count))
        if loc_name:
            locations += 1
            weather.set_property('Location{0}'.format(locations), loc_name)

        elif not weather.get_setting('Location{0}ID'.format(count)):
            weather.set_setting('Location{0}ID'.format(count), '')

    weather.set_property('Locations', locations)


def set_location_props(forecast_info):
    count_days = 0
    count_hourly = 0
    count_36hour = 0
    count_weekends = 0

    # Current
    current_props = weather.prop_current()
    set_item_info(current_props, forecast_info['current'], 'cur')

    location_info = Location(forecast_info)
    current_props['Location'] = location_info.name

    weather.set_properties(current_props, 'Current')

    # Forecast
    forecast_props = weather.prop_forecast()
    forecast_props['City'] = forecast_info['name']
    forecast_props['Country'] = forecast_info['country']
    forecast_props['State'] = forecast_info['district']
    forecast_props['Latitude'] = forecast_info['lat']
    forecast_props['Longitude'] = forecast_info['lng']
    forecast_props['Updated'] = weather.convert_date(forecast_info['cur_time'])

    weather.set_properties(forecast_props, 'Forecast')

    # Today
    today_props = weather.prop_today()
    if forecast_info['current']['sunrise']['unix'] != forecast_info['current']['sunset']['unix']:
        today_props['Sunrise'] = weather.get_time(forecast_info['current']['sunrise'])
        today_props['Sunset'] = weather.get_time(forecast_info['current']['sunset'])
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
                    hourly_props = weather.prop_hourly()
                    set_item_info(hourly_props, hour, 'hour', WEATHER_ICON)
                    weather.set_properties(hourly_props, 'Hourly', count_hourly + 1)

                    count_hourly += 1

                # 36Hour
                if count_36hour < MAX_36HOUR \
                  and hour['tod'] in [2, 3]:
                    if hour['tod'] == 2 \
                      and hour['date']['unix'] >= CURRENT_TIME['unix'] \
                      or hour['tod'] == 3:
                        _36hour_props = weather.prop_36hour()
                        set_item_info(_36hour_props, hour, 'hour', WEATHER_ICON)

                        if hour['tod'] == 2:
                            _36hour_props['Heading'] = xbmc.getLocalizedString(33006 + count_days)
                            _36hour_props['TemperatureHeading'] = xbmc.getLocalizedString(393)
                        else:
                            _36hour_props['Heading'] = xbmc.getLocalizedString(33018 + count_days)
                            _36hour_props['TemperatureHeading'] = xbmc.getLocalizedString(391)

                        weather.set_properties(_36hour_props, '36Hour', count_36hour + 1)

                        count_36hour += 1

        # Day
        if count_days <= MAX_DAYS:
            day_props = weather.prop_day()
            set_item_info(day_props, day, 'day')
            weather.set_properties(day_props, 'Day', count_days, '')

        # Daily
        if count_days <= MAX_DAILYS:
            daily_props = weather.prop_daily()
            set_item_info(daily_props, day, 'day', WEATHER_ICON, day_temp)
            weather.set_properties(daily_props, 'Daily', count_days + 1)

        # Weekend
        if weather.is_weekend(day) \
          and count_weekends <= MAX_WEEKENDS:
            weekend_props = weather.prop_daily()
            set_item_info(weekend_props, day, 'day', WEATHER_ICON, day_temp)
            weather.set_properties(weekend_props, 'Weekend', count_weekends + 1)

            count_weekends += 1

        count_days += 1

    # Day
    day_props = weather.prop_day()
    for count in range(count_days, MAX_DAYS + 1):
        weather.set_properties(day_props, 'Day', count, '')

    # Daily
    daily_props = weather.prop_daily()
    for count in range(count_days + 1, MAX_DAILYS + 1):
        weather.set_properties(daily_props, 'Daily', count)

    # Hourly
    hourly_props = weather.prop_hourly()
    for count in range(count_hourly + 1, MAX_HOURLY + 1):
        weather.set_properties(hourly_props, 'Hourly', count)

    # Weekend
    for count in range(count_weekends + 1, MAX_WEEKENDS + 1):
        weather.set_properties(daily_props, 'Weekend', count)

    # 36Hour
    _36hour_props = weather.prop_36hour()
    for count in range(count_36hour + 1, MAX_36HOUR + 1):
        weather.set_properties(_36hour_props, '36Hour', count)


@weather.action('root')
def forecast(params):

    location = get_location(params.id)
    if location.id:
        try:
            lang = weather.gismeteo_lang()
            data = _location_forecast(lang, location.id)
        except (GismeteoError, WebClientError) as e:
            weather.notify_error(e)
            clear()
        else:
            set_location_props(data)

    refresh_locations()


@weather.action()
def location(params):
    labels = []
    locations = []

    keyword = weather.get_keyboard_text('', xbmc.getLocalizedString(14024), False)
    if keyword:

        try:
            lang = weather.gismeteo_lang()
            search_result = Gismeteo(lang).cities_search(keyword)
        except (GismeteoError, WebClientError) as e:
            weather.notify_error(e, True)
        else:
            for s_location in search_result:
                location = Location(s_location)

                item = {'id': location.id,
                        'name': location.name,
                        }
                locations.append(item)
                labels.append(location.label)

            if locations:
                selected = weather.dialog_select(xbmc.getLocalizedString(396), labels)
                if selected != -1:
                    selected_location = locations[selected]
                    weather.set_setting('Location{0}'.format(params.id), selected_location['name'])
                    weather.set_setting('Location{0}ID'.format(params.id), selected_location['id'])
            else:
                weather.dialog_ok(weather.name, xbmc.getLocalizedString(284))


@weather.mem_cached(30)
def _location_forecast(lang, _id):

    gismeteo = Gismeteo(lang)

    params = {'city_id': _id,
              }

    return _call_method(gismeteo.forecast, params)



@weather.mem_cached(10)
def _ip_locations(lang):

    gismeteo = Gismeteo(lang)

    return _call_method(gismeteo.cities_ip)

def get_location(loc_id):

    use_current_location = weather.get_setting('CurrentLocation')

    if loc_id == '1' \
      and use_current_location:
        try:
            lang = weather.gismeteo_lang()
            ip_locations = _ip_locations(lang)
        except (GismeteoError, WebClientError) as e:
            weather.notify_error(e)
        else:
            for ip_location in ip_locations:
                return Location(ip_location)
    else:
        int_loc_id = int(loc_id)

        if use_current_location:
            int_loc_id -= 1

        location_id = weather.get_setting('Location{0}ID'.format(int_loc_id))

        if not location_id \
           and int_loc_id != 1:
            int_loc_id = 1

            location_id = weather.get_setting('Location{0}ID'.format(int_loc_id))

        location_name = weather.get_setting('Location{0}'.format(int_loc_id))

        data = {'name': location_name,
                'id': location_id,
                }

        return Location(data)

    return Location()


def _call_method(func, params=None):
    params = params or {}

    retry = 0
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        try:
            return func(**params)
        except (GismeteoError, WebClientError, ImportError) as e:
            if retry >= 10:
                raise e
        finally:
            retry += 1
            monitor.waitForAbort(1)


if __name__ == '__main__':

    description = weather.prop_description()

    description['Forecast.IsFetched'] = 'true'
    description['Current.IsFetched'] = 'true'
    description['Today.IsFetched'] = 'true'
    description['Daily.IsFetched'] = 'true'
    description['Weekend.IsFetched'] = 'true'
    description['36Hour.IsFetched'] = 'true'
    description['Hourly.IsFetched'] = 'true'

    description['WeatherProvider'] = weather.name
    description['WeatherProviderLogo'] = xbmc.translatePath(os.path.join(weather.path, 'resources', 'media', 'banner.png'))

    weather.set_properties(description)

    weather.run()
