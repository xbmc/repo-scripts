# -*- coding: utf-8 -*-

# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING. If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *

import os, sys, socket
import xbmc, xbmcvfs, xbmcgui, xbmcaddon
import re
import time

# Minimal code to import bossanova808 common code
ADDON           = xbmcaddon.Addon()
CWD             = ADDON.getAddonInfo('path')
RESOURCES_PATH  = xbmc.translatePath( os.path.join( CWD, 'resources' ))
LIB_PATH        = xbmc.translatePath(os.path.join( RESOURCES_PATH, "lib" ))
WEATHER_WINDOW  = xbmcgui.Window(12600)

# Extra imports
sys.path.append( LIB_PATH )

from b808common import *
from weatherzone import *
from abcvideo import *
from bom import *

# Clear all weather window properties

def clearProperties():
    log("Clearing Properties")
    try:
        setProperty(WEATHER_WINDOW, 'WeatherProviderLogo')
        setProperty(WEATHER_WINDOW, 'WeatherProvider')
        setProperty(WEATHER_WINDOW, 'WeatherVersion')
        setProperty(WEATHER_WINDOW, 'Location')
        setProperty(WEATHER_WINDOW, 'Updated')
        setProperty(WEATHER_WINDOW, 'Weather.IsFetched',"false")
        setProperty(WEATHER_WINDOW, 'Daily.IsFetched'  ,"false")
        setProperty(WEATHER_WINDOW, 'Radar')
        setProperty(WEATHER_WINDOW, 'Video.1')

        setProperty(WEATHER_WINDOW, 'Forecast.City')
        setProperty(WEATHER_WINDOW, 'Forecast.Country')
        setProperty(WEATHER_WINDOW, 'Forecast.Updated')

        setProperty(WEATHER_WINDOW, 'Current.IsFetched',"false")
        setProperty(WEATHER_WINDOW, 'Current.Location')
        setProperty(WEATHER_WINDOW, 'Current.Condition')
        setProperty(WEATHER_WINDOW, 'Current.ConditionLong')
        setProperty(WEATHER_WINDOW, 'Current.Temperature')
        setProperty(WEATHER_WINDOW, 'Current.Wind')
        setProperty(WEATHER_WINDOW, 'Current.WindDirection')
        setProperty(WEATHER_WINDOW, 'Current.WindDegree')
        setProperty(WEATHER_WINDOW, 'Current.WindGust')
        setProperty(WEATHER_WINDOW, 'Current.Pressure')
        setProperty(WEATHER_WINDOW, 'Current.FireDanger')
        setProperty(WEATHER_WINDOW, 'Current.FireDangerText')
        setProperty(WEATHER_WINDOW, 'Current.Visibility')
        setProperty(WEATHER_WINDOW, 'Current.Humidity')
        setProperty(WEATHER_WINDOW, 'Current.FeelsLike')
        setProperty(WEATHER_WINDOW, 'Current.DewPoint')
        setProperty(WEATHER_WINDOW, 'Current.UVIndex')
        setProperty(WEATHER_WINDOW, 'Current.OutlookIcon', "na.png")
        setProperty(WEATHER_WINDOW, 'Current.ConditionIcon', "na.png")
        setProperty(WEATHER_WINDOW, 'Current.FanartCode')
        setProperty(WEATHER_WINDOW, 'Current.Sunrise')
        setProperty(WEATHER_WINDOW, 'Current.Sunset')
        setProperty(WEATHER_WINDOW, 'Current.RainSince9')
        setProperty(WEATHER_WINDOW, 'Current.RainLastHr')
        setProperty(WEATHER_WINDOW, 'Current.Precipitation')
        setProperty(WEATHER_WINDOW, 'Current.ChancePrecipitation')
        setProperty(WEATHER_WINDOW, 'Current.SolarRadiation')

        setProperty(WEATHER_WINDOW, 'Today.IsFetched'  ,"false")
        setProperty(WEATHER_WINDOW, 'Today.Sunrise')
        setProperty(WEATHER_WINDOW, 'Today.Sunset')
        setProperty(WEATHER_WINDOW, 'Today.moonphase')
        setProperty(WEATHER_WINDOW, 'Today.Moonphase')


        #and all the properties for the forecast
        for count in range(0,8):
            setProperty(WEATHER_WINDOW, 'Day%i.Title'                           % count)
            setProperty(WEATHER_WINDOW, 'Day%i.RainChance'                      % count)
            setProperty(WEATHER_WINDOW, 'Day%i.RainChanceAmount'                % count)
            setProperty(WEATHER_WINDOW, 'Day%i.ChancePrecipitation'             % count)
            setProperty(WEATHER_WINDOW, 'Day%i.Precipitation'                   % count)
            setProperty(WEATHER_WINDOW, 'Day%i.HighTemp'                        % count)
            setProperty(WEATHER_WINDOW, 'Day%i.LowTemp'                         % count)
            setProperty(WEATHER_WINDOW, 'Day%i.HighTemperature'                 % count)
            setProperty(WEATHER_WINDOW, 'Day%i.LowTemperature'                  % count)
            setProperty(WEATHER_WINDOW, 'Day%i.Outlook'                         % count)
            setProperty(WEATHER_WINDOW, 'Day%i.LongOutlookDay'                  % count)
            setProperty(WEATHER_WINDOW, 'Day%i.OutlookIcon'                     % count, "na.png")
            setProperty(WEATHER_WINDOW, 'Day%i.ConditionIcon'                   % count, "na.png")
            setProperty(WEATHER_WINDOW, 'Day%i.FanartCode'                      % count)
            setProperty(WEATHER_WINDOW, 'Day%i.ShortDate'                       % count)
            setProperty(WEATHER_WINDOW, 'Day%i.ShortDay'                        % count)
                        
            setProperty(WEATHER_WINDOW, 'Daily.%i.Title'                        % count)
            setProperty(WEATHER_WINDOW, 'Daily.%i.RainChance'                   % count)
            setProperty(WEATHER_WINDOW, 'Daily.%i.RainChanceAmount'             % count)
            setProperty(WEATHER_WINDOW, 'Daily.%i.ChancePrecipitation'          % count)
            setProperty(WEATHER_WINDOW, 'Daily.%i.Precipitation'                % count)
            setProperty(WEATHER_WINDOW, 'Daily.%i.HighTemp'                     % count)
            setProperty(WEATHER_WINDOW, 'Daily.%i.LowTemp'                      % count)
            setProperty(WEATHER_WINDOW, 'Daily.%i.HighTemperature'              % count)
            setProperty(WEATHER_WINDOW, 'Daily.%i.LowTemperature'               % count)
            setProperty(WEATHER_WINDOW, 'Daily.%i.Outlook'                      % count)
            setProperty(WEATHER_WINDOW, 'Daily.%i.LongOutlookDay'               % count)
            setProperty(WEATHER_WINDOW, 'Daily.%i.OutlookIcon'                  % count, "na.png")
            setProperty(WEATHER_WINDOW, 'Daily.%i.ConditionIcon'                % count, "na.png")
            setProperty(WEATHER_WINDOW, 'Daily.%i.FanartCode'                   % count)
            setProperty(WEATHER_WINDOW, 'Daily.%i.ShortDate'                    % count)
            setProperty(WEATHER_WINDOW, 'Daily.%i.ShortDay'                     % count)

    except Exception as inst:
        log("********** OzWeather Couldn't clear all the properties, sorry!!", inst)


# Set the location and radar code properties

def refresh_locations():

    log("Refreshing locations from settings")
    location_set1 = ADDON.getSetting('Location1')
    location_set2 = ADDON.getSetting('Location2')
    location_set3 = ADDON.getSetting('Location3')
    locations = 0
    if location_set1 != '':
        locations += 1
        setProperty(WEATHER_WINDOW, 'Location1', location_set1)
    else:
        setProperty(WEATHER_WINDOW, 'Location1')
    if location_set2 != '':
        locations += 1
        setProperty(WEATHER_WINDOW, 'Location2', location_set2)
    else:
        setProperty(WEATHER_WINDOW, 'Location2')
    if location_set3 != '':
        locations += 1
        setProperty(WEATHER_WINDOW, 'Location3', location_set3)
    else:
        setProperty(WEATHER_WINDOW, 'Location3')

    setProperty(WEATHER_WINDOW, 'Locations', str(locations))

    log("Refreshing radar locations from settings")
    radar_set1 = ADDON.getSetting('Radar1')
    radar_set2 = ADDON.getSetting('Radar2')
    radar_set3 = ADDON.getSetting('Radar3')
    radars = 0
    if radar_set1 != '':
        radars += 1
        setProperty(WEATHER_WINDOW, 'Radar1', radar_set1)
    else:
        setProperty(WEATHER_WINDOW, 'Radar1')
    if radar_set2 != '':
        radars += 1
        setProperty(WEATHER_WINDOW, 'Radar2', radar_set2)
    else:
        setProperty(WEATHER_WINDOW, 'Radar2')
    if radar_set3 != '':
        radars += 1
        setProperty(WEATHER_WINDOW, 'Radar3', radar_set3)
    else:
        setProperty(WEATHER_WINDOW, 'Radar3')

    setProperty(WEATHER_WINDOW, 'Radars', str(locations))



# Set any weather values to the old style, e.g. hardcoded icon paths
def oldKodiWeatherData(weatherData):

    print("Modifying weather data for kodi version " + str(VERSION_NUMBER))
    
    for index in range(0,7):

        keys = ["OutlookIcon","ConditionIcon"]   
        value = weatherData['Day' + str(index) + '.' + keys[0]]
        value = xbmc.translatePath('special://temp/weather/%s').decode("utf-8") % value

        for key in keys:
            if index is 0:
                weatherData['Current.' + key] = value
                weatherData['Current.' + key] = value

            weatherData['Day' + str(index) + '.' + key] = value
            weatherData['Day' + str(index) + '.' + key] = value
            weatherData['Daily.' + str(index+1) + '.' + key] = value
            weatherData['Daily.' + str(index+1) + '.' + key] = value

    return weatherData

# The main forecast retrieval function
# Does either a basic forecast or a more extended forecast with radar etc.

def forecast(urlPath, radarCode):

    extendedFeatures = ADDON.getSetting('ExtendedFeaturesToggle')

    log("Getting weather from [%s] with radar [%s], extended features is: [%s]" % (urlPath, radarCode, str(extendedFeatures)))

    # Get the radar images first - looks better on refreshes
    if extendedFeatures == "true":
        log("Getting radar images for " + radarCode)
        
        backgroundsPath = xbmc.translatePath("special://profile/addon_data/weather.ozweather/radarbackgrounds/" + radarCode + "/");
        overlayLoopPath = xbmc.translatePath("special://profile/addon_data/weather.ozweather/currentloop/" + radarCode + "/");

        updateRadarBackgrounds = ADDON.getSetting('BGDownloadToggle')

        buildImages(radarCode, updateRadarBackgrounds, backgroundsPath, overlayLoopPath)
        setProperty(WEATHER_WINDOW, 'Radar', radarCode)

    # Get all the weather & forecast data from weatherzone
    log("Get the forecast data from http://weatherzone.com.au" + urlPath)
    weatherData = getWeatherData(urlPath, extendedFeatures, VERSION_NUMBER)
    if VERSION_NUMBER < 15.9:
        weatherData = oldKodiWeatherData(weatherData)

    for key in sorted(weatherData):
        setProperty(WEATHER_WINDOW, key, weatherData[key])

    # Get the ABC video link
    if extendedFeatures == "true":
        log("Get the ABC weather video link")
        url = getABCWeatherVideoLink(ADDON.getSetting("ABCQuality"))
        if url:
            setProperty(WEATHER_WINDOW, 'Video.1',url)


    # And announce everything is fetched..    
    setProperty(WEATHER_WINDOW, "Weather.IsFetched", "true")
    setProperty(WEATHER_WINDOW, 'Forecast.Updated', time.strftime("%d/%m/%Y %H:%M"))
    setProperty(WEATHER_WINDOW, 'Today.IsFetched', "true")        


# TWO MAJOR MODES - SETTINGS and FORECAST RETRIEVAL

if __name__ == "__main__":

    footprints()

    socket.setdefaulttimeout(100)

    # SETTINGS
    # the addon is being called from the settings section where the user enters their postcodes
    if sys.argv[1].startswith('Location'):
        
        keyboard = xbmc.Keyboard('', LANGUAGE(32195), False)
        keyboard.doModal()
        
        if (keyboard.isConfirmed() and keyboard.getText() != ''):
            text = keyboard.getText()

            log("Doing locations search for " + text)
            locations, locationURLPaths = getLocationsForPostcodeOrSuburb(text)

            # Now get them to choose an actual location
            dialog = xbmcgui.Dialog()
            if locations != []:
                selected = dialog.select(xbmc.getLocalizedString(396), locations)
                if selected != -1:
                    ADDON.setSetting(sys.argv[1], locations[selected])
                    ADDON.setSetting(sys.argv[1] + 'UrlPath', locationURLPaths[selected])
            # Or indicate we did not receieve any locations
            else:
                dialog.ok(ADDONNAME, xbmc.getLocalizedString(284))


    # FORECAST
    # script is being called in general use, not from the settings page
    # sys.argv[1] has the current location number, so get the currently selected location and grab it's forecast
    else:

        # Nice neat updates - clear out everything first...
        clearProperties()

        # Set basic properties/brand
        setProperty(WEATHER_WINDOW, 'WeatherProviderLogo'       , xbmc.translatePath(os.path.join(CWD, 'resources', 'banner.png')))
        setProperty(WEATHER_WINDOW, 'WeatherProvider'           , 'Bureau of Meteorology Australia (via WeatherZone)')
        setProperty(WEATHER_WINDOW, 'WeatherVersion'            , ADDONNAME + "-" + VERSION)
        
        # Set what we updated and when
        setProperty(WEATHER_WINDOW, 'Location'              , ADDON.getSetting('Location%s' % sys.argv[1]))
        setProperty(WEATHER_WINDOW, 'Updated'               , time.strftime("%d/%m/%Y %H:%M"))
        setProperty(WEATHER_WINDOW, 'Current.Location'      , ADDON.getSetting('Location%s' % sys.argv[1]))
        setProperty(WEATHER_WINDOW, 'Forecast.City'         , ADDON.getSetting('Location%s' % sys.argv[1]))
        setProperty(WEATHER_WINDOW, 'Forecast.Country'      , "Australia")
        setProperty(WEATHER_WINDOW, 'Forecast.Updated'      , time.strftime("%d/%m/%Y %H:%M"))

        # Retrieve the currently chosen location & radar
        locationUrlPath = ""
        locationUrlPath = ADDON.getSetting('Location%sUrlPath' % sys.argv[1])

        # Old style paths (pre v0.8.5) must be updated to new
        if not locationUrlPath:
            locationUrlPath = ADDON.getSetting('Location%sid' % sys.argv[1])
            locationUrlPath = locationUrlPath.replace("http://www.weatherzone.com.au","")
            ADDON.setSetting('Location%sUrlPath' % sys.argv[1], locationUrlPath)

        radar = ""
        radar = ADDON.getSetting('Radar%s' % sys.argv[1])
        # If we don't have a radar code, get the national radar by default
        if radar == "":
            log("Radar code empty for location " + location +" so using default radar code IDR00004 (national radar)")
            radar = "IDR00004"
        
        # Now scrape the weather data & radar images
        forecast(locationUrlPath, radar)

    # Refresh the locations
    refresh_locations()

    # and close out...
    footprints(startup=False)
