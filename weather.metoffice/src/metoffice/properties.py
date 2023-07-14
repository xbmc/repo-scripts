import json
import time
from datetime import timedelta

import pytz

from . import astronomy, urlcache, utilities
from .constants import (
    ADDON_DATA_PATH,
    DAILY_LOCATION_FORECAST_URL,
    DATAPOINT_DATE_FORMAT,
    DATAPOINT_DATETIME_FORMAT,
    FORECAST_LOCATION,
    FORECAST_LOCATION_ID,
    HOURLY_LOCATION_OBSERVATION_URL,
    ISSUEDAT_FORMAT,
    LATITUDE,
    LONGITUDE,
    OBSERVATION_LOCATION,
    OBSERVATION_LOCATION_ID,
    REGIONAL_LOCATION,
    REGIONAL_LOCATION_ID,
    SHORT_DATE_FORMAT,
    SHORT_DAY_FORMAT,
    TEMPERATUREUNITS,
    TEXT_FORECAST_URL,
    THREEHOURLY_LOCATION_FORECAST_URL,
    TIME_FORMAT,
    TZ,
    WEATHER_CODES,
    window,
)


def observation():
    utilities.log(
        "Fetching Hourly Observation for '%s (%s)' from the Met Office..."
        % (OBSERVATION_LOCATION, OBSERVATION_LOCATION_ID)
    )
    with urlcache.URLCache(ADDON_DATA_PATH) as cache:
        filename = cache.get(HOURLY_LOCATION_OBSERVATION_URL, observation_expiry)
        with open(filename) as fh:
            data = json.load(fh)
    try:
        dv = data["SiteRep"]["DV"]
        dataDate = utilities.strptime(
            dv.get("dataDate").rstrip("Z"), DATAPOINT_DATETIME_FORMAT
        ).replace(tzinfo=pytz.utc)
        window().setProperty(
            "HourlyObservation.IssuedAt",
            dataDate.astimezone(TZ).strftime(ISSUEDAT_FORMAT),
        )
        try:
            latest_period = dv["Location"]["Period"][-1]
        except KeyError:
            latest_period = dv["Location"]["Period"]
        try:
            latest_obs = latest_period["Rep"][-1]
        except KeyError:
            latest_obs = latest_period["Rep"]
        window().setProperty(
            "Current.Condition", WEATHER_CODES[latest_obs.get("W", "na")][1]
        )
        window().setProperty("Current.Visibility", latest_obs.get("V", "n/a"))
        window().setProperty("Current.Pressure", latest_obs.get("P", "n/a"))
        window().setProperty(
            "Current.Temperature",
            str(round(float(latest_obs.get("T", "n/a")))).split(".")[0],
        )
        window().setProperty("Current.FeelsLike", "n/a")
        # if we get Wind, then convert it to kmph.
        window().setProperty("Current.Wind", utilities.mph_to_kmph(latest_obs, "S"))
        window().setProperty("Current.WindDirection", latest_obs.get("D", "n/a"))
        window().setProperty("Current.WindGust", latest_obs.get("G", "n/a"))
        window().setProperty(
            "Current.OutlookIcon",
            "%s.png" % WEATHER_CODES[latest_obs.get("W", "na")][0],
        )
        window().setProperty(
            "Current.FanartCode", "%s.png" % WEATHER_CODES[latest_obs.get("W", "na")][0]
        )
        window().setProperty(
            "Current.DewPoint",
            str(round(float(latest_obs.get("Dp", "n/a")))).split(".")[0],
        )
        window().setProperty(
            "Current.Humidity",
            str(round(float(latest_obs.get("H", "n/a")))).split(".")[0],
        )

        window().setProperty("HourlyObservation.IsFetched", "true")

    except KeyError as e:
        e.args = (
            "Key Error in JSON File",
            "Key '{0}' not found while processing file from url:".format(e.args[0]),
            HOURLY_LOCATION_OBSERVATION_URL,
        )
        raise


def daily():
    utilities.log(
        "Fetching Daily Forecast for '%s (%s)' from the Met Office..."
        % (FORECAST_LOCATION, FORECAST_LOCATION_ID)
    )
    with urlcache.URLCache(ADDON_DATA_PATH) as cache:
        filename = cache.get(DAILY_LOCATION_FORECAST_URL, daily_expiry)
        with open(filename) as fh:
            data = json.load(fh)
    try:
        dv = data["SiteRep"]["DV"]
        dataDate = utilities.strptime(
            dv.get("dataDate").rstrip("Z"), DATAPOINT_DATETIME_FORMAT
        ).replace(tzinfo=pytz.utc)
        window().setProperty(
            "DailyForecast.IssuedAt", dataDate.astimezone(TZ).strftime(ISSUEDAT_FORMAT)
        )
        for p, period in enumerate(dv["Location"]["Period"]):
            window().setProperty(
                "Day%d.Title" % p,
                time.strftime(
                    SHORT_DAY_FORMAT,
                    time.strptime(period.get("value"), DATAPOINT_DATE_FORMAT),
                ),
            )
            window().setProperty(
                "Daily.%d.ShortDay" % (p + 1),
                time.strftime(
                    SHORT_DAY_FORMAT,
                    time.strptime(period.get("value"), DATAPOINT_DATE_FORMAT),
                ),
            )
            window().setProperty(
                "Daily.%d.ShortDate" % (p + 1),
                time.strftime(
                    SHORT_DATE_FORMAT,
                    time.strptime(period.get("value"), DATAPOINT_DATE_FORMAT),
                ),
            )
            for rep in period["Rep"]:
                weather_type = rep.get("W", "na")
                if rep.get("$") == "Day":
                    window().setProperty("Day%d.HighTemp" % p, rep.get("Dm", "na"))
                    window().setProperty("Day%d.HighTempIcon" % p, rep.get("Dm"))
                    window().setProperty(
                        "Day%d.Outlook" % p, WEATHER_CODES.get(weather_type)[1]
                    )
                    window().setProperty(
                        "Day%d.OutlookIcon" % p,
                        "%s.png" % WEATHER_CODES.get(weather_type, "na")[0],
                    )
                    window().setProperty("Day%d.WindSpeed" % p, rep.get("S", "na"))
                    window().setProperty(
                        "Day%d.WindDirection" % p, rep.get("D", "na").lower()
                    )

                    # "Extended" properties used by some skins.
                    window().setProperty(
                        "Daily.%d.HighTemperature" % (p + 1),
                        utilities.localised_temperature(rep.get("Dm", "na"))
                        + TEMPERATUREUNITS,
                    )
                    window().setProperty(
                        "Daily.%d.HighTempIcon" % (p + 1), rep.get("Dm")
                    )
                    window().setProperty(
                        "Daily.%d.Outlook" % (p + 1), WEATHER_CODES.get(weather_type)[1]
                    )
                    window().setProperty(
                        "Daily.%d.OutlookIcon" % (p + 1),
                        "%s.png" % WEATHER_CODES.get(weather_type, "na")[0],
                    )
                    window().setProperty(
                        "Daily.%d.FanartCode" % (p + 1),
                        WEATHER_CODES.get(weather_type, "na")[0],
                    )
                    window().setProperty(
                        "Daily.%d.WindSpeed" % (p + 1), rep.get("S", "na")
                    )
                    window().setProperty(
                        "Daily.%d.WindDirection" % (p + 1), rep.get("D", "na").lower()
                    )

                elif rep.get("$") == "Night":
                    window().setProperty("Day%d.LowTemp" % p, rep.get("Nm", "na"))
                    window().setProperty("Day%d.LowTempIcon" % p, rep.get("Nm"))

                    window().setProperty(
                        "Daily.%d.LowTemperature" % (p + 1),
                        utilities.localised_temperature(rep.get("Nm", "na"))
                        + TEMPERATUREUNITS,
                    )
                    window().setProperty(
                        "Daily.%d.LowTempIcon" % (p + 1), rep.get("Nm")
                    )

    except KeyError as e:
        e.args = (
            "Key Error in JSON File",
            "Key '{0}' not found while processing file from url:".format(e.args[0]),
            DAILY_LOCATION_FORECAST_URL,
        )
        raise

    window().setProperty("Daily.IsFetched", "true")


def threehourly():
    utilities.log(
        "Fetching 3 Hourly Forecast for '%s (%s)' from the Met Office..."
        % (FORECAST_LOCATION, FORECAST_LOCATION_ID)
    )
    with urlcache.URLCache(ADDON_DATA_PATH) as cache:
        filename = cache.get(THREEHOURLY_LOCATION_FORECAST_URL, threehourly_expiry)
        with open(filename) as fh:
            data = json.load(fh)
    try:
        dv = data["SiteRep"]["DV"]
        dataDate = utilities.strptime(
            dv.get("dataDate").rstrip("Z"), DATAPOINT_DATETIME_FORMAT
        ).replace(tzinfo=pytz.utc)
        window().setProperty(
            "3HourlyForecast.IssuedAt",
            dataDate.astimezone(TZ).strftime(ISSUEDAT_FORMAT),
        )
        count = 1
        for period in dv["Location"]["Period"]:
            for rep in period["Rep"]:
                # extra xbmc targeted info:
                weather_type = rep.get("W", "na")
                window().setProperty(
                    "Hourly.%d.Outlook" % count, WEATHER_CODES.get(weather_type)[1]
                )
                window().setProperty("Hourly.%d.WindSpeed" % count, rep.get("S", "n/a"))
                window().setProperty(
                    "Hourly.%d.WindDirection" % count, rep.get("D", "na").lower()
                )
                window().setProperty("Hourly.%d.GustSpeed" % count, rep.get("G", "n/a"))
                window().setProperty("Hourly.%d.UVIndex" % count, rep.get("U", "n/a"))
                window().setProperty(
                    "Hourly.%d.Precipitation" % count, rep.get("Pp") + "%"
                )
                window().setProperty(
                    "Hourly.%d.OutlookIcon" % count,
                    "%s.png" % WEATHER_CODES.get(weather_type, "na")[0],
                )
                window().setProperty(
                    "Hourly.%d.ShortDate" % count,
                    time.strftime(
                        SHORT_DATE_FORMAT,
                        time.strptime(period.get("value"), DATAPOINT_DATE_FORMAT),
                    ),
                )
                window().setProperty(
                    "Hourly.%d.Time" % count,
                    utilities.minutes_as_time(int(rep.get("$"))),
                )
                window().setProperty(
                    "Hourly.%d.Temperature" % count,
                    utilities.rownd(utilities.localised_temperature(rep.get("T", "na")))
                    + TEMPERATUREUNITS,
                )
                window().setProperty(
                    "Hourly.%d.ActualTempIcon" % count, rep.get("T", "na")
                )
                window().setProperty(
                    "Hourly.%d.FeelsLikeTemp" % count,
                    utilities.rownd(
                        utilities.localised_temperature(rep.get("F", "na"))
                    ),
                )
                window().setProperty(
                    "Hourly.%d.FeelsLikeTempIcon" % count, rep.get("F", "na")
                )
                count += 1
    except KeyError as e:
        e.args = (
            "Key Error in JSON File",
            "Key '{0}' not found while processing file from url:".format(e.args[0]),
            THREEHOURLY_LOCATION_FORECAST_URL,
        )
        raise
    window().setProperty("Hourly.IsFetched", "true")


def sunrisesunset():
    sun = astronomy.Sun(lat=float(LATITUDE), lng=float(LONGITUDE))
    window().setProperty("Today.Sunrise", sun.sunrise().strftime(TIME_FORMAT))
    window().setProperty("Today.Sunset", sun.sunset().strftime(TIME_FORMAT))


def text():
    utilities.log(
        "Fetching Text Forecast for '%s (%s)' from the Met Office..."
        % (REGIONAL_LOCATION, REGIONAL_LOCATION_ID)
    )
    with urlcache.URLCache(ADDON_DATA_PATH) as cache:
        filename = cache.get(TEXT_FORECAST_URL, text_expiry)
        with open(filename) as fh:
            data = json.load(fh)
    try:
        rf = data["RegionalFcst"]
        issuedat = utilities.strptime(
            rf["issuedAt"].rstrip("Z"), DATAPOINT_DATETIME_FORMAT
        ).replace(tzinfo=pytz.utc)
        window().setProperty(
            "TextForecast.IssuedAt", issuedat.astimezone(TZ).strftime(ISSUEDAT_FORMAT)
        )
        count = 0
        for period in rf["FcstPeriods"]["Period"]:
            # have to check type because json can return list or dict here
            if isinstance(period["Paragraph"], list):
                for paragraph in period["Paragraph"]:
                    window().setProperty(
                        "Text.Paragraph%d.Title" % count,
                        paragraph["title"].rstrip(":").lstrip("UK Outlook for"),
                    )
                    window().setProperty(
                        "Text.Paragraph%d.Content" % count, paragraph["$"]
                    )
                    count += 1
            else:
                window().setProperty(
                    "Text.Paragraph%d.Title" % count,
                    period["Paragraph"]["title"].rstrip(":").lstrip("UK Outlook for"),
                )

                window().setProperty(
                    "Text.Paragraph%d.Content" % count, period["Paragraph"]["$"]
                )
                count += 1
    except KeyError as e:
        e.args = (
            "Key Error in JSON File",
            "Key '{0}' not found while processing file from url:".format(e.args[0]),
            TEXT_FORECAST_URL,
        )
        raise
    window().setProperty("TextForecast.IsFetched", "true")


def daily_expiry(filename):
    with open(filename) as fh:
        data = json.load(fh)
    dataDate = data["SiteRep"]["DV"]["dataDate"].rstrip("Z")
    return utilities.strptime(dataDate, DATAPOINT_DATETIME_FORMAT) + timedelta(
        hours=1.5
    )


def threehourly_expiry(filename):
    with open(filename) as fh:
        data = json.load(fh)
    dataDate = data["SiteRep"]["DV"]["dataDate"].rstrip("Z")
    return utilities.strptime(dataDate, DATAPOINT_DATETIME_FORMAT) + timedelta(
        hours=1.5
    )


def text_expiry(filename):
    with open(filename) as fh:
        data = json.load(fh)
    issuedAt = data["RegionalFcst"]["issuedAt"].rstrip("Z")
    return utilities.strptime(issuedAt, DATAPOINT_DATETIME_FORMAT) + timedelta(hours=12)


def observation_expiry(filename):
    with open(filename) as fh:
        data = json.load(fh)
    dataDate = data["SiteRep"]["DV"]["dataDate"].rstrip("Z")
    return utilities.strptime(dataDate, DATAPOINT_DATETIME_FORMAT) + timedelta(
        hours=1.5
    )
