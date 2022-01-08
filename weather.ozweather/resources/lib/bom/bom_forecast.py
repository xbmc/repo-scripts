# -*- coding: utf-8 -*-
import datetime
import pytz
import sys
import requests
import math
import xbmc

# Small hack to allow for unit testing - see common.py for explanation
if not xbmc.getUserAgent():
    sys.path.insert(0, '../../..')

from resources.lib.store import Store
from resources.lib.common import *

"""
(See bottom of this file for BOM API output examples!)
"""


# This is a hack fix for a wicked long standing Python bug...
# See: https://forum.kodi.tv/showthread.php?tid=112916
class ProxyDatetime(datetime.datetime):
    @staticmethod
    def strptime(date_string, format):
        import time
        return datetime.datetime(*(time.strptime(date_string, format)[0:6]))


datetime.datetime = ProxyDatetime


def set_key(weather_data, index, key, value):
    """
    Set a key - for old and new weather label support
    """

    if value == "":
        return

    value = str(value)

    if index == 0:
        weather_data['Current.' + key] = value.strip()
        weather_data['Current.' + key] = value.strip()

    weather_data['Day' + str(index) + '.' + key] = value.strip()
    weather_data['Day' + str(index) + '.' + key] = value.strip()
    weather_data['Daily.' + str(index + 1) + '.' + key] = value.strip()
    weather_data['Daily.' + str(index + 1) + '.' + key] = value.strip()


def set_keys(weather_data, index, keys, value):
    """
    Set a group of keys at once - for old and new weather label support
    """
    if value == "":
        return

    for key in keys:
        set_key(weather_data, index, key, value)


def utc_str_to_local_datetime(utc_str: str, utc_format: str = '%Y-%m-%dT%H:%M:%SZ', time_zone=None):
    """
    Given a UTC string, return a datetime in the local timezone

    :param utc_str: UTC time string
    :param utc_format: format of UTC time string
    :param time_zone:  specific timezone to convert to, if not the local timezone
    :return: local time string
    """

    temp1 = datetime.datetime.strptime(utc_str, utc_format)
    temp2 = temp1.replace(tzinfo=datetime.timezone.utc)
    return temp2.astimezone(time_zone)


def utc_str_to_local_str(utc_str: str, utc_format: str = '%Y-%m-%dT%H:%M:%SZ', local_format: str = '%I:%M%p', time_zone=None):
    """
    Given a UTC string, return a string with the local time in the given format

    :param utc_str: UTC time string
    :param utc_format: format of UTC time string
    :param local_format: format of local time string
    :param time_zone: specific timezone to convert to, if not the local timezone
    :return: local time string
    """

    local_time = utc_str_to_local_datetime(utc_str, utc_format, time_zone)
    return local_time.strftime(local_format).lstrip('0').lower()


def bom_forecast(geohash):
    """
    Return are information, current observations, warnings, and forecast for the given geohash
    If we're unable to get the key data (current observations and forecast) then return False

    :param: geohash - the BOM location geohash
    """

    # Gather the weather data into a dict from which we will later set all the Kodi labels
    weather_data = {}



    # The areahash is the geohash minus the last character
    areahash = geohash[:-1]

    bom_api_url_geohash = f'{Store.BOM_API_LOCATIONS_URL}/{geohash}'
    bom_api_url_areahash = f'{Store.BOM_API_LOCATIONS_URL}/{areahash}'

    bom_api_area_information_url = bom_api_url_geohash
    bom_api_warnings_url = f'{bom_api_url_geohash}/warnings'

    bom_api_current_observations_url = f'{bom_api_url_areahash}/observations'
    bom_api_forecast_seven_days_url = f'{bom_api_url_areahash}/forecasts/daily'
    # FUTURE? - these API end points exist, but are not yet used by OzWeather
    bom_api_forecast_three_hourly_url = f'{bom_api_url_areahash}/forecasts/3-hourly'
    bom_api_forecast_rain = f'{bom_api_url_areahash}/forecast/rain'

    # Holders for the BOM JSON API results...
    area_information = None
    current_observations = None
    warnings = None
    forecast_seven_days = None
    # forecast_three_hourly = None
    # forecast_rain = None

    # Get the AREA INFORMATION, including the location's timezone so we can correctly show the location local times
    location_timezone = ""
    # In case we can't get the localised now time, below...
    now = datetime.datetime.now()

    try:
        r = requests.get(bom_api_area_information_url)
        area_information = r.json()["data"]
        log(area_information)
        if area_information:
            location_timezone_text = area_information['timezone']
            log(f"Location timezone from BOM is {location_timezone_text}")
            location_timezone = pytz.timezone(location_timezone_text)
            # For any date comparisons - this is the localised now...
            now = datetime.datetime.now(location_timezone)

    except Exception as inst:
        log(f'Error retrieving area information from {bom_api_area_information_url}')

    # Get CURRENT OBSERVATIONS
    try:
        r = requests.get(bom_api_current_observations_url)
        current_observations = r.json()["data"]
        weather_data['ObservationsUpdated'] = utc_str_to_local_str(r.json()["metadata"]["issue_time"], time_zone=location_timezone)
        weather_data['ObservationsStation'] = r.json()["data"]['station']['name']
        log(current_observations)

    except Exception as inst:
        log(f'Error retrieving current observations from {bom_api_current_observations_url}')
        return False

    # Get WARNINGS
    try:
        r = requests.get(bom_api_warnings_url)
        warnings = r.json()["data"]
        log(warnings)

    except Exception as inst:
        log(f'Error retrieving warnings from {bom_api_warnings_url}')

    # Get 7 DAY FORECAST
    try:
        r = requests.get(bom_api_forecast_seven_days_url)
        forecast_seven_days = r.json()["data"]
        weather_data['ForecastUpdated'] = utc_str_to_local_str(r.json()["metadata"]["issue_time"], time_zone=location_timezone)
        weather_data['ForecastRegion'] = r.json()["metadata"]["forecast_region"].title()
        weather_data['ForecastType'] = r.json()["metadata"]["forecast_type"].title()
        log(forecast_seven_days)

    except Exception as inst:
        log(f'Error retrieving seven day forecast from {bom_api_forecast_seven_days_url}')
        return False

    # FUTURE?
    # # Get 3 HOURLY FORECAST
    # try:
    #     r = requests.get(bom_api_forecast_three_hourly_url)
    #     forecast_three_hourly = r.json()["data"]
    #     log(forecast_three_hourly)
    #
    # except Exception as inst:
    #     log(f'Error retrieving three hourly forecast from {bom_api_forecast_three_hourly_url}')
    #     raise
    #
    # # Get RAIN FORECAST
    # try:
    #     r = requests.get(bom_api_forecast_rain)
    #     forecast_rain = r.json()["data"]
    #     log(forecast_rain)
    #
    # except Exception as inst:
    #     log(f'Error retrieving rain forecast from {bom_api_forecast_rain}')
    #     raise

    # CURRENT OBSERVATIONS

    # IMPORTANT - to avoid issues with Kodi malforming weather values due to 'magic'
    # (the magic is presumably because Kodi seeks to support both farenheit and celsius, so unofrtunately tends to return 0
    # for any non-numeric value in these labels...
    # ...So, we set the normal Kodi weather labels as best we can.
    # ...But, we also set a version with OzW_ prepended to the label name, which is used in OzWeather Skin files to avoid this.

    if current_observations:
        weather_data['Current.Temperature'] = current_observations['temp']
        weather_data['Current.Ozw_Temperature'] = current_observations['temp']
        weather_data['Current.Humidity'] = current_observations['humidity'] or 0
        weather_data['Current.Ozw_Humidity'] = current_observations['humidity'] or "N/A"
        weather_data['Current.WindSpeed'] = current_observations['wind']['speed_kilometre']
        weather_data['Current.OzW_WindSpeed'] = current_observations['wind']['speed_kilometre']
        weather_data['Current.WindDirection'] = current_observations['wind']['direction']
        weather_data['Current.Wind'] = f'From {current_observations["wind"]["direction"]} at {current_observations["wind"]["speed_kilometre"]} kph'
        if current_observations["gust"] is not None:
            weather_data['Current.WindGust'] = f'{current_observations["gust"]["speed_kilometre"]}'
        else:
            weather_data['Current.WindGust'] = "N/A "
        weather_data['Current.Precipitation'] = weather_data["Current.RainSince9"] = current_observations["rain_since_9am"] or 0

    # Sometimes this is not provided...
    if current_observations['temp_feels_like']:
        weather_data['Current.FeelsLike'] = current_observations['temp_feels_like']
        weather_data['Current.OzW_FeelsLike'] = current_observations['temp_feels_like']
    # if not provided, attempt to calculate it - https://www.vcalc.com/wiki/rklarsen/Australian+Apparent+Temperature+%28AT%29
    # AT = Ta + 0.33•ρ − 0.70•ws − 4.00
    else:
        try:
            log("Feels Like not provided by BOM.  Attempting to calculate feels like...but will likely fail...")
            water_vapour_pressure = current_observations['humidity'] * 6.105 * math.exp((17.27 * current_observations['temp'])/(237.7 + current_observations['temp']))
            calculated_feels_like = current_observations['temp'] + (0.33 * water_vapour_pressure) - (0.70 * current_observations['wind']['speed_kilometre']) - 4.00
            weather_data['Current.FeelsLike'] = calculated_feels_like
            weather_data['Current.Ozw_FeelsLike'] = calculated_feels_like
            log(f"Success!  Using calculated feels like of {calculated_feels_like}")
        # Not provided, could not calculate it, so set it to the current temp (avoids Kodi showing a random '0' value!)
        except:
            log("Feels like not provided, could not calculate - setting to current temperature to avoid kodi displaying random 0s.")
            weather_data['Current.FeelsLike'] = str(round(current_observations['temp']))

    # WARNINGS
    warnings_text = ""
    if warnings:
        for i, warning in enumerate(warnings):
            # Warnings body...only major warnings as we don't need every little message about sheep grazing etc..
            if warning['warning_group_type'] == 'major':
                # Don't really care when it was issue, if it hasn't expired, it's current, so show it..
                # warning_issued = utc_str_to_local_str(warning['issue_time'], local_format='%d/%m %I:%M%p', time_zone=location_timezone)
                # Time signature on the expiry is different for some reason?!
                # Remove the completely unnecessary fractions of a second...
                warning_expires = utc_str_to_local_str(warning['expiry_time'].replace('.000Z', 'Z'), local_format='%d/%m %I:%M%p', time_zone=location_timezone)
                # Strip off the date if it is today...
                if now.strftime('%d/%m %I:%M%p')[0:5] == warning_expires[0:5]:
                    warning_expires = warning_expires[6:]
                    warning_expires = warning_expires.lstrip('0')

                # We filter out any expired warnings, cause...well, who cares after the fact?
                warning_expires_dt = utc_str_to_local_datetime(warning['expiry_time'].replace('.000Z', 'Z'), time_zone=location_timezone)
                if warning_expires_dt > now:
                    warning_text = f'- {warning["title"]} (expires {warning_expires})'
                    warnings_text += warning_text
                    warnings_text += '\n'
                    if i == len(warnings):
                        warnings_text += '\n'

        # Did we actually add any warnings once expired/minor were filtered out?  If so, add the Warning Header
        if warnings_text and area_information:
            warnings_text = f"[B]Major Warnings[/B], current for {area_information['name']}:\n" + warnings_text

    # Pop where the observations are from on the end of the extended text
    warnings_text += f"\n(Current weather observations retrieved from {weather_data['ObservationsStation']} station).\n\n"

    weather_data['Current.WarningsText'] = warnings_text

    # 7 DAY FORECAST
    if forecast_seven_days:
        weather_data['Current.Condition'] = forecast_seven_days[0]['short_text']
        weather_data['Current.ConditionLong'] = forecast_seven_days[0]['extended_text']
        weather_data['Current.Sunrise'] = weather_data['Today.Sunrise'] = utc_str_to_local_str(forecast_seven_days[0]['astronomical']['sunrise_time'], time_zone=location_timezone)
        weather_data['Current.Sunset'] = weather_data['Today.Sunset'] = utc_str_to_local_str(forecast_seven_days[0]['astronomical']['sunset_time'], time_zone=location_timezone)
        weather_data['Current.FireDanger'] = 'None' if not forecast_seven_days[0]['fire_danger'] else forecast_seven_days[0]['fire_danger']
        weather_data["Current.NowLabel"] = forecast_seven_days[0]['now']['now_label']
        weather_data["Current.NowValue"] = forecast_seven_days[0]['now']['temp_now']
        weather_data["Current.LaterLabel"] = forecast_seven_days[0]['now']['later_label']
        weather_data["Current.LaterValue"] = forecast_seven_days[0]['now']['temp_later']

        # For each day of the forecast...
        for i, forecast_day in enumerate(forecast_seven_days):

            forecast_datetime = utc_str_to_local_datetime(forecast_seven_days[i]['date'], time_zone=location_timezone)
            # The names for days - short (Mon) and long (Monday)
            set_key(weather_data, i, "ShortDay", forecast_datetime.strftime('%a'))
            set_key(weather_data, i, "Title", forecast_datetime.strftime('%A'))
            set_key(weather_data, i, "LongDay", forecast_datetime.strftime('%A'))
            # Date (Apr 4)
            set_key(weather_data, i, "ShortDate", forecast_datetime.strftime('%b ') + forecast_datetime.strftime('%d').lstrip('0'))
            # Outlook / Condition (same thing)
            set_key(weather_data, i, "Outlook", forecast_seven_days[i]['short_text'])
            set_key(weather_data, i, "Condition", forecast_seven_days[i]['short_text'])
            #  See end of loop for the extended forecast (OutlookLong, ConditionLong)
            #  as we add warnings and sun protection info.OutlookLong / ConditionLong (same thing) - extended text forecast -

            # Weather icon (icon for the current day is different - i.e. we use night icons if it is night...)
            icon_code = "na"
            # By default, we use the icon_descriptor the BOM supplies
            # However, preferentially try and use the short text, to cope with BOM madness like:
            # "icon_descriptor":"mostly_sunny","short_text":"Mostly cloudy."
            icon_descriptor = forecast_seven_days[i]['icon_descriptor']
            if forecast_seven_days[i]['short_text']:
                descriptor_from_short_text = forecast_seven_days[i]['short_text'].lower()
                descriptor_from_short_text = descriptor_from_short_text.replace(' ', '_').replace('.', '').strip()
                if descriptor_from_short_text in Store.WEATHER_CODES:
                    log("Using short text as icon descriptor as this is often more reliable than the actual icon_descriptor")
                    icon_descriptor = descriptor_from_short_text
            # Now we have some sort of icon descriptor, try and get the actual icon_code
            try:
                if i == 0 and forecast_seven_days[i]['now']['is_night']:
                    icon_code = Store.WEATHER_CODES_NIGHT[icon_descriptor]
                else:
                    icon_code = Store.WEATHER_CODES[icon_descriptor]
            except KeyError:
                log(f'Could not find icon code for BOM icon_descriptor: {forecast_seven_days[i]["icon_descriptor"]} and from short text {descriptor_from_short_text}')
                # Pop the missing icon descriptor into the outlook to make it easier for people to report in the forum thread
                set_key(weather_data, i, "Outlook", f"[{forecast_seven_days[i]['icon_descriptor']}] {forecast_seven_days[i]['short_text']}")

            log(f"Icon descriptor is: {icon_descriptor}, icon code is {icon_code}")
            set_keys(weather_data, i, ["OutlookIcon", "ConditionIcon"], f'{icon_code}.png')
            set_keys(weather_data, i, ["FanartCode"], icon_code)

            # Maxes, Mins
            # In general, just get this from the forecast
            # But the BOM, bizarrely, removes the min/max for the current day
            # Which is f-ing stupid, but there you go.
            # Then there's this dance with the 'now' data as to what it means depending on the time
            # Which is a thoroughly sh*t way to design an API...
            # All that being said, with the re-design of the skin files, we now use the 'now' info for the current day
            # And not the forecast info, but left here for compatibility (see Current.X above for what we do use now)
            temp_max = forecast_seven_days[i]['temp_max']
            if i == 0 and not temp_max:
                if forecast_seven_days[i]['now']['now_label'] == "Tomorrow's Max":
                    log("Using now->temp_now as now->now_label is Tomorrow's Max")
                    temp_max = forecast_seven_days[i]['now']['temp_now']
                elif forecast_seven_days[i]['now']['later_label'] == "Tomorrow's Max":
                    log("Using now->temp_later as now->later_label is Tomorrow's Max")
                    temp_max = forecast_seven_days[i]['now']['temp_later']
            set_keys(weather_data, i, ["HighTemp", "HighTemperature"], temp_max)

            temp_min = forecast_seven_days[i]['temp_min']
            if i == 0 and not temp_min:
                if forecast_seven_days[i]['now']['now_label'] == 'Overnight Min':
                    log("Using now->temp_now as now->now_label is Overnight Min")
                    temp_min = forecast_seven_days[i]['now']['temp_now']
                elif forecast_seven_days[i]['now']['later_label'] == 'Overnight Min':
                    log("Using now->temp_later as now->later_label is Overnight Min")
                    temp_min = forecast_seven_days[i]['now']['temp_later']
            set_keys(weather_data, i, ["LowTemp", "LowTemperature"], temp_min)

            # Chance & amount of rain
            set_keys(weather_data, i, ["RainChance", "ChancePrecipitation"], f'{forecast_seven_days[i]["rain"]["chance"]}%')
            amount_min = forecast_seven_days[i]['rain']['amount']['min'] or '0'
            amount_max = forecast_seven_days[i]['rain']['amount']['max'] or '0'
            if amount_min == '0' and amount_max == '0':
                set_keys(weather_data, i, ["RainChanceAmount", "RainAmount", "Precipitation"], 'None')
            else:
                set_keys(weather_data, i, ["RainChanceAmount", "RainAmount", "Precipitation"], f'{amount_min}-{amount_max}mm')

            # UV - Predicted max, text for such, and the recommended 'Wear Sun Protection' period
            set_key(weather_data, i, 'UVIndex',  f'{forecast_seven_days[i]["uv"]["max_index"]}' or "")
            if forecast_seven_days[i]['uv']['category']:
                set_key(weather_data, i, 'UVIndex', f'{forecast_seven_days[i]["uv"]["max_index"]} ({forecast_seven_days[i]["uv"]["category"].title()})' or "")
                set_key(weather_data, i, 'UVCategory', forecast_seven_days[i]['uv']['category'].title() or "")
            else:
                set_key(weather_data, i, 'UVCategory', "None")

            # OutlookLong / Condition Long
            extended_text = f'{forecast_seven_days[i]["extended_text"]}' or ""

            # Add sun protection recommendation, if there is one
            if i == 0 and forecast_seven_days[i]['uv']['start_time'] and forecast_seven_days[i]['uv']['end_time']:
                sun_protection_start = utc_str_to_local_str(forecast_seven_days[i]['uv']['start_time'], time_zone=location_timezone)
                sun_protection_end = utc_str_to_local_str(forecast_seven_days[i]['uv']['end_time'], time_zone=location_timezone)
                sun_text = f'Sun protection is recommended from {sun_protection_start} to {sun_protection_end}.'
                extended_text = f'{extended_text}\n\n{sun_text}'

            # For the current day, add the warnings if there are any.
            if i == 0 and warnings_text:
                extended_text = f'{extended_text}\n\n{warnings_text}'

            # TESTING for skin scrolling - DON'T LEAVE THIS UNCOMMENTED!
            # for j in range(0, 5):
            #     extended_text += "add some more random text on the end so it just goes on and on\n"

            set_key(weather_data, i, "OutlookLong", extended_text)
            set_key(weather_data, i, "ConditionLong", extended_text)

        # Cleanup & Final Data massaging
        # Historical - these are not available from the BOM API
        weather_data['Current.DewPoint'] = "N/A"
        weather_data['Current.Pressure'] = "N/A"
        weather_data['Current.FireDangerText'] = ""  # -> use only FireDanger with the BOM as is now text already

    return weather_data


###########################################################
# MAIN (only for unit testing outside of Kodi)

if __name__ == "__main__":

    geohashes_to_test = ['r1r11df', 'r1f94ew']
    for geohash in geohashes_to_test:
        log(f'Getting weather data from BOM for geohash "{geohash}"')
        weather_data = bom_forecast(geohash)

        for key in sorted(weather_data):
            if weather_data[key] == "?" or weather_data[key] == "na":
                log("**** MISSING: ")
            log(f'{key}: "{weather_data[key]}"')

"""
BOM API

Information about the area the geohash represents:
https://api.weather.bom.gov.au/v1/locations/r659gg5 

{
    "data": {
        "geohash": "r659gg5", 
        "has_wave": true, 
        "id": "Gosford-r659gg5", 
        "latitude": -33.42521667480469, 
        "longitude": 151.3414764404297, 
        "marine_area_id": "NSW_MW009", 
        "name": "Gosford", 
        "state": "NSW", 
        "tidal_point": "NSW_TP036", 
        "timezone": "Australia/Sydney"
    }, 
    "metadata": {
        "response_timestamp": "2021-04-23T03:03:17Z"
    }
}

Current Observations 
https://api.weather.bom.gov.au/v1/locations/r659gg/observations

{
    "data": {
        "gust": {
            "speed_kilometre": 11, 
            "speed_knot": 6
        }, 
        "humidity": 45, 
        "rain_since_9am": 0, 
        "station": {
            "bom_id": "061425", 
            "distance": 2226, 
            "name": "Gosford"
        }, 
        "temp": 20.2, 
        "temp_feels_like": 18, 
        "wind": {
            "direction": "SSW", 
            "speed_kilometre": 9, 
            "speed_knot": 5
        }
    }, 
    "metadata": {
        "issue_time": "2021-04-23T03:11:02Z", 
        "response_timestamp": "2021-04-23T03:24:08Z"
    }
}

Weather warnings for geohash:
https://api.weather.bom.gov.au/v1/locations/rhzwe9e/warnings

{
    "data": [
        {
            "expiry_time": "2021-04-24T02:03:41.000Z", 
            "id": "QLD_RC051_IDQ20712", 
            "issue_time": "2021-04-22T23:03:41Z", 
            "phase": "final", 
            "short_title": "Flood Warning", 
            "state": "QLD", 
            "title": "Flood Warning for Russell River", 
            "type": "flood_warning", 
            "warning_group_type": "major"
        }, 
        {
            "expiry_time": "2021-04-23T09:26:45.000Z", 
            "id": "QLD_FL028_IDQ20900", 
            "issue_time": "2021-04-22T03:26:45Z", 
            "phase": "final", 
            "short_title": "Flood Watch", 
            "state": "QLD", 
            "title": "Flood Watch for Barron River", 
            "type": "flood_watch", 
            "warning_group_type": "major"
        }
    ], 
    "metadata": {
        "response_timestamp": "2021-04-23T03:07:57Z"
    }
}

7 Day Forecast
https://api.weather.bom.gov.au/v1/locations/r659gg/forecasts/daily

{
    "data": [
        {
            "astronomical": {
                "sunrise_time": "2021-04-22T20:23:29Z", 
                "sunset_time": "2021-04-23T07:24:46Z"
            }, 
            "date": "2021-04-22T14:00:00Z", 
            "extended_text": "Mostly sunny. Areas of smoke haze this morning. Light winds.", 
            "fire_danger": null, 
            "icon_descriptor": "hazy", 
            "now": {
                "is_night": false, 
                "later_label": "Overnight Min", 
                "now_label": "Max", 
                "temp_later": 10, 
                "temp_now": 22
            }, 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 0
            }, 
            "short_text": "Sunny. Possible smoke haze.", 
            "temp_max": 22, 
            "temp_min": 8, 
            "uv": {
                "category": "moderate", 
                "end_time": "2021-04-23T04:00:00Z", 
                "max_index": 4, 
                "start_time": "2021-04-22T23:40:00Z"
            }
        }, 
        {
            "astronomical": {
                "sunrise_time": "2021-04-23T20:24:14Z", 
                "sunset_time": "2021-04-24T07:23:40Z"
            }, 
            "date": "2021-04-23T14:00:00Z", 
            "extended_text": "Mostly sunny. Light winds.", 
            "fire_danger": null, 
            "icon_descriptor": "mostly_sunny", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 5
            }, 
            "short_text": "Sunny.", 
            "temp_max": 22, 
            "temp_min": 10, 
            "uv": {
                "category": "moderate", 
                "end_time": "2021-04-24T03:40:00Z", 
                "max_index": 4, 
                "start_time": "2021-04-24T00:00:00Z"
            }
        }, 
        {
            "astronomical": {
                "sunrise_time": "2021-04-24T20:24:59Z", 
                "sunset_time": "2021-04-25T07:22:35Z"
            }, 
            "date": "2021-04-24T14:00:00Z", 
            "extended_text": "Mostly sunny. Medium (40%) chance of showers. Light winds becoming southerly 15 to 20 km/h during the day.", 
            "fire_danger": null, 
            "icon_descriptor": "shower", 
            "rain": {
                "amount": {
                    "max": 1, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 40
            }, 
            "short_text": "Possible shower.", 
            "temp_max": 21, 
            "temp_min": 10, 
            "uv": {
                "category": "moderate", 
                "end_time": "2021-04-25T03:50:00Z", 
                "max_index": 4, 
                "start_time": "2021-04-24T23:50:00Z"
            }
        }, 
        {
            "astronomical": {
                "sunrise_time": "2021-04-25T20:25:44Z", 
                "sunset_time": "2021-04-26T07:21:31Z"
            }, 
            "date": "2021-04-25T14:00:00Z", 
            "extended_text": "Partly cloudy. Medium (40%) chance of showers. Light winds.", 
            "fire_danger": null, 
            "icon_descriptor": "shower", 
            "rain": {
                "amount": {
                    "max": 1, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 40
            }, 
            "short_text": "Possible shower.", 
            "temp_max": 21, 
            "temp_min": 12, 
            "uv": {
                "category": "moderate", 
                "end_time": "2021-04-26T04:00:00Z", 
                "max_index": 5, 
                "start_time": "2021-04-25T23:40:00Z"
            }
        }, 
        {
            "astronomical": {
                "sunrise_time": "2021-04-26T20:26:29Z", 
                "sunset_time": "2021-04-27T07:20:28Z"
            }, 
            "date": "2021-04-26T14:00:00Z", 
            "extended_text": "Partly cloudy. Slight (30%) chance of a shower. Light winds.", 
            "fire_danger": null, 
            "icon_descriptor": "mostly_sunny", 
            "rain": {
                "amount": {
                    "max": 0.4, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 30
            }, 
            "short_text": "Partly cloudy.", 
            "temp_max": 21, 
            "temp_min": 10, 
            "uv": {
                "category": null, 
                "end_time": null, 
                "max_index": null, 
                "start_time": null
            }
        }, 
        {
            "astronomical": {
                "sunrise_time": "2021-04-27T20:27:14Z", 
                "sunset_time": "2021-04-28T07:19:26Z"
            }, 
            "date": "2021-04-27T14:00:00Z", 
            "extended_text": "Partly cloudy. Slight (30%) chance of a shower. Light winds.", 
            "fire_danger": null, 
            "icon_descriptor": "mostly_sunny", 
            "rain": {
                "amount": {
                    "max": 1, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 30
            }, 
            "short_text": "Partly cloudy.", 
            "temp_max": 21, 
            "temp_min": 12, 
            "uv": {
                "category": null, 
                "end_time": null, 
                "max_index": null, 
                "start_time": null
            }
        }, 
        {
            "astronomical": {
                "sunrise_time": "2021-04-28T20:27:59Z", 
                "sunset_time": "2021-04-29T07:18:25Z"
            }, 
            "date": "2021-04-28T14:00:00Z", 
            "extended_text": "Partly cloudy. Medium (40%) chance of showers. Light winds.", 
            "fire_danger": null, 
            "icon_descriptor": "shower", 
            "rain": {
                "amount": {
                    "max": 2, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 40
            }, 
            "short_text": "Possible shower.", 
            "temp_max": 21, 
            "temp_min": 11, 
            "uv": {
                "category": null, 
                "end_time": null, 
                "max_index": null, 
                "start_time": null
            }
        }
    ], 
    "metadata": {
        "forecast_region": "Central Coast", 
        "forecast_type": "metropolitan", 
        "issue_time": "2021-04-23T00:04:22Z", 
        "response_timestamp": "2021-04-23T03:06:43Z"
    }
}

3 Hourly Forecast:
https://api.weather.bom.gov.au/v1/locations/r659gg/forecasts/3-hourly

{
    "data": [
        {
            "icon_descriptor": "hazy", 
            "is_night": false, 
            "next_forecast_period": "2021-04-23T06:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 0
            }, 
            "temp": 21, 
            "time": "2021-04-23T03:00:00Z", 
            "wind": {
                "direction": "SW", 
                "speed_kilometre": 11, 
                "speed_knot": 6
            }
        }, 
        {
            "icon_descriptor": "hazy", 
            "is_night": false, 
            "next_forecast_period": "2021-04-23T09:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 0
            }, 
            "temp": 21, 
            "time": "2021-04-23T06:00:00Z", 
            "wind": {
                "direction": "SW", 
                "speed_kilometre": 9, 
                "speed_knot": 5
            }
        }, 
        {
            "icon_descriptor": "hazy", 
            "is_night": true, 
            "next_forecast_period": "2021-04-23T12:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 0
            }, 
            "temp": 17, 
            "time": "2021-04-23T09:00:00Z", 
            "wind": {
                "direction": "NNE", 
                "speed_kilometre": 4, 
                "speed_knot": 2
            }
        }, 
        {
            "icon_descriptor": "hazy", 
            "is_night": true, 
            "next_forecast_period": "2021-04-23T15:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 0
            }, 
            "temp": 15, 
            "time": "2021-04-23T12:00:00Z", 
            "wind": {
                "direction": "NW", 
                "speed_kilometre": 6, 
                "speed_knot": 3
            }
        }, 
        {
            "icon_descriptor": "mostly_sunny", 
            "is_night": true, 
            "next_forecast_period": "2021-04-23T18:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 5
            }, 
            "temp": 11, 
            "time": "2021-04-23T15:00:00Z", 
            "wind": {
                "direction": "WSW", 
                "speed_kilometre": 11, 
                "speed_knot": 6
            }
        }, 
        {
            "icon_descriptor": "mostly_sunny", 
            "is_night": true, 
            "next_forecast_period": "2021-04-23T21:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 5
            }, 
            "temp": 10, 
            "time": "2021-04-23T18:00:00Z", 
            "wind": {
                "direction": "W", 
                "speed_kilometre": 13, 
                "speed_knot": 7
            }
        }, 
        {
            "icon_descriptor": "mostly_sunny", 
            "is_night": false, 
            "next_forecast_period": "2021-04-24T00:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 5
            }, 
            "temp": 11, 
            "time": "2021-04-23T21:00:00Z", 
            "wind": {
                "direction": "W", 
                "speed_kilometre": 13, 
                "speed_knot": 7
            }
        }, 
        {
            "icon_descriptor": "sunny", 
            "is_night": false, 
            "next_forecast_period": "2021-04-24T03:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 5
            }, 
            "temp": 19, 
            "time": "2021-04-24T00:00:00Z", 
            "wind": {
                "direction": "WSW", 
                "speed_kilometre": 11, 
                "speed_knot": 6
            }
        }, 
        {
            "icon_descriptor": "sunny", 
            "is_night": false, 
            "next_forecast_period": "2021-04-24T06:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 5
            }, 
            "temp": 22, 
            "time": "2021-04-24T03:00:00Z", 
            "wind": {
                "direction": "W", 
                "speed_kilometre": 7, 
                "speed_knot": 4
            }
        }, 
        {
            "icon_descriptor": "sunny", 
            "is_night": false, 
            "next_forecast_period": "2021-04-24T09:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 5
            }, 
            "temp": 21, 
            "time": "2021-04-24T06:00:00Z", 
            "wind": {
                "direction": "E", 
                "speed_kilometre": 9, 
                "speed_knot": 5
            }
        }, 
        {
            "icon_descriptor": "mostly_sunny", 
            "is_night": true, 
            "next_forecast_period": "2021-04-24T12:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 5
            }, 
            "temp": 15, 
            "time": "2021-04-24T09:00:00Z", 
            "wind": {
                "direction": "NE", 
                "speed_kilometre": 6, 
                "speed_knot": 3
            }
        }, 
        {
            "icon_descriptor": "mostly_sunny", 
            "is_night": true, 
            "next_forecast_period": "2021-04-24T15:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 5
            }, 
            "temp": 13, 
            "time": "2021-04-24T12:00:00Z", 
            "wind": {
                "direction": "WNW", 
                "speed_kilometre": 9, 
                "speed_knot": 5
            }
        }, 
        {
            "icon_descriptor": "mostly_sunny", 
            "is_night": true, 
            "next_forecast_period": "2021-04-24T18:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 5
            }, 
            "temp": 12, 
            "time": "2021-04-24T15:00:00Z", 
            "wind": {
                "direction": "WSW", 
                "speed_kilometre": 13, 
                "speed_knot": 7
            }
        }, 
        {
            "icon_descriptor": "sunny", 
            "is_night": true, 
            "next_forecast_period": "2021-04-24T21:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 5
            }, 
            "temp": 11, 
            "time": "2021-04-24T18:00:00Z", 
            "wind": {
                "direction": "WSW", 
                "speed_kilometre": 15, 
                "speed_knot": 8
            }
        }, 
        {
            "icon_descriptor": "sunny", 
            "is_night": false, 
            "next_forecast_period": "2021-04-25T00:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 5
            }, 
            "temp": 11, 
            "time": "2021-04-24T21:00:00Z", 
            "wind": {
                "direction": "WSW", 
                "speed_kilometre": 15, 
                "speed_knot": 8
            }
        }, 
        {
            "icon_descriptor": "mostly_sunny", 
            "is_night": false, 
            "next_forecast_period": "2021-04-25T03:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 5
            }, 
            "temp": 19, 
            "time": "2021-04-25T00:00:00Z", 
            "wind": {
                "direction": "SW", 
                "speed_kilometre": 15, 
                "speed_knot": 8
            }
        }, 
        {
            "icon_descriptor": "mostly_sunny", 
            "is_night": false, 
            "next_forecast_period": "2021-04-25T06:00:00Z", 
            "rain": {
                "amount": {
                    "max": null, 
                    "min": 0, 
                    "units": "mm"
                }, 
                "chance": 10
            }, 
            "temp": 21, 
            "time": "2021-04-25T03:00:00Z", 
            "wind": {
                "direction": "S", 
                "speed_kilometre": 15, 
                "speed_knot": 8
            }
        }
    ], 
    "metadata": {
        "issue_time": "2021-04-23T00:04:15Z", 
        "response_timestamp": "2021-04-23T03:23:14Z"
    }
}

Rain Forecast - Next 3 Hours (I think?)
https://api.weather.bom.gov.au/v1/locations/rhzwe9e/forecast/rain

{
    "data": {
        "amount": {
            "max": 1.2, 
            "min": 0.2, 
            "units": "mm"
        }, 
        "chance": 52, 
        "period": "PT3H", 
        "start_time": "2021-04-23T06:00:00Z"
    }, 
    "metadata": {
        "response_timestamp": "2021-04-23T03:27:50Z"
    }
}

"""