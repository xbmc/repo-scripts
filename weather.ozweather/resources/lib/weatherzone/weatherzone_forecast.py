# -*- coding: utf-8 -*-
import sys
import requests
import re
import datetime
import xbmc
from bs4 import BeautifulSoup

# Small hack to allow for unit testing - see common.py for explanation
if not xbmc.getUserAgent():
    sys.path.insert(0, '../../..')

from resources.lib.weatherzone.weatherzone_location import *
# As we're likely to later remove this Weatherzone stuff, store common functions in the BOM code
from resources.lib.bom.bom_forecast import *


def fireDangerToText(fire_danger_float):
    """
    Convert a fire danger numerical rating to human friendly text
    """
    if 0.0 <= fire_danger_float <= 5.99:
        fire_danger_text = "Low"
    elif 6 <= fire_danger_float <= 11.99:
        fire_danger_text = "Moderate"
    elif 12.0 <= fire_danger_float <= 24.99:
        fire_danger_text = "High"
    elif 25.0 <= fire_danger_float <= 49.99:
        fire_danger_text = "Very High"
    elif 50.0 <= fire_danger_float <= 74.99:
        fire_danger_text = "Severe"
    elif 75.0 <= fire_danger_float <= 99.99:
        fire_danger_text = "Extreme"
    elif fire_danger_float >= 100.0:
        fire_danger_text = "Catastrophic"
    else:
        fire_danger_text = "?"

    return fire_danger_text


def cleanShortDescription(description):
    """
    Clean up the short weather description text
    """
    description = description.replace('<br />', '')
    description = description.replace('<Br />', '')
    description = description.replace('-', '')
    description = description.replace('-', '')
    description = description.replace('ThunderStorms', 'Thunderstorms')
    description = description.replace('windy', 'Windy')
    # title capitalises the first letter of each word
    return description.title()


def cleanLongDescription(description):
    """
    Clean up the long weather description text
    """
    description = description.replace('\t', '')
    description = description.replace('\r', ' ')
    description = description.replace('&amp;', '&')
    description = description[:-1]
    return description


def getWeatherData(url_path):
    """
    Get weather data from a given Weatherzone url_path
    """
    log(f'Requesting & souping weather page at {Store.WEATHERZONE_URL}{url_path}')

    # This is where we store it all
    weather_data = {}

    # Get the page data...
    try:
        r = requests.get(f'{Store.WEATHERZONE_URL}{url_path}')
        soup = BeautifulSoup(r.text, 'html.parser')

        # We need to extract the location id for the ajax loaded forecast data...
        lc = re.search(r'lc: \"(\d+)\"', r.text)
        if lc:
            weather_data['lc'] = lc.group(1)
        else:
            log(f"Error finding lc value for {url_path} - 7 day forecast probably won't work...")

    except Exception as inst:
        # If we can't get and parse the page at all, might as well bail right out...
        log(f'Error requesting/souping weather page at {Store.WEATHERZONE_URL}{url_path}')
        raise

    # Bail early if we can't parse the data for whatever reason...
    if not soup:
        log(f"Soup was None - can't get weather data from {Store.WEATHERZONE_URL}{url_path}")
        return weather_data

    else:
        # The longer forecast text
        try:
            p = soup.find_all("p", class_="district-forecast")
            weather_data["Current.ConditionLong"] = "(FALLBACK WEATHERZONE DATA - BOM location not configured, or BOM API not available?).\n\n"
            weather_data["Current.ConditionLong"] += cleanLongDescription(p[0].text).strip()
        except Exception as inst:
            log(str(inst))
            log("Exception in ConditionLong")
            weather_data["Current.ConditionLong"] = "?"

        # Astronomy Data
        try:
            astronomy_table = soup.find("table", class_="astronomy")
            tds = astronomy_table.find_all("td")

            # Moonphase
            value = tds[4].find("img").get('title').title().strip()
            weather_data['Today.moonphase'] = value
            weather_data['Today.Moonphase'] = value

            # Sunrise/set
            sunrise = tds[1].text.strip()
            sunset = tds[2].text.strip()
            weather_data['Today.Sunrise'] = sunrise
            weather_data['Today.Sunset'] = sunset
            weather_data['Current.Sunrise'] = sunrise
            weather_data['Current.Sunset'] = sunset

        except Exception as inst:
            log(f"Exception processing astronomy data from {Store.WEATHERZONE_URL}{url_path}\n" + str(inst))
            weather_data['Today.moonphase'] = "?"
            weather_data['Today.Moonphase'] = "?"
            weather_data['Today.Sunrise'] = "?"
            weather_data['Today.Sunset'] = "?"
            weather_data['Current.Sunrise'] = "?"
            weather_data['Current.Sunset'] = "?"

        # Current Conditions - split in to two sides
        try:

            div_current_details_lhs = soup.find("div", class_="details_lhs")
            lhs = div_current_details_lhs.find_all("td", class_="hilite")

            # Labels we set to emulate the BOM data...
            weather_data["Current.NowLabel"] = "Predicted Min"
            weather_data["Current.LaterLabel"] = "Predicted Max"

            # LHS
            try:
                weather_data["Current.Temperature"] = str(int(round(float(lhs[0].text[:-2]))))
                weather_data["Current.OzW_Temperature"] = str(int(round(float(lhs[0].text[:-2]))))
            except Exception as inst:
                log(str(inst))
                weather_data["Current.Temperature"] = "?"
                weather_data["Current.OzW_Temperature"] = "?"
            try:
                weather_data["Current.DewPoint"] = str(int(round(float(lhs[1].text[:-2]))))
            except Exception as inst:
                log(str(inst))
                weather_data["Current.DewPoint"] = "?"
            try:
                weather_data["Current.FeelsLike"] = str(int(round(float(lhs[2].text[:-2]))))
                weather_data["Current.Ozw_FeelsLike"] = str(int(round(float(lhs[2].text[:-2]))))
            except Exception as inst:
                log(str(inst))
                weather_data["Current.FeelsLike"] = "?"
                weather_data["Current.Ozw_FeelsLike"] = "N/A"
            try:
                weather_data["Current.Humidity"] = str(int(round(float(lhs[3].text[:-1]))))
                weather_data["Current.Ozw_Humidity"] = str(int(round(float(lhs[3].text[:-1]))))
            except Exception as inst:
                log(str(inst))
                weather_data["Current.Humidity"] = "?"
                weather_data["Current.OzW_Humidity"] = "N/A"
            try:
                weather_data["Current.WindDirection"] = str(lhs[4].text.split(" ")[0])
                weather_data["Current.WindDegree"] = weather_data["Current.WindDirection"]
            except Exception as inst:
                log(str(inst))
                weather_data["Current.WindDirection"] = "?"
                weather_data["Current.WindDegree"] = "?"
            try:
                weather_data["Current.Wind"] = str(lhs[4].text.split(" ")[1][:-4])
            except Exception as inst:
                log(str(inst))
                weather_data["Current.Wind"] = "?"
            try:
                weather_data["Current.WindGust"] = str(lhs[5].text[:-4])
            except Exception as inst:
                log(str(inst))
                weather_data["Current.WindGust"] = "?"
            try:
                weather_data["Current.Pressure"] = str(lhs[6].text[:-3])
            except Exception as inst:
                log(str(inst))
                weather_data["Current.Pressure"] = "?"
            try:
                weather_data["Current.FireDanger"] = str(float(lhs[7].text))
            except Exception as inst:
                log(str(inst))
                weather_data["Current.FireDanger"] = "?"
            try:
                weather_data["Current.FireDangerText"] = fireDangerToText(float(lhs[7].text))
            except Exception as inst:
                log(str(inst))
                weather_data["Current.FireDangerText"] = "?"
            try:
                rain_since = lhs[8].text.partition('/')
                if rain_since[0] == "- ":
                    weather_data["Current.RainSince9"] = "0 mm"
                    weather_data["Current.Precipitation"] = "0 mm"
                else:
                    weather_data["Current.RainSince9"] = str(rain_since[0][:-3])
                    weather_data["Current.Precipitation"] = str(weather_data["Current.RainSince9"])
                if rain_since[2] == " -":
                    weather_data["Current.RainLastHr"] = "0 mm"
                else:
                    weather_data["Current.RainLastHr"] = str(rain_since[2][:-2])
            except Exception as inst:
                log(str(inst))
                weather_data["Current.RainSince9"] = "?"
                weather_data["Current.Precipitation"] = "?"
                weather_data["Current.RainLastHr"] = "?"

        except Exception as inst:
            log("Exception processing current conditions data from {Store.WEATHERZONE_URL}{url_path}\n" + str(inst))

        # 7 Day Forecast & UV
        try:
            # We have to store these, and then set at the end...as we need to process two rows to get all the info..

            wind_speeds9am = []
            wind_speeds3pm = []
            wind_directions9am = []
            wind_directions3pm = []

            # Pre April 2020 (and if they revert back as they sometime do)..
            # ...direct load the forecast data from the on-page table
            forecast_table = soup.find("table", id="forecast-table")

            # April 2020 - WeatherZone have moved to ajax loading this data?
            if forecast_table is None:
                r = requests.post(f'{Store.WEATHERZONE_URL}/local/ajax/forecastlocal.jsp',
                                  data={'lt': 'twcid', 'lc': weather_data['lc'], 'fs': 'TWC'})
                ajax_soup = BeautifulSoup(r.text, 'html.parser')
                forecast_table = ajax_soup.find("table", id="forecast-table")

            for index, row in enumerate(forecast_table.find_all("tr")):

                # Days and dates
                if index == 0:

                    for i, day in enumerate(row.find_all("span", class_="bold")):
                        try:
                            full_day = Store.DAYS[day.text]
                            set_key(weather_data, i, "ShortDay", day.text)
                            set_key(weather_data, i, "Title", full_day)
                            set_key(weather_data, i, "LongDay", full_day)

                        except Exception as inst:
                            log(str(inst))
                            log("Exception in ShortDay,Title,LongDay")
                            set_key(weather_data, i, "ShortDay", "?")
                            set_key(weather_data, i, "Title", "?")
                            set_key(weather_data, i, "LongDay", "?")

                    for i, date in enumerate(row.find_all("span", class_="text_blue")):
                        try:
                            set_key(weather_data, i, "ShortDate", date.text[3:])

                        except Exception as inst:
                            log(str(inst))
                            log("Exception in ShortDate")
                            set_key(weather_data, i, "ShortDate", "?")

                # Outlook = Short Descriptions & Corresponding Icons
                if index == 1:

                    for i, shortDesc in enumerate(row.find_all("span")):

                        try:
                            set_key(weather_data, i, "Outlook", cleanShortDescription(shortDesc.text))
                            set_key(weather_data, i, "Condition", cleanShortDescription(shortDesc.text))
                        except Exception as inst:
                            log(str(inst))
                            log("Exception in Outlook,Condition")
                            set_key(weather_data, i, "Outlook", "?")
                            set_key(weather_data, i, "Condition", "?")

                        # Attempt to set day / night weather codes as appropriate...
                        # Fall back on day codes if things go wrong...
                        try:
                            now = datetime.datetime.now()

                            # Try and use the actual sunrise/sunset, otherwise go with defaults of sunrise 7am, sunset 7pm
                            try:
                                sunrise_time = weather_data['Today.Sunrise'].split(" ")
                                sunrise_hour = sunrise_time[0].split(":")[0]
                                sunrise_minutes = sunrise_time[0].split(":")[1]
                            except Exception as inst:
                                sunrise_hour = 7
                                sunrise_minutes = 0

                            try:
                                sunset_time = weather_data['Today.Sunset'].split(" ")
                                sunset_hour = sunset_time[0].split(":")[0]
                                sunset_minutes = sunset_time[0].split(":")[1]
                            except Exception as inst:
                                sunset_hour = 19
                                sunset_minutes = 0

                            today_sunrise = now.replace(hour=int(sunrise_hour), minute=int(sunrise_minutes), second=0,
                                                        microsecond=0)
                            today_sunset = now.replace(hour=int(sunset_hour), minute=int(sunset_minutes), second=0,
                                                       microsecond=0)

                            code_to_look_up = cleanShortDescription(shortDesc.text).replace(" ","_").lower()
                            if i == 0 and (now > today_sunset or now < today_sunrise):
                                weather_code = Store.WEATHER_CODES_NIGHT[code_to_look_up]
                            else:
                                weather_code = Store.WEATHER_CODES[code_to_look_up]

                        except Exception as inst:
                            log(str(inst))
                            log("Exception in weather_code")
                            try:
                                weather_code = Store.WEATHER_CODES[code_to_look_up]
                            except Exception as inst:
                                log(str(inst))
                                log("Exception (2nd) in weather_code")
                                weather_code = 'na'

                        value = '%s.png' % weather_code
                        set_keys(weather_data, i, ["OutlookIcon", "ConditionIcon"], value)
                        set_keys(weather_data, i, ["FanartCode"], value.replace(".png", ""))

                # Maximums
                if index == 2:

                    for i, td in enumerate(row.find_all("td")):
                        try:
                            value = '%s' % td.text[:-2]
                            set_keys(weather_data, i, ["HighTemp", "HighTemperature"], value)
                            if i == 0:
                                set_key(weather_data, i, "NowValue", value)
                        except Exception as inst:
                            log(str(inst))
                            log("Exception in HighTemp,HighTemperature")
                            set_keys(weather_data, i, ["HighTemp", "HighTemperature"], "?")

                            # Minimums
                if index == 3:

                    for i, td in enumerate(row.find_all("td")):
                        try:
                            value = '%s' % td.text[:-2]
                            set_keys(weather_data, i, ["LowTemp", "LowTemperature"], value)
                            if i == 0:
                                set_key(weather_data, i, "LaterValue", value)
                        except Exception as inst:
                            log(str(inst))
                            log("Exception in LowTemp,LowTemperature")
                            set_keys(weather_data, i, ["LowTemp", "LowTemperature"], "?")

                            # Chance of rain
                if index == 4:

                    for i, td in enumerate(row.find_all("td")):
                        try:
                            value = '%s' % td.text[:-1]
                            set_key(weather_data, i, "ChancePrecipitation", value)
                            set_key(weather_data, i, "RainChance", value)
                        except Exception as inst:
                            log(str(inst))
                            log("Exception ChancePrecipitation,RainChance")
                            set_key(weather_data, i, "ChancePrecipitation", "?")
                            set_key(weather_data, i, "RainChance", "?")

                            # Amount of rain
                if index == 5:

                    for i, td in enumerate(row.find_all("td")):
                        try:
                            value = '%s' % td.text
                            set_key(weather_data, i, "Precipitation", value)
                            set_key(weather_data, i, "RainChanceAmount", value)
                            set_key(weather_data, i, "RainAmount", value)
                        except Exception as inst:
                            log(str(inst))
                            log("Exception in Precipitation,RainChanceAmount")
                            set_key(weather_data, i, "Precipitation", "?")
                            set_key(weather_data, i, "RainChanceAmount", "?")
                            set_key(weather_data, i, "RainAmount", "?")
                # UV
                if index == 6:

                    try:
                        tds = row.find_all("td")
                        span = tds[0].find("span")
                        weather_data["Current.UVIndex"] = "%s (%s)" % (span.text, span.get('title'))
                    except Exception as inst:
                        log(str(inst))
                        log("Exception in UVIndex")
                        weather_data["Current.UVIndex"] = "?"

                # Wind speed and direction - there are two values per day here...
                # and, sigh, they can appear as rows 10 and 11 or 9 and 10, depending on if there is a pollen row...

                # Wind Speed
                if index == 9 or 10:

                    try:
                        header = row.find("th")
                        if header is not None and header.text == "Wind Speed":

                            wind_speed_data = row.find_all("td")
                            for i in range(0, len(wind_speed_data), 2):
                                wind_speeds9am.append(wind_speed_data[i].text)
                                wind_speeds3pm.append(wind_speed_data[i + 1].text)
                    except Exception as inst:
                        log(str(inst))
                        wind_speeds9am.append("?")
                        wind_speeds9am.append("?")

                # # Wind Direction
                if index == 10 or 11:

                    try:
                        header = row.find("th")
                        if header is not None and header.text == "Wind Direction":
                            wind_direction_data = row.find_all("td")
                            for i in range(0, len(wind_direction_data), 2):
                                wind_directions9am.append(wind_direction_data[i].text.replace("\n", ""))
                                wind_directions3pm.append(wind_direction_data[i + 1].text.replace("\n", ""))

                    except Exception as inst:
                        log(str(inst))
                        wind_directions9am.append("?")
                        wind_directions3pm.append("?")

            # Now join the stored wind data and set it...
            for i in range(0, len(wind_speeds9am)):
                # set_key(i, "WindSpeed", "9am - " + wind_speeds9am[i] + ", 3pm - " + wind_speeds3pm[i])
                set_key(weather_data, i, "WindSpeed", wind_speeds3pm[i])
                set_key(weather_data, i, "OzW_WindSpeed", wind_speeds3pm[i])
                # set_key(i, "WindDirection", "9am - " + wind_directions9am[i] + ", 3pm - " + windDirections3pm[i])
                set_key(weather_data, i, "WindDirection", wind_directions3pm[i])

        except Exception as inst:
            log(f"Exception processing forecast rows data from {Store.WEATHERZONE_URL}{url_path}\n" + str(inst))

    return weather_data


###########################################################
# MAIN - for testing outside of Kodi

if __name__ == "__main__":

    log("\nTesting scraping of Weatherzone\n")
    log("First test getting weatherzone location from postcode/suburb name:");

    log("\n3032:")
    log(getLocationsForPostcodeOrSuburb(3032))
    log("\n9999:")
    log(getLocationsForPostcodeOrSuburb(9999))
    log("\nKyneton:")
    log(getLocationsForPostcodeOrSuburb("Kyneton"))

    log("\n\nGet weather data for /vic/central/kyneton:")

    weatherData = getWeatherData("/vic/central/kyneton")

    for key in sorted(weatherData):
        if weatherData[key] == "?" or weatherData[key] == "na":
            log("**** MISSING: ")
        log("[%s]: [%s]" % (key, weatherData[key]))

    log("\n\nGet weather data for /vic/melbourne/ascot-vale:")

    weatherData = getWeatherData("/vic/melbourne/ascot-vale")

    for key in sorted(weatherData):
        if weatherData[key] == "?" or weatherData[key] == "na":
            log("**** MISSING: ")
        log("[%s]: [%s]" % (key, weatherData[key]))
