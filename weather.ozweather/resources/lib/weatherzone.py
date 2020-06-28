# -*- coding: utf-8 -*-

import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import datetime

# This little bit of code is only for unit testing.
# When this module is run within Kodi, it will use the Kodi log function as usual
# However, when unit testing from the command line, the xbmc* modules will not be importable
# So the exception will be raised and in response we define a local log function that simply
# prints stuff to the command line.
try:
    from .common import log as log
except ImportError:
    print("\nKodi is not available -> probably unit testing")

    def log(message):
        print(message)

# CONSTANTS

SCHEMA = "https://"
WEATHERZONE_URL = 'www.weatherzone.com.au'
WEATHERZONE_SEARCH_URL = WEATHERZONE_URL + "/search/"

DAYS = {"Mon": "Monday",
        "Tue": "Tuesday",
        "Wed": "Wednesday",
        "Thu": "Thursday",
        "Fri": "Friday",
        "Sat": "Saturday",
        "Sun": "Sunday"}

WEATHER_CODES = {'Clearing Shower': '39',
                 'Cloudy': '26',
                 'Cloud And Wind Increasing': '23',
                 'Cloud Increasing': '26',
                 'Drizzle': '11',
                 'Drizzle Clearing': '39',
                 'Fog Then Sunny': '34',
                 'Frost Then Sunny': '34',
                 'Hazy': '21',
                 'Heavy Rain': '40',
                 'Heavy Showers': '12',
                 'Increasing Sunshine': '30',
                 'Late Shower': '45',
                 'Late Thunder': '47',
                 'Mostly Cloudy': '26',
                 'Mostly Sunny': '34',
                 'Overcast': '26',
                 'Possible Shower': '11',
                 'Possible Thunderstorm': '37',
                 'Rain': '40',
                 'Rain And Snow': '5',
                 'Rain Clearing': '39',
                 'Rain Developing': '12',
                 'Rain Tending To Snow': '5',
                 'Showers': '11',
                 'Showers Easing': '11',
                 'Showers Increasing': '11',
                 'Snow': '41',
                 'Snowfalls Clearing': '5',
                 'Snow Developing': '13',
                 'Snow Showers': '41',
                 'Snow Tending To Rain': '5',
                 'Sunny': '32',
                 'Thunderstorms': '38',
                 'ThunderStorms': '38',
                 'Thunderstorms Clearing': '37',
                 'Windy': '23',
                 'Windy With Rain': '2',
                 'Windy With Showers': '2',
                 'Windy With Snow': '43',
                 'Wind And Rain Increasing': '2',
                 'Wind And Showers Easing': '11',
                 'Unknown': 'na',
                 'nt_unknown': 'na'}

WEATHER_CODES_NIGHT = {'Clearing Shower': '45',
                       'Cloudy': '29',
                       'Cloud And Wind Increasing': '27',
                       'Cloud Increasing': '27',
                       'Drizzle': '45',
                       'Drizzle Clearing': '45',
                       'Fog Then Sunny': '33',
                       'Frost Then Sunny': '33',
                       'Hazy': '33',
                       'Heavy Rain': '47',
                       'Heavy Showers': '45',
                       'Increasing Sunshine': '31',
                       'Late Shower': '45',
                       'Late Thunder': '47',
                       'Mostly Cloudy': '27',
                       'Mostly Sunny': '31',
                       'Overcast': '29',
                       'Possible Shower': '45',
                       'Possible Thunderstorm': '47',
                       'Rain': '45',
                       'Rain And Snow': '46',
                       'Rain Clearing': '45',
                       'Rain Developing': '45',
                       'Rain Tending To Snow': '45',
                       'Showers': '45',
                       'Showers Easing': '45',
                       'Showers Increasing': '45',
                       'Snow': '46',
                       'Snowfalls Clearing': '46',
                       'Snow Developing': '46',
                       'Snow Showers': '46',
                       'Snow Tending To Rain': '46',
                       'Sunny': '31',
                       'Thunderstorms': '47',
                       'ThunderStorms': '47',
                       'Thunder-Storms': '47',
                       'Thunder-storms': '47',
                       'Thunderstorms Clearing': '47',
                       'Windy': '29',
                       'Windy With Rain': '45',
                       'Windy With Showers': '45',
                       'Windy With Snow': '46',
                       'Wind And Rain Increasing': '45',
                       'Wind And Showers Easing': '45',
                       'Unknown': 'na',
                       'nt_unknown': 'na'}

"""   These are the weather codes for XBMC is seems
N/A Not Available
0 Rain/Lightning
01 Windy/Rain
02 Same as 01
03 Same as 00
04 Same as 00
05 Cloudy/Snow-Rain Mix
06 Hail
07 Icy/Clouds Rain-Snow
08 Icy/Haze Rain
09 Haze/Rain
10 Icy/Rain
11 Light Rain
12 Moderate Rain
13 Cloudy/Flurries
14 Same as 13
15 Flurries
16 Same as 13
17 Same as 00
18 Same as 00
19 Dust
20 Fog
21 Haze
22 Smoke
23 Windy
24 Same as 23
25 Frigid
26 Mostly Cloudy
27 Mostly Cloudy/Night
28 Mostly Cloudy/Sunny
29 Partly Cloudy/Night
30 Partly Cloudy/Day
31 Clear/Night
32 Clear/Day
33 Hazy/Night
34 Hazy/Day
35 Same as 00
36 Hot!
37 Lightning/Day
38 Lightning
39 Rain/Day
40 Rain
41 Snow
42 Same as 41
43 Windy/Snow
44 Same as 30
45 Rain/Night
46 Snow/Night
47 Thunder Showers/Night

NIGHT SUBSET:
27 Mostly Cloudy/Night
29 Partly Cloudy/Night
31 Clear/Night
33 Hazy/Night
45 Rain/Night
46 Snow/Night
47 Thunder Showers/Night

"""

# Our global to hold the built up weather data
weatherData = {}


# Convert a fire danger numerical rating to human friendly text

def fireDangerToText(fireDangerFloat):
    if 0.0 <= fireDangerFloat <= 5.99:
        fireDangerText = "Low"
    elif 6 <= fireDangerFloat <= 11.99:
        fireDangerText = "Moderate"
    elif 12.0 <= fireDangerFloat <= 24.99:
        fireDangerText = "High"
    elif 25.0 <= fireDangerFloat <= 49.99:
        fireDangerText = "Very High"
    elif 50.0 <= fireDangerFloat <= 74.99:
        fireDangerText = "Severe"
    elif 75.0 <= fireDangerFloat <= 99.99:
        fireDangerText = "Extreme"
    elif fireDangerFloat >= 100.0:
        fireDangerText = "Catastrophic"
    else:
        fireDangerText = "?"

    return fireDangerText


# Clean up the short weather description text

def cleanShortDescription(description):
    description = description.replace('<br />', '')
    description = description.replace('<Br />', '')
    description = description.replace('-', '')
    description = description.replace('-', '')
    description = description.replace('ThunderStorms', 'Thunderstorms')
    description = description.replace('windy', 'Windy')
    # title capitalises the first letter of each word
    return description.title()


# Clean up the long weather description text

def cleanLongDescription(description):
    description = description.replace('\t', '')
    description = description.replace('\r', ' ')
    description = description.replace('&amp;', '&')
    description = description[:-1]
    return description


# Set a group of keys at once - for old and new weather label support

def setKeys(index, keys, value):
    global weatherData

    for key in keys:
        setKey(index, key, value)


# Set a key - for old and new weather label support

def setKey(index, key, value):
    global weatherData

    if index == 0:
        weatherData['Current.' + key] = value.strip()
        weatherData['Current.' + key] = value.strip()

    weatherData['Day' + str(index) + '.' + key] = value.strip()
    weatherData['Day' + str(index) + '.' + key] = value.strip()
    weatherData['Daily.' + str(index + 1) + '.' + key] = value.strip()
    weatherData['Daily.' + str(index + 1) + '.' + key] = value.strip()


# Returns an array of dicts, each with a Location name and LocationUrlPart.  Empty if no location found.
# [{'LocationName': u'Ascot Vale, VIC 3032', 'LocationUrlPart': u'/vic/melbourne/ascot-vale'}, ... ]

def getLocationsForPostcodeOrSuburb(text):
    locations = []
    locationURLPaths = []

    try:
        r = requests.post(SCHEMA + WEATHERZONE_SEARCH_URL, data={'q': text, 't': '3'})
        soup = BeautifulSoup(r.text, 'html.parser')
        log("Result url: " + r.url)

    except Exception as inst:
        log("Exception loading locations results in weatherzone.getLocationsForPostcodeOrSuburb" + str(inst))
        raise

    # Two responses are possible.
    try:

        # 1. A list of possible locations to choose from (e.g. several suburbs sharing one postcode)
        if r.url.endswith(WEATHERZONE_SEARCH_URL):
            locationUl = soup.find("ul", class_="typ2")

            # Results block missing? Short circuit
            if not locationUl:
                return locations, locationURLPaths

            for locationLi in locationUl.find_all("li"):
                location = locationLi.find("a")
                locations.append(location.text)
                locationURLPaths.append(location.get('href'))

        # 2. Straight to one location
        else:
            h1 = soup.find("h1", class_="local")
            name = h1.text.split(" Weather")[0]
            url = urlparse(r.url).path
            locations.append(name)
            locationURLPaths.append(url)

    except Exception as inst:
        log("Exception processing locations in weatherzone.getLocationsForPostcodeOrSuburb" + str(inst))
        raise

    return locations, locationURLPaths


# Returns a dict of weather data values
# All the try/excepts to follow are gross - python needs ?? support.  
# But let's not fail if one value is missing/malformed...

def getWeatherData(urlPath):
    log("Requesting & souping weather page at " + SCHEMA + WEATHERZONE_URL + urlPath)

    # Get the page data...
    try:
        r = requests.get(SCHEMA + WEATHERZONE_URL + urlPath)
        soup = BeautifulSoup(r.text, 'html.parser')

        # We need to extract the location id for the ajax loaded forecast data...
        lc = re.search(r'lc: \"(\d+)\"', r.text)
        if lc:
            weatherData['lc'] = lc.group(1)
        else:
            log("Error finding lc value for " + urlPath + " - 7 day forecast probably won't work...")

    except Exception as inst:
        # If we can't get and parse the page at all, might as well bail right out...
        log("Error requesting/souping weather page at " + SCHEMA + WEATHERZONE_URL + urlPath)
        raise

    # Bail early if we can't parse the data for whatever reason...
    if not soup:
        log("Soup was None - can't get weather data from " + SCHEMA + WEATHERZONE_URL + urlPath)
        return weatherData

    else:
        # The longer forecast text
        try:
            p = soup.find_all("p", class_="district-forecast")
            weatherData["Current.ConditionLong"] = cleanLongDescription(p[0].text).strip()
        except Exception as inst:
            log(str(inst))
            log("Exception in ConditionLong")
            weatherData["Current.ConditionLong"] = "?"

        # Astronomy Data
        try:
            astronomyTable = soup.find("table", class_="astronomy")
            tds = astronomyTable.find_all("td")

            # Moonphase
            value = tds[4].find("img").get('title').title().strip()
            weatherData['Today.moonphase'] = value
            weatherData['Today.Moonphase'] = value

            # Sunrise/set
            sunrise = tds[1].text.strip()
            sunset = tds[2].text.strip()
            weatherData['Today.Sunrise'] = sunrise
            weatherData['Today.Sunset'] = sunset
            weatherData['Current.Sunrise'] = sunrise
            weatherData['Current.Sunset'] = sunset

        except Exception as inst:
            log("Exception processing astronomy data from " + SCHEMA + WEATHERZONE_URL + urlPath + "\n" + str(inst))
            weatherData['Today.moonphase'] = "?"
            weatherData['Today.Moonphase'] = "?"
            weatherData['Today.Sunrise'] = "?"
            weatherData['Today.Sunset'] = "?"
            weatherData['Current.Sunrise'] = "?"
            weatherData['Current.Sunset'] = "?"

        # Current Conditions - split in to two sides
        try:

            divCurrentDetailsLHS = soup.find("div", class_="details_lhs")
            lhs = divCurrentDetailsLHS.find_all("td", class_="hilite")

            # LHS
            try:
                weatherData["Current.Temperature"] = str(int(round(float(lhs[0].text[:-2]))))
            except Exception as inst:
                log(str(inst))
                weatherData["Current.Temperature"] = "?"
            try:
                weatherData["Current.DewPoint"] = str(int(round(float(lhs[1].text[:-2]))))
            except Exception as inst:
                log(str(inst))
                weatherData["Current.DewPoint"] = "?"
            try:
                weatherData["Current.FeelsLike"] = str(int(round(float(lhs[2].text[:-2]))))
            except Exception as inst:
                log(str(inst))
                weatherData["Current.FeelsLike"] = "?"
            try:
                weatherData["Current.Humidity"] = str(int(round(float(lhs[3].text[:-1]))))
            except Exception as inst:
                log(str(inst))
                weatherData["Current.Humidity"] = "?"
            try:
                weatherData["Current.WindDirection"] = str(lhs[4].text.split(" ")[0])
                weatherData["Current.WindDegree"] = weatherData["Current.WindDirection"]
            except Exception as inst:
                log(str(inst))
                weatherData["Current.WindDirection"] = "?"
                weatherData["Current.WindDegree"] = "?"
            try:
                weatherData["Current.Wind"] = str(lhs[4].text.split(" ")[1][:-4])
            except Exception as inst:
                log(str(inst))
                weatherData["Current.Wind"] = "?"
            try:
                weatherData["Current.WindGust"] = str(lhs[5].text[:-4])
            except Exception as inst:
                log(str(inst))
                weatherData["Current.WindGust"] = "?"
            try:
                weatherData["Current.Pressure"] = str(lhs[6].text[:-3])
            except Exception as inst:
                log(str(inst))
                weatherData["Current.Pressure"] = "?"
            try:
                weatherData["Current.FireDanger"] = str(float(lhs[7].text))
            except Exception as inst:
                log(str(inst))
                weatherData["Current.FireDanger"] = "?"
            try:
                weatherData["Current.FireDangerText"] = fireDangerToText(float(lhs[7].text))
            except Exception as inst:
                log(str(inst))
                weatherData["Current.FireDangerText"] = "?"
            try:
                rainSince = lhs[8].text.partition('/')
                if rainSince[0] == "- ":
                    weatherData["Current.RainSince9"] = "0 mm"
                    weatherData["Current.Precipitation"] = "0 mm"
                else:
                    weatherData["Current.RainSince9"] = str(rainSince[0][:-3])
                    weatherData["Current.Precipitation"] = str(weatherData["Current.RainSince9"])
                if rainSince[2] == " -":
                    weatherData["Current.RainLastHr"] = "0 mm"
                else:
                    weatherData["Current.RainLastHr"] = str(rainSince[2][:-2])
            except Exception as inst:
                log(str(inst))
                weatherData["Current.RainSince9"] = "?"
                weatherData["Current.Precipitation"] = "?"
                weatherData["Current.RainLastHr"] = "?"

        except Exception as inst:
            log("Exception processing current conditions data from " + SCHEMA + WEATHERZONE_URL + urlPath + "\n" + str(
                inst))

        # 7 Day Forecast & UV
        try:

            # We have to store these, and then set at the end...as we need to process two rows to get all the info..

            windSpeeds9am = []
            windSpeeds3pm = []
            windDirections9am = []
            windDirections3pm = []

            # Pre April 2020 (and if they revert back as they sometime do)..
            # ...direct load the forecast data from the on-page table
            forecastTable = soup.find("table", id="forecast-table")

            # April 2020 - WeatherZone have moved to ajax loading this data?
            if forecastTable is None:
                r = requests.post(SCHEMA + WEATHERZONE_URL + '/local/ajax/forecastlocal.jsp',
                                  data={'lt': 'twcid', 'lc': weatherData['lc'], 'fs': 'TWC'})
                ajaxSoup = BeautifulSoup(r.text, 'html.parser')
                forecastTable = ajaxSoup.find("table", id="forecast-table")

            for index, row in enumerate(forecastTable.find_all("tr")):

                # Days and dates
                if index == 0:

                    for i, day in enumerate(row.find_all("span", class_="bold")):
                        try:
                            fullDay = DAYS[day.text]
                            setKey(i, "ShortDay", day.text)
                            setKey(i, "Title", fullDay)
                            setKey(i, "LongDay", fullDay)

                        except Exception as inst:
                            log(str(inst))
                            log("Exception in ShortDay,Title,LongDay")
                            setKey(i, "ShortDay", "?")
                            setKey(i, "Title", "?")
                            setKey(i, "LongDay", "?")

                    for i, date in enumerate(row.find_all("span", class_="text_blue")):
                        try:
                            setKey(i, "ShortDate", date.text[3:])

                        except Exception as inst:
                            log(str(inst))
                            log("Exception in ShortDate")
                            setKey(i, "ShortDate", "?")

                # Outlook = Short Descriptions & Corresponding Icons
                if index == 1:

                    for i, shortDesc in enumerate(row.find_all("span")):

                        try:
                            setKey(i, "Outlook", cleanShortDescription(shortDesc.text))
                            setKey(i, "Condition", cleanShortDescription(shortDesc.text))
                        except Exception as inst:
                            log(str(inst))
                            log("Exception in Outlook,Condition")
                            setKey(i, "Outlook", "?")
                            setKey(i, "Condition", "?")

                        # Attempt to set day / night weather codes as appropriate...
                        # Fall back on day codes if things go wrong...
                        try:
                            now = datetime.datetime.now()

                            # Try and use the actual sunrise/sunset, otherwise go with defaults of sunrise 7am, sunset 7pm
                            try:
                                sunriseTime = weatherData['Today.Sunrise'].split(" ")
                                sunriseHour = sunriseTime[0].split(":")[0]
                                sunriseMinutes = sunriseTime[0].split(":")[1]
                            except Exception as inst:
                                sunriseHour = 7
                                sunriseMinutes = 0

                            try:
                                sunsetTime = weatherData['Today.Sunset'].split(" ")
                                sunsetHour = sunsetTime[0].split(":")[0]
                                sunsetMinutes = sunsetTime[0].split(":")[1]
                            except Exception as inst:
                                sunsetHour = 19
                                sunsetMinutes = 0

                            todaySunrise = now.replace(hour=int(sunriseHour), minute=int(sunriseMinutes), second=0,
                                                       microsecond=0)
                            todaySunset = now.replace(hour=int(sunsetHour), minute=int(sunsetMinutes), second=0,
                                                      microsecond=0)

                            if i == 0 and (now > todaySunset or now < todaySunrise):
                                weathercode = WEATHER_CODES_NIGHT[cleanShortDescription(shortDesc.text)]
                            else:
                                weathercode = WEATHER_CODES[cleanShortDescription(shortDesc.text)]

                        except Exception as inst:
                            log(str(inst))
                            log("Exception in weathercode")
                            try:
                                weathercode = WEATHER_CODES[cleanShortDescription(shortDesc.text)]
                            except Exception as inst:
                                log(str(inst))
                                log("Exception (2nd) in weathercode")
                                weathercode = 'na'

                        value = '%s.png' % weathercode
                        setKeys(i, ["OutlookIcon", "ConditionIcon"], value)
                        setKeys(i, ["FanartCode"], value.replace(".png", ""))

                # Maximums
                if index == 2:

                    for i, td in enumerate(row.find_all("td")):
                        try:
                            value = '%s' % td.text[:-2]
                            setKeys(i, ["HighTemp", "HighTemperature"], value)
                        except Exception as inst:
                            log(str(inst))
                            log("Exception in HighTemp,HighTemperature")
                            setKeys(i, ["HighTemp", "HighTemperature"], "?")

                            # Minimums
                if index == 3:

                    for i, td in enumerate(row.find_all("td")):
                        try:
                            value = '%s' % td.text[:-2]
                            setKeys(i, ["LowTemp", "LowTemperature"], value)
                        except Exception as inst:
                            log(str(inst))
                            log("Exception in LowTemp,LowTemperature")
                            setKeys(i, ["LowTemp", "LowTemperature"], "?")

                            # Chance of rain
                if index == 4:

                    for i, td in enumerate(row.find_all("td")):
                        try:
                            value = '%s' % td.text[:-1]
                            setKey(i, "ChancePrecipitation", value)
                            setKey(i, "RainChance", value)
                        except Exception as inst:
                            log(str(inst))
                            log("Exception ChancePrecipitation,RainChance")
                            setKey(i, "ChancePrecipitation", "?")
                            setKey(i, "RainChance", "?")

                            # Amount of rain
                if index == 5:

                    for i, td in enumerate(row.find_all("td")):
                        try:
                            value = '%s' % td.text
                            setKey(i, "Precipitation", value)
                            setKey(i, "RainChanceAmount", value)
                        except Exception as inst:
                            log(str(inst))
                            log("Exception in Precipitation,RainChanceAmount")
                            setKey(i, "Precipitation", "?")
                            setKey(i, "RainChanceAmount", "?")
                # UV
                if index == 6:

                    try:
                        tds = row.find_all("td")
                        span = tds[0].find("span")
                        weatherData["Current.UVIndex"] = "%s (%s)" % (span.text, span.get('title'))
                    except Exception as inst:
                        log(str(inst))
                        log("Exception in UVIndex")
                        weatherData["Current.UVIndex"] = "?"

                # Wind speed and direction - there are two values per day here...
                # and, sigh, they can appear as rows 10 and 11 or 9 and 10, depending on if there is a pollen row...

                # Wind Speed
                if index == 9 or 10:

                    try:
                        header = row.find("th")
                        if header is not None and header.text == "Wind Speed":

                            windSpeedData = row.find_all("td")
                            for i in range(0,len(windSpeedData),2):
                                windSpeeds9am.append(windSpeedData[i].text)
                                windSpeeds3pm.append(windSpeedData[i + 1].text)
                    except Exception as inst:
                        log(str(inst))
                        windSpeeds9am.append("?")
                        windSpeeds9am.append("?")

                # # Wind Direction
                if index == 10 or 11:

                    try:
                        header = row.find("th")
                        if header is not None and header.text == "Wind Direction":
                            windDirectionData = row.find_all("td")
                            for i in range(0,len(windDirectionData),2):
                                windDirections9am.append(windDirectionData[i].text.replace("\n",""))
                                windDirections3pm.append(windDirectionData[i+1].text.replace("\n",""))

                    except Exception as inst:
                        log(str(inst))
                        windDirections9am.append("?")
                        windDirections3pm.append("?")

            # Now join the stored wind data and set it...
            for i in range(0,len(windSpeeds9am)):
                # setKey(i, "WindSpeed", "9am - " + windSpeeds9am[i] + ", 3pm - " + windSpeeds3pm[i])
                setKey(i, "WindSpeed", windSpeeds3pm[i])
                # setKey(i, "WindDirection", "9am - " + windDirections9am[i] + ", 3pm - " + windDirections3pm[i])
                setKey(i, "WindDirection", windDirections3pm[i])

        except Exception as inst:
            log("Exception processing forecast rows data from " + SCHEMA + WEATHERZONE_URL + urlPath + "\n" + str(inst))


    return weatherData


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
