import os
import glob
import time
import sys
import shutil

import xbmc
import xbmcvfs

from bossanova808.constants import ADDON, ADDON_NAME, ADDON_VERSION, WEATHER_WINDOW, CWD
from bossanova808.utilities import set_property, clear_property
from bossanova808.logger import Logger

# noinspection PyPackages
from .abc.abc_video import get_abc_weather_video_link
# noinspection PyPackages
from .bom.bom_radar import build_images
# noinspection PyPackages
from .bom.bom_forecast import bom_forecast, utc_str_to_local_str


def clear_properties():
    """
    Clear all properties on the weather window in preparation for an update.
    """
    Logger.info("Clearing all weather window properties")
    try:
        clear_property(WEATHER_WINDOW, 'Weather.IsFetched')
        clear_property(WEATHER_WINDOW, 'Daily.IsFetched')

        clear_property(WEATHER_WINDOW, 'WeatherProviderLogo')
        clear_property(WEATHER_WINDOW, 'WeatherProvider')
        clear_property(WEATHER_WINDOW, 'WeatherVersion')
        clear_property(WEATHER_WINDOW, 'Location')
        clear_property(WEATHER_WINDOW, 'Updated')
        clear_property(WEATHER_WINDOW, 'Radar')
        clear_property(WEATHER_WINDOW, 'RadarOldest')
        clear_property(WEATHER_WINDOW, 'RadarNewest')
        clear_property(WEATHER_WINDOW, 'Video.1')

        clear_property(WEATHER_WINDOW, 'Forecast.City')
        clear_property(WEATHER_WINDOW, 'Forecast.Country')
        clear_property(WEATHER_WINDOW, 'Forecast.Latitude')
        clear_property(WEATHER_WINDOW, 'Forecast.Longitude')
        clear_property(WEATHER_WINDOW, 'Forecast.Updated')

        clear_property(WEATHER_WINDOW, 'ForecastUpdated')
        clear_property(WEATHER_WINDOW, 'ForecastRegion')
        clear_property(WEATHER_WINDOW, 'ForecastType')
        clear_property(WEATHER_WINDOW, 'ObservationsUpdated')

        clear_property(WEATHER_WINDOW, 'Current.IsFetched')
        clear_property(WEATHER_WINDOW, 'Current.Location')
        clear_property(WEATHER_WINDOW, 'Current.Condition')
        clear_property(WEATHER_WINDOW, 'Current.ConditionLong')
        clear_property(WEATHER_WINDOW, 'Current.Temperature')
        clear_property(WEATHER_WINDOW, 'Current.Ozw_Temperature')
        clear_property(WEATHER_WINDOW, 'Current.Wind')
        clear_property(WEATHER_WINDOW, 'Current.WindSpeed')
        clear_property(WEATHER_WINDOW, 'Current.Ozw_WindSpeed')
        clear_property(WEATHER_WINDOW, 'Current.WindDirection')
        clear_property(WEATHER_WINDOW, 'Current.WindDegree')
        clear_property(WEATHER_WINDOW, 'Current.WindGust')
        clear_property(WEATHER_WINDOW, 'Current.Pressure')
        clear_property(WEATHER_WINDOW, 'Current.FireDanger')
        clear_property(WEATHER_WINDOW, 'Current.FireDangerText')
        clear_property(WEATHER_WINDOW, 'Current.Visibility')
        clear_property(WEATHER_WINDOW, 'Current.Humidity')
        clear_property(WEATHER_WINDOW, 'Current.Ozw_Humidity')
        clear_property(WEATHER_WINDOW, 'Current.FeelsLike')
        clear_property(WEATHER_WINDOW, 'Current.Ozw_FeelsLike')
        clear_property(WEATHER_WINDOW, 'Current.DewPoint')
        clear_property(WEATHER_WINDOW, 'Current.UVIndex')
        clear_property(WEATHER_WINDOW, 'Current.OutlookIcon')
        clear_property(WEATHER_WINDOW, 'Current.ConditionIcon')
        clear_property(WEATHER_WINDOW, 'Current.FanartCode')
        clear_property(WEATHER_WINDOW, 'Current.Sunrise')
        clear_property(WEATHER_WINDOW, 'Current.Sunset')
        clear_property(WEATHER_WINDOW, 'Current.RainSince9')
        clear_property(WEATHER_WINDOW, 'Current.RainLastHr')
        clear_property(WEATHER_WINDOW, 'Current.Precipitation')
        clear_property(WEATHER_WINDOW, 'Current.ChancePrecipitation')
        clear_property(WEATHER_WINDOW, 'Current.SolarRadiation')
        clear_property(WEATHER_WINDOW, 'Current.NowLabel')
        clear_property(WEATHER_WINDOW, 'Current.NowValue')
        clear_property(WEATHER_WINDOW, 'Current.LaterLabel')
        clear_property(WEATHER_WINDOW, 'Current.LaterValue')

        clear_property(WEATHER_WINDOW, 'Today.IsFetched')
        clear_property(WEATHER_WINDOW, 'Today.Sunrise')
        clear_property(WEATHER_WINDOW, 'Today.Sunset')
        clear_property(WEATHER_WINDOW, 'Today.moonphase')
        clear_property(WEATHER_WINDOW, 'Today.Moonphase')

        # and all the properties for the forecast
        for count in range(0, 8):
            clear_property(WEATHER_WINDOW, 'Day%i.Title' % count)
            clear_property(WEATHER_WINDOW, 'Day%i.RainChance' % count)
            clear_property(WEATHER_WINDOW, 'Day%i.RainChanceAmount' % count)
            clear_property(WEATHER_WINDOW, 'Day%i.ChancePrecipitation' % count)
            clear_property(WEATHER_WINDOW, 'Day%i.Precipitation' % count)
            clear_property(WEATHER_WINDOW, 'Day%i.HighTemp' % count)
            clear_property(WEATHER_WINDOW, 'Day%i.LowTemp' % count)
            clear_property(WEATHER_WINDOW, 'Day%i.HighTemperature' % count)
            clear_property(WEATHER_WINDOW, 'Day%i.LowTemperature' % count)
            clear_property(WEATHER_WINDOW, 'Day%i.Outlook' % count)
            clear_property(WEATHER_WINDOW, 'Day%i.LongOutlookDay' % count)
            clear_property(WEATHER_WINDOW, 'Day%i.OutlookIcon' % count)
            clear_property(WEATHER_WINDOW, 'Day%i.ConditionIcon' % count)
            clear_property(WEATHER_WINDOW, 'Day%i.FanartCode' % count)
            clear_property(WEATHER_WINDOW, 'Day%i.ShortDate' % count)
            clear_property(WEATHER_WINDOW, 'Day%i.ShortDay' % count)

            clear_property(WEATHER_WINDOW, 'Daily.%i.Title' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.RainChance' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.RainChanceAmount' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.RainAmount' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.ChancePrecipitation' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.Precipitation' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.HighTemp' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.LowTemp' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.HighTemperature' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.LowTemperature' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.Outlook' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.LongOutlookDay' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.OutlookIcon' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.ConditionIcon' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.FanartCode' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.ShortDate' % count)
            clear_property(WEATHER_WINDOW, 'Daily.%i.ShortDay' % count)

    except Exception:
        Logger.error("********** Oz Weather Couldn't clear all the properties, sorry!!")


# noinspection PyShadowingNames
def forecast(geohash, radar_code):
    """
    Retrieve forecast data from the BOM and populate Kodi weather window properties.
    
    Performs an optional extended update: may purge stored radar backgrounds, build radar background and loop images for the supplied radar code, set loop time labels from generated image filenames, fetch an ABC weather video link, and write all retrieved weather and status properties to the weather window (including fetch flags and update timestamp).
    
    Parameters:
        geohash (str): BOM geohash for the location.
        radar_code (str): BOM radar code (e.g. 'IDR063') used to build radar backgrounds and loop images.
    """

    extended_features = ADDON.getSettingBool('ExtendedFeaturesToggle')
    Logger.debug(f'Extended features: {extended_features}')

    # Has the user requested we refresh the radar data on next weather fetch?
    purge_radar_backgrounds = ADDON.getSettingBool('PurgeRadarBackgroundsOnNextRefresh')
    if purge_radar_backgrounds:
        Logger.info("Purging all radar background per user request")
        if os.path.isdir(xbmcvfs.translatePath("special://temp/ozweather/backgrounds")):
            shutil.rmtree(xbmcvfs.translatePath("special://temp/ozweather/backgrounds"))
            # Little pause to make sure this is complete before any weather refresh...
            time.sleep(0.5)
        ADDON.setSetting('PurgeRadarBackgroundsOnNextRefresh', 'false')

    # Get the radar images first - because it looks better on refreshes
    if extended_features:
        Logger.debug(f'Getting radar images for {radar_code}')
        # Use cache for all radar data (backgrounds and current loop images)
        # Kodi does not routinely clear this on exit (so the backgrounds are conserved as desired)
        # OzWeather takes care of deleting the ephemeral (loop) images as needed
        # Seems the best place, see: https://forum.kodi.tv/showthread.php?tid=382805
        # (If the cache is cleared at any point, OzWeather will then re-download what it needs).
        backgrounds_path = xbmcvfs.translatePath(f"special://temp/ozweather/backgrounds/{radar_code}/")
        overlay_loop_path = xbmcvfs.translatePath(f"special://temp/ozweather/loop/{radar_code}/")
        build_images(radar_code, backgrounds_path, overlay_loop_path)
        set_property(WEATHER_WINDOW, 'Radar', radar_code)

        # Finally, set some labels, so we can see the time period the loop covers
        list_of_loop_files = list(filter(os.path.isfile, glob.glob(overlay_loop_path + "*")))
        list_of_loop_files.sort(key=lambda x: os.path.getmtime(x))

        if list_of_loop_files:
            oldest_file = list_of_loop_files[0]
            newest_file = list_of_loop_files[-1]
            # utc - get from filename of oldest and newest - it's the last number before the .png
            utc_oldest = oldest_file.split('.')[-2]
            utc_newest = newest_file.split('.')[-2]
            Logger.debug(f"utc_oldest {utc_oldest}")
            Logger.debug(f"utc_newest {utc_newest}")

            time_oldest = utc_str_to_local_str(utc_oldest, "%Y%m%d%H%M")
            time_newest = utc_str_to_local_str(utc_newest, "%Y%m%d%H%M")

            set_property(WEATHER_WINDOW, 'RadarOldest', time_oldest)
            set_property(WEATHER_WINDOW, 'RadarNewest', time_newest)

    # Get all the weather & forecast data from the BOM API
    weather_data = None

    if geohash:
        Logger.info(f'Using the BOM API.  Getting weather data for {geohash}')
        weather_data = bom_forecast(geohash)

    # At this point, we should have _something_ - if not, log the issue, and we're done...
    if not weather_data:
        Logger.error("Unable to get weather_data from BOM - internet connection issue or addon not configured?")
        return

    # We have weather_data - set all the properties on Kodi's weather window...
    for weather_key in sorted(weather_data):
        set_property(WEATHER_WINDOW, weather_key, weather_data[weather_key])

    # Get the ABC 90-second weather video link if extended features is enabled
    if extended_features:
        Logger.info("Getting the ABC weather video link")
        url = get_abc_weather_video_link()
        if url:
            set_property(WEATHER_WINDOW, 'Video.1', url)

    # And announce everything is fetched...
    set_property(WEATHER_WINDOW, "Weather.IsFetched", "true")
    set_property(WEATHER_WINDOW, "Daily.IsFetched", "true")
    set_property(WEATHER_WINDOW, "Today.IsFetched", "true")
    set_property(WEATHER_WINDOW, 'Forecast.Updated', time.strftime("%d/%m/%Y %H:%M"))


# noinspection PyShadowingNames
def get_weather():
    """
    Gets the latest observations, forecast and radar images for the currently chosen location
    """

    Logger.info("*** Updating Weather Data ***")

    # Nice neat updates - clear out all set window data first...
    clear_properties()

    # This is/was an attempt to use conditions in skins to basically auto-adapt the MyWeather.xml and all OzWeather
    # components to the currently-in-use skin.  However, no matter what I try I can't get the conditions to work
    # in the skin files.  This is still used by my OzWeather Skin Patcher addon, however, so left here.
    # noinspection PyBroadException
    try:
        skin_in_use = xbmc.getSkinDir().split('.')[1]
        set_property(WEATHER_WINDOW, 'SkinInUse', skin_in_use)
    except IndexError:
        pass

    # Retrieve the currently chosen location geohash & radar code
    geohash = ADDON.getSetting(f'Location{sys.argv[1]}BOMGeoHash')
    radar = ADDON.getSetting(f'Radar{sys.argv[1]}') or ADDON.getSetting(f'Location{sys.argv[1]}ClosestRadar')

    # With the new closest radar system, the radar is stored as e.g. 'Melbourne - IDR023' so strip the name off...
    split_code = radar.split(' - ')
    if len(split_code) > 1:
        Logger.warning(f"Radar code: transforming [{radar}] to: [{split_code[-1]}]")
        radar = split_code[-1]

    if not geohash:
        Logger.error("No BOM location geohash - can't retrieve weather data!")
        return

    # If we don't have a radar code, get the national radar by default
    if not radar:
        radar = 'IDR00004'
        Logger.warning(f'Radar code empty for location, so using default radar code {radar} (= national radar)')

    Logger.info(f'Current location: BOM geohash "{geohash}", radar code {radar}')

    # Now scrape the weather data & radar images
    forecast(geohash, radar)

    # Set basic properties/'brand'
    set_property(WEATHER_WINDOW, 'WeatherProviderLogo', xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'banner.png')))
    set_property(WEATHER_WINDOW, 'WeatherProvider', 'Bureau of Meteorology Australia')
    set_property(WEATHER_WINDOW, 'WeatherVersion', ADDON_NAME + "-" + ADDON_VERSION)

    # Set the location we updated
    location_in_use = ADDON.getSetting(f'Location{sys.argv[1]}BOM')
    latitude = ADDON.getSetting(f'Location{sys.argv[1]}Lat')
    longitude = ADDON.getSetting(f'Location{sys.argv[1]}Lon')
    try:
        location_in_use = location_in_use[0:location_in_use.index(',')]
    except ValueError:
        pass

    set_property(WEATHER_WINDOW, 'Location', location_in_use)
    set_property(WEATHER_WINDOW, 'Updated', time.strftime("%d/%m %H:%M").lower())
    set_property(WEATHER_WINDOW, 'Current.Location', location_in_use)
    set_property(WEATHER_WINDOW, 'Forecast.City', location_in_use)
    set_property(WEATHER_WINDOW, 'Forecast.Country', "Australia")
    set_property(WEATHER_WINDOW, 'Forecast.Latitude', latitude)
    set_property(WEATHER_WINDOW, 'Forecast.Longitude', longitude)
    time_updated = time.strftime("%d/%m @ %H:%M").lower()
    set_property(WEATHER_WINDOW, 'Forecast.Updated', time_updated)
    set_property(WEATHER_WINDOW, 'LastUpdated', time_updated)
