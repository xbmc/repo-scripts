# -*- coding: utf-8 -*-

import xbmcgui
import socket

from .common import *
from .weatherzone import *
from .abcvideo import *
from .bom import *

WEATHER_WINDOW = xbmcgui.Window(12600)


def run(args):
    """
    This is 'main' basically.
    TWO MAJOR MODES - SETTINGS and FORECAST RETRIEVAL

    @param args: sys.argv is passed through to here...
    """

    footprints()
    socket.setdefaulttimeout(100)

    # SETTINGS
    # the addon is being called from the settings section where the user enters their postcodes
    if args[1].startswith('Location'):
        find_location()

    # FORECAST
    # script is being called in general use, not from the settings page
    # sys.argv[1] has the current location number, so get the currently selected location and grab it's forecast
    else:
        get_forecast()

    # Refresh the locations
    refresh_locations()

    # and close out...
    footprints(startup=False)


def clear_properties():
    """
    Clear all properties on the weather window in preparation for an update.
    """
    log("Clearing Properties")
    try:
        set_property(WEATHER_WINDOW, 'WeatherProviderLogo')
        set_property(WEATHER_WINDOW, 'WeatherProvider')
        set_property(WEATHER_WINDOW, 'WeatherVersion')
        set_property(WEATHER_WINDOW, 'Location')
        set_property(WEATHER_WINDOW, 'Updated')
        set_property(WEATHER_WINDOW, 'Weather.IsFetched', "false")
        set_property(WEATHER_WINDOW, 'Daily.IsFetched', "false")
        set_property(WEATHER_WINDOW, 'Radar')
        set_property(WEATHER_WINDOW, 'Video.1')

        set_property(WEATHER_WINDOW, 'Forecast.City')
        set_property(WEATHER_WINDOW, 'Forecast.Country')
        set_property(WEATHER_WINDOW, 'Forecast.Updated')

        set_property(WEATHER_WINDOW, 'Current.IsFetched', "false")
        set_property(WEATHER_WINDOW, 'Current.Location')
        set_property(WEATHER_WINDOW, 'Current.Condition')
        set_property(WEATHER_WINDOW, 'Current.ConditionLong')
        set_property(WEATHER_WINDOW, 'Current.Temperature')
        set_property(WEATHER_WINDOW, 'Current.Wind')
        set_property(WEATHER_WINDOW, 'Current.WindDirection')
        set_property(WEATHER_WINDOW, 'Current.WindDegree')
        set_property(WEATHER_WINDOW, 'Current.WindGust')
        set_property(WEATHER_WINDOW, 'Current.Pressure')
        set_property(WEATHER_WINDOW, 'Current.FireDanger')
        set_property(WEATHER_WINDOW, 'Current.FireDangerText')
        set_property(WEATHER_WINDOW, 'Current.Visibility')
        set_property(WEATHER_WINDOW, 'Current.Humidity')
        set_property(WEATHER_WINDOW, 'Current.FeelsLike')
        set_property(WEATHER_WINDOW, 'Current.DewPoint')
        set_property(WEATHER_WINDOW, 'Current.UVIndex')
        set_property(WEATHER_WINDOW, 'Current.OutlookIcon', "na.png")
        set_property(WEATHER_WINDOW, 'Current.ConditionIcon', "na.png")
        set_property(WEATHER_WINDOW, 'Current.FanartCode')
        set_property(WEATHER_WINDOW, 'Current.Sunrise')
        set_property(WEATHER_WINDOW, 'Current.Sunset')
        set_property(WEATHER_WINDOW, 'Current.RainSince9')
        set_property(WEATHER_WINDOW, 'Current.RainLastHr')
        set_property(WEATHER_WINDOW, 'Current.Precipitation')
        set_property(WEATHER_WINDOW, 'Current.ChancePrecipitation')
        set_property(WEATHER_WINDOW, 'Current.SolarRadiation')

        set_property(WEATHER_WINDOW, 'Today.IsFetched', "false")
        set_property(WEATHER_WINDOW, 'Today.Sunrise')
        set_property(WEATHER_WINDOW, 'Today.Sunset')
        set_property(WEATHER_WINDOW, 'Today.moonphase')
        set_property(WEATHER_WINDOW, 'Today.Moonphase')

        # and all the properties for the forecast
        for count in range(0, 14):
            set_property(WEATHER_WINDOW, 'Day%i.Title' % count)
            set_property(WEATHER_WINDOW, 'Day%i.RainChance' % count)
            set_property(WEATHER_WINDOW, 'Day%i.RainChanceAmount' % count)
            set_property(WEATHER_WINDOW, 'Day%i.ChancePrecipitation' % count)
            set_property(WEATHER_WINDOW, 'Day%i.Precipitation' % count)
            set_property(WEATHER_WINDOW, 'Day%i.HighTemp' % count)
            set_property(WEATHER_WINDOW, 'Day%i.LowTemp' % count)
            set_property(WEATHER_WINDOW, 'Day%i.HighTemperature' % count)
            set_property(WEATHER_WINDOW, 'Day%i.LowTemperature' % count)
            set_property(WEATHER_WINDOW, 'Day%i.Outlook' % count)
            set_property(WEATHER_WINDOW, 'Day%i.LongOutlookDay' % count)
            set_property(WEATHER_WINDOW, 'Day%i.OutlookIcon' % count, "na.png")
            set_property(WEATHER_WINDOW, 'Day%i.ConditionIcon' % count, "na.png")
            set_property(WEATHER_WINDOW, 'Day%i.FanartCode' % count)
            set_property(WEATHER_WINDOW, 'Day%i.ShortDate' % count)
            set_property(WEATHER_WINDOW, 'Day%i.ShortDay' % count)

            set_property(WEATHER_WINDOW, 'Daily.%i.Title' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.RainChance' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.RainChanceAmount' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.ChancePrecipitation' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.Precipitation' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.HighTemp' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.LowTemp' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.HighTemperature' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.LowTemperature' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.Outlook' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.LongOutlookDay' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.OutlookIcon' % count, "na.png")
            set_property(WEATHER_WINDOW, 'Daily.%i.ConditionIcon' % count, "na.png")
            set_property(WEATHER_WINDOW, 'Daily.%i.FanartCode' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.ShortDate' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.ShortDay' % count)

    except Exception as inst:
        log("********** Oz Weather Couldn't clear all the properties, sorry!!", inst)


def refresh_locations():
    """
    Set the location and radar code properties
    """
    log("Refreshing locations from settings")
    location_set1 = ADDON.getSetting('Location1')
    location_set2 = ADDON.getSetting('Location2')
    location_set3 = ADDON.getSetting('Location3')
    locations = 0
    if location_set1 != '':
        locations += 1
        set_property(WEATHER_WINDOW, 'Location1', location_set1)
    else:
        set_property(WEATHER_WINDOW, 'Location1')
    if location_set2 != '':
        locations += 1
        set_property(WEATHER_WINDOW, 'Location2', location_set2)
    else:
        set_property(WEATHER_WINDOW, 'Location2')
    if location_set3 != '':
        locations += 1
        set_property(WEATHER_WINDOW, 'Location3', location_set3)
    else:
        set_property(WEATHER_WINDOW, 'Location3')

    set_property(WEATHER_WINDOW, 'Locations', str(locations))

    log("Refreshing radar locations from settings")
    radar_set1 = ADDON.getSetting('Radar1')
    radar_set2 = ADDON.getSetting('Radar2')
    radar_set3 = ADDON.getSetting('Radar3')
    radars = 0
    if radar_set1 != '':
        radars += 1
        set_property(WEATHER_WINDOW, 'Radar1', radar_set1)
    else:
        set_property(WEATHER_WINDOW, 'Radar1')
    if radar_set2 != '':
        radars += 1
        set_property(WEATHER_WINDOW, 'Radar2', radar_set2)
    else:
        set_property(WEATHER_WINDOW, 'Radar2')
    if radar_set3 != '':
        radars += 1
        set_property(WEATHER_WINDOW, 'Radar3', radar_set3)
    else:
        set_property(WEATHER_WINDOW, 'Radar3')

    set_property(WEATHER_WINDOW, 'Radars', str(locations))


def forecast(urlPath, radarCode):
    """
    The main forecast retrieval function
    Does either a basic forecast or a more extended forecast with radar etc.

    @param urlPath: the WeatherZone url path, e.g. sa/adelaide/myrtle-bank
    @param radarCode: the full radar code e.g. IDR035
    """
    extended_features = ADDON.getSetting('ExtendedFeaturesToggle')

    log("Getting weather from [%s] with radar [%s], extended features is: [%s]" % (
        urlPath, radarCode, str(extended_features)))

    # Get the radar images first - looks better on refreshes
    if extended_features == "true":
        log("Getting radar images for " + radarCode)

        backgroundsPath = xbmc.translatePath(
            "special://profile/addon_data/weather.ozweather/radarbackgrounds/" + radarCode + "/");
        overlayLoopPath = xbmc.translatePath(
            "special://profile/addon_data/weather.ozweather/currentloop/" + radarCode + "/");

        updateRadarBackgrounds = ADDON.getSetting('BGDownloadToggle')

        buildImages(radarCode, updateRadarBackgrounds, backgroundsPath, overlayLoopPath)
        set_property(WEATHER_WINDOW, 'Radar', radarCode)

    # Get all the weather & forecast data from weatherzone
    log("Get the forecast data from http://weatherzone.com.au" + urlPath)
    weather_data = getWeatherData(urlPath)

    for weather_key in sorted(weather_data):
        set_property(WEATHER_WINDOW, weather_key, weather_data[weather_key])

    # Get the ABC video link
    if extended_features == "true":
        log("Get the ABC weather video link")
        url = getABCWeatherVideoLink(ADDON.getSetting("ABCQuality"))
        if url:
            set_property(WEATHER_WINDOW, 'Video.1', url)

    # And announce everything is fetched..
    set_property(WEATHER_WINDOW, "Weather.IsFetched", "true")
    set_property(WEATHER_WINDOW, 'Forecast.Updated', time.strftime("%d/%m/%Y %H:%M"))
    set_property(WEATHER_WINDOW, 'Today.IsFetched', "true")


def find_location():
    """
    Search WeatherZone for locations matching the given postcode or suburb
    """
    keyboard = xbmc.Keyboard('', LANGUAGE(32195), False)
    keyboard.doModal()

    if keyboard.isConfirmed() and keyboard.getText() != '':
        text = keyboard.getText()

        log("Doing locations search for " + text)
        locations, location_url_paths = getLocationsForPostcodeOrSuburb(text)

        # Now get them to choose an actual location
        dialog = xbmcgui.Dialog()
        if locations:
            selected = dialog.select(xbmc.getLocalizedString(396), locations)
            if selected != -1:
                ADDON.setSetting(sys.argv[1], locations[selected])
                ADDON.setSetting(sys.argv[1] + 'UrlPath', location_url_paths[selected])
        # Or indicate we did not receive any locations
        else:
            dialog.ok(ADDON_NAME, xbmc.getLocalizedString(284))


def get_forecast():
    """
    Get the forecast from BOM via WeatherZone...
    """
    # Nice neat updates - clear out all set window data first...
    clear_properties()

    # Set basic properties/brand
    set_property(WEATHER_WINDOW, 'WeatherProviderLogo', xbmc.translatePath(os.path.join(CWD, 'resources', 'banner.png')))
    set_property(WEATHER_WINDOW, 'WeatherProvider', 'Bureau of Meteorology Australia (via WeatherZone)')
    set_property(WEATHER_WINDOW, 'WeatherVersion', ADDON_NAME + "-" + ADDON_VERSION)

    # Set what we updated and when
    set_property(WEATHER_WINDOW, 'Location', ADDON.getSetting('Location%s' % sys.argv[1]))
    set_property(WEATHER_WINDOW, 'Updated', time.strftime("%d/%m/%Y %H:%M"))
    set_property(WEATHER_WINDOW, 'Current.Location', ADDON.getSetting('Location%s' % sys.argv[1]))
    set_property(WEATHER_WINDOW, 'Forecast.City', ADDON.getSetting('Location%s' % sys.argv[1]))
    set_property(WEATHER_WINDOW, 'Forecast.Country', "Australia")
    set_property(WEATHER_WINDOW, 'Forecast.Updated', time.strftime("%d/%m/%Y %H:%M"))

    # Retrieve the currently chosen location & radar
    location_url_path = ''
    location_url_path = ADDON.getSetting('Location%sUrlPath' % sys.argv[1])

    # Old style paths (pre v0.8.5) must be updated to new
    if not location_url_path:
        location_url_path = ADDON.getSetting('Location%sid' % sys.argv[1])
        location_url_path = location_url_path.replace('http://www.weatherzone.com.au', '')
        ADDON.setSetting('Location%sUrlPath' % sys.argv[1], location_url_path)

    radar = ''
    radar = ADDON.getSetting('Radar%s' % sys.argv[1])
    # If we don't have a radar code, get the national radar by default
    if radar == '':
        log(
            f'Radar code empty for location {location_url_path} so using default radar code IDR00004 (national radar)')
        radar = 'IDR00004'

    # Now scrape the weather data & radar images
    forecast(location_url_path, radar)
