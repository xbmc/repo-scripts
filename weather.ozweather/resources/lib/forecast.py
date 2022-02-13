import xbmcplugin

from .abc.abc_video import *
from .bom.bom_radar import *
from .bom.bom_forecast import *
from pathlib import Path


def clear_properties():
    """
    Clear all properties on the weather window in preparation for an update.
    """
    log("Clearing all weather window properties")
    try:
        set_property(WEATHER_WINDOW, 'Weather.IsFetched')
        set_property(WEATHER_WINDOW, 'Daily.IsFetched')

        set_property(WEATHER_WINDOW, 'WeatherProviderLogo')
        set_property(WEATHER_WINDOW, 'WeatherProvider')
        set_property(WEATHER_WINDOW, 'WeatherVersion')
        set_property(WEATHER_WINDOW, 'Location')
        set_property(WEATHER_WINDOW, 'Updated')
        set_property(WEATHER_WINDOW, 'Radar')
        set_property(WEATHER_WINDOW, 'RadarOldest')
        set_property(WEATHER_WINDOW, 'RadarNewest')
        set_property(WEATHER_WINDOW, 'Video.1')

        set_property(WEATHER_WINDOW, 'Forecast.City')
        set_property(WEATHER_WINDOW, 'Forecast.Country')
        set_property(WEATHER_WINDOW, 'Forecast.Updated')

        set_property(WEATHER_WINDOW, 'ForecastUpdated')
        set_property(WEATHER_WINDOW, 'ForecastRegion')
        set_property(WEATHER_WINDOW, 'ForecastType')
        set_property(WEATHER_WINDOW, 'ObservationsUpdated')

        set_property(WEATHER_WINDOW, 'Current.IsFetched')
        set_property(WEATHER_WINDOW, 'Current.Location')
        set_property(WEATHER_WINDOW, 'Current.Condition')
        set_property(WEATHER_WINDOW, 'Current.ConditionLong')
        set_property(WEATHER_WINDOW, 'Current.Temperature')
        set_property(WEATHER_WINDOW, 'Current.Ozw_Temperature')
        set_property(WEATHER_WINDOW, 'Current.Wind')
        set_property(WEATHER_WINDOW, 'Current.WindSpeed')
        set_property(WEATHER_WINDOW, 'Current.Ozw_WindSpeed')
        set_property(WEATHER_WINDOW, 'Current.WindDirection')
        set_property(WEATHER_WINDOW, 'Current.WindDegree')
        set_property(WEATHER_WINDOW, 'Current.WindGust')
        set_property(WEATHER_WINDOW, 'Current.Pressure')
        set_property(WEATHER_WINDOW, 'Current.FireDanger')
        set_property(WEATHER_WINDOW, 'Current.FireDangerText')
        set_property(WEATHER_WINDOW, 'Current.Visibility')
        set_property(WEATHER_WINDOW, 'Current.Humidity')
        set_property(WEATHER_WINDOW, 'Current.Ozw_Humidity')
        set_property(WEATHER_WINDOW, 'Current.FeelsLike')
        set_property(WEATHER_WINDOW, 'Current.Ozw_FeelsLike')
        set_property(WEATHER_WINDOW, 'Current.DewPoint')
        set_property(WEATHER_WINDOW, 'Current.UVIndex')
        set_property(WEATHER_WINDOW, 'Current.OutlookIcon')
        set_property(WEATHER_WINDOW, 'Current.ConditionIcon')
        set_property(WEATHER_WINDOW, 'Current.FanartCode')
        set_property(WEATHER_WINDOW, 'Current.Sunrise')
        set_property(WEATHER_WINDOW, 'Current.Sunset')
        set_property(WEATHER_WINDOW, 'Current.RainSince9')
        set_property(WEATHER_WINDOW, 'Current.RainLastHr')
        set_property(WEATHER_WINDOW, 'Current.Precipitation')
        set_property(WEATHER_WINDOW, 'Current.ChancePrecipitation')
        set_property(WEATHER_WINDOW, 'Current.SolarRadiation')
        set_property(WEATHER_WINDOW, 'Current.NowLabel')
        set_property(WEATHER_WINDOW, 'Current.NowValue')
        set_property(WEATHER_WINDOW, 'Current.LaterLabel')
        set_property(WEATHER_WINDOW, 'Current.LaterValue')

        set_property(WEATHER_WINDOW, 'Today.IsFetched')
        set_property(WEATHER_WINDOW, 'Today.Sunrise')
        set_property(WEATHER_WINDOW, 'Today.Sunset')
        set_property(WEATHER_WINDOW, 'Today.moonphase')
        set_property(WEATHER_WINDOW, 'Today.Moonphase')

        # and all the properties for the forecast
        for count in range(0, 8):
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
            set_property(WEATHER_WINDOW, 'Day%i.OutlookIcon' % count )
            set_property(WEATHER_WINDOW, 'Day%i.ConditionIcon' % count)
            set_property(WEATHER_WINDOW, 'Day%i.FanartCode' % count)
            set_property(WEATHER_WINDOW, 'Day%i.ShortDate' % count)
            set_property(WEATHER_WINDOW, 'Day%i.ShortDay' % count)

            set_property(WEATHER_WINDOW, 'Daily.%i.Title' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.RainChance' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.RainChanceAmount' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.RainAmount' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.ChancePrecipitation' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.Precipitation' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.HighTemp' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.LowTemp' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.HighTemperature' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.LowTemperature' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.Outlook' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.LongOutlookDay' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.OutlookIcon' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.ConditionIcon' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.FanartCode' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.ShortDate' % count)
            set_property(WEATHER_WINDOW, 'Daily.%i.ShortDay' % count)

    except Exception as inst:
        log("********** Oz Weather Couldn't clear all the properties, sorry!!", inst)


def forecast(geohash, radar_code):
    """
    The main weather data retrieval function
    Does either a basic forecast, or a more extended forecast with radar etc.
    :param geohash: the BOM geohash for the location
    :param radar_code: the BOM radar code (e.g. 'IDR063') to retrieve the radar loop for
    """

    extended_features = ADDON.getSettingBool('ExtendedFeaturesToggle')
    log(f'Extended features: {extended_features}')
    purge_backgrounds = ADDON.getSettingBool('PurgeRadarBackgroundsOnNextRefresh')
    log(f'Purge Backgrounds: {purge_backgrounds}')

    # Has the user requested we refresh the radar backgrounds on next weather fetch?
    if purge_backgrounds:
        dump_all_radar_backgrounds()
        ADDON.setSetting('PurgeRadarBackgroundsOnNextRefresh', 'false')

    # Get the radar images first - because it looks better on refreshes
    if extended_features:
        log(f'Getting radar images for {radar_code}')
        backgrounds_path = xbmcvfs.translatePath(
            "special://profile/addon_data/weather.ozweather/radarbackgrounds/" + radar_code + "/")
        overlay_loop_path = xbmcvfs.translatePath(
            "special://profile/addon_data/weather.ozweather/currentloop/" + radar_code + "/")
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
            log(f"utc_oldest {utc_oldest}")
            log(f"utc_newest {utc_newest}")

            time_oldest = utc_str_to_local_str(utc_oldest, "%Y%m%d%H%M")
            time_newest = utc_str_to_local_str(utc_newest, "%Y%m%d%H%M")

            oldest_dt = datetime.datetime.fromtimestamp(os.path.getctime(oldest_file))
            newest_dt = datetime.datetime.fromtimestamp(os.path.getctime(newest_file))
            set_property(WEATHER_WINDOW, 'RadarOldest', time_oldest)
            set_property(WEATHER_WINDOW, 'RadarNewest', time_newest)

    # Get all the weather & forecast data from the BOM API
    weather_data = False

    if geohash:
        log(f'Using the BOM API.  Getting weather data for {geohash}')
        weather_data = bom_forecast(geohash)

    # At this point, we should have _something_ - if not, log the issue and we're done...
    if not weather_data:
        log("Unable to get weather_data from BOM - internet connection issue or addon not configured?", level=xbmc.LOGINFO)
        return

    # We have weather_data - set all the properties on Kodi's weather window...
    for weather_key in sorted(weather_data):
        set_property(WEATHER_WINDOW, weather_key, weather_data[weather_key])

    # Get the ABC 90-second weather video link if extended features is enabled
    if extended_features:
        log("Getting the ABC weather video link")
        url = get_abc_weather_video_link(ADDON.getSetting("ABCQuality"))
        if url:
            set_property(WEATHER_WINDOW, 'Video.1', url)

    # And announce everything is fetched..
    set_property(WEATHER_WINDOW, "Weather.IsFetched", "true")
    set_property(WEATHER_WINDOW, "Daily.IsFetched", "true")
    set_property(WEATHER_WINDOW, "Today.IsFetched", "true")
    set_property(WEATHER_WINDOW, 'Forecast.Updated', time.strftime("%d/%m/%Y %H:%M"))


def get_weather():
    """
    Gets the latest observations, forecast and radar images for the currently chosen location
    """

    log("*** Updating Weather Data ***")

    # Nice neat updates - clear out all set window data first...
    clear_properties()

    # This is/was an attempt to use conditions in skins to basically auto-adapt the MyWeather.xml and all OzWeather
    # components to the currently-in-use skin.  However, no matter what I try I can't get the conditions to work
    # in the skin files.
    try:
        skin_in_use = xbmc.getSkinDir().split('.')[1]
        set_property(WEATHER_WINDOW, 'SkinInUse', skin_in_use)
    except:
        pass

    # Retrieve the currently chosen location geohash & radar code
    geohash = ADDON.getSetting(f'Location{sys.argv[1]}BOMGeoHash')
    radar = ADDON.getSetting(f'Radar{sys.argv[1]}') or ADDON.getSetting(f'Location{sys.argv[1]}ClosestRadar')

    # With the new closest radar system, the radar is store as e.g. 'Melbourne - IDR023' so strip the name off...
    split_code = radar.split(' - ')
    if len(split_code) > 1:
        log(f"Radar code: transforming [{radar}] to: [{split_code[-1]}]")
        radar = split_code[-1]

    if not geohash:
        log("No BOM location geohash - can't retrieve weather data!")
        return

    # If we don't have a radar code, get the national radar by default
    if not radar:
        radar = 'IDR00004'
        log(f'Radar code empty for location, so using default radar code {radar} (= national radar)')

    log(f'Current location: BOM geohash "{geohash}", radar code {radar}')

    # Now scrape the weather data & radar images
    forecast(geohash, radar)

    # Set basic properties/'brand'
    set_property(WEATHER_WINDOW, 'WeatherProviderLogo', xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'banner.png')))
    set_property(WEATHER_WINDOW, 'WeatherProvider', 'Bureau of Meteorology Australia')
    set_property(WEATHER_WINDOW, 'WeatherVersion', ADDON_NAME + "-" + ADDON_VERSION)

    # Set the location we updated
    location_in_use = ADDON.getSetting(f'Location{sys.argv[1]}BOM')
    try:
        location_in_use = location_in_use[0:location_in_use.index(' (')]
    except ValueError:
        pass

    set_property(WEATHER_WINDOW, 'Location', location_in_use)
    set_property(WEATHER_WINDOW, 'Updated', time.strftime("%d/%m %H:%M").lower())
    set_property(WEATHER_WINDOW, 'Current.Location', location_in_use)
    set_property(WEATHER_WINDOW, 'Forecast.City', location_in_use)
    set_property(WEATHER_WINDOW, 'Forecast.Country', "Australia")
    set_property(WEATHER_WINDOW, 'Forecast.Updated', time.strftime("%d/%m @ %H:%M").lower())

