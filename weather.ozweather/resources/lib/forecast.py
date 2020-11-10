import xbmc
import xbmcvfs
import xbmcgui

from resources.lib.common import *
from resources.lib.locations import *
from resources.lib.weatherzone import *
from resources.lib.abcvideo import *
from resources.lib.bom import *


def clear_properties():
    """
    Clear all properties on the weather window in preparation for an update.
    """
    log("Clearing all weather window properties")
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


def forecast(urlPath, radarCode):
    """
    The main forecast retrieval function
    Does either a basic forecast or a more extended forecast with radar etc.
    :param urlPath: the WeatherZone URL path (e.g. '/vic/melbourne/ascot-vale') for the location we're to get the forecast for
    :param radarCode: the BOM radar code (e.g. 'IDR063') to retrieve the radar loop for
    """
    extended_features = ADDON.getSetting('ExtendedFeaturesToggle')

    log("Getting weather from [%s] with radar [%s], extended features is: [%s]" % (
        urlPath, radarCode, str(extended_features)))

    # Get the radar images first - looks better on refreshes
    if extended_features == "true":
        log("Getting radar images for " + radarCode)

        backgroundsPath = xbmcvfs.translatePath(
            "special://profile/addon_data/weather.ozweather/radarbackgrounds/" + radarCode + "/");
        overlayLoopPath = xbmcvfs.translatePath(
            "special://profile/addon_data/weather.ozweather/currentloop/" + radarCode + "/");

        updateRadarBackgrounds = ADDON.getSetting('BGDownloadToggle')

        buildImages(radarCode, updateRadarBackgrounds, backgroundsPath, overlayLoopPath)
        set_property(WEATHER_WINDOW, 'Radar', radarCode)

    # Get all the weather & forecast data from weatherzone
    log("Getting the forecast data from https://weatherzone.com.au" + urlPath)
    weather_data = getWeatherData(urlPath)

    for weather_key in sorted(weather_data):
        set_property(WEATHER_WINDOW, weather_key, weather_data[weather_key])

    # Get the ABC video link
    if extended_features == "true":
        log("Getting the ABC weather video link")
        url = getABCWeatherVideoLink(ADDON.getSetting("ABCQuality"))
        if url:
            set_property(WEATHER_WINDOW, 'Video.1', url)

    # And announce everything is fetched..
    set_property(WEATHER_WINDOW, "Weather.IsFetched", "true")
    set_property(WEATHER_WINDOW, 'Forecast.Updated', time.strftime("%d/%m/%Y %H:%M"))
    set_property(WEATHER_WINDOW, 'Today.IsFetched', "true")


def get_forecast():
    """
    Get the latest forecast data for the currently chosen location
    """

    # Nice neat updates - clear out all set window data first...
    clear_properties()

    # Set basic properties/'brand'
    set_property(WEATHER_WINDOW, 'WeatherProviderLogo', xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'banner.png')))
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
    location_url_path = ADDON.getSetting('Location%sUrlPath' % sys.argv[1])

    # Old style paths (pre v0.8.5) must be updated to new
    if not location_url_path:
        location_url_path = ADDON.getSetting('Location%sid' % sys.argv[1])
        location_url_path = location_url_path.replace('http://www.weatherzone.com.au', '')
        ADDON.setSetting('Location%sUrlPath' % sys.argv[1], location_url_path)

    radar = ADDON.getSetting('Radar%s' % sys.argv[1])
    # If we don't have a radar code, get the national radar by default
    if radar == '':
        log(
            f'Radar code empty for location {location_url_path} so using default radar code IDR00004 (national radar)')
        radar = 'IDR00004'

    # Now scrape the weather data & radar images
    forecast(location_url_path, radar)
