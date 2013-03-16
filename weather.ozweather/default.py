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

import os, sys, urllib, urllib2, socket
import xbmc, xbmcvfs, xbmcgui, xbmcaddon
import CommonFunctions
import re
import ftplib
import shutil
import time

# Minimal code to import bossanova808 common code
ADDON           = xbmcaddon.Addon()
CWD             = ADDON.getAddonInfo('path')
RESOURCES_PATH  = xbmc.translatePath( os.path.join( CWD, 'resources' ))
LIB_PATH        = xbmc.translatePath(os.path.join( RESOURCES_PATH, "lib" ))
sys.path.append( LIB_PATH )
from b808common import *

#import the tables that map conditions to icon number and short days to long days
from utilities import *

#parseDOM setup
common = CommonFunctions
common.plugin = ADDONNAME + "-" + VERSION
dbg = False # Set to false if you don't want debugging
dbglevel = 3

#Handy Strings
WEATHER_WINDOW  = xbmcgui.Window(12600)
WEATHERZONE_URL = 'http://www.weatherzone.com.au'
FTPSTUB = "ftp://anonymous:someone%40somewhere.com@ftp.bom.gov.au//anon/gen/radar_transparencies/"
HTTPSTUB = "http://www.bom.gov.au/products/radar_transparencies/"
RADAR_BACKGROUNDS_PATH = ""
LOOP_IMAGES_PATH = ""



################################################################################
# blank out all the window properties

def clearProperties():
    log("Clearing Properties")
    try:
        setProperty(WEATHER_WINDOW, 'Weather.IsFetched')
        setProperty(WEATHER_WINDOW, 'Radar')
        setProperty(WEATHER_WINDOW, 'Video.1')

        #now set all the XBMC current weather properties
        setProperty(WEATHER_WINDOW, 'Current.Condition')
        setProperty(WEATHER_WINDOW, 'Current.ConditionLong')
        setProperty(WEATHER_WINDOW, 'Current.Temperature')
        setProperty(WEATHER_WINDOW, 'Current.Wind')
        setProperty(WEATHER_WINDOW, 'Current.WindDirection')
        setProperty(WEATHER_WINDOW, 'Current.Humidity')
        setProperty(WEATHER_WINDOW, 'Current.FeelsLike')
        setProperty(WEATHER_WINDOW, 'Current.DewPoint')
        setProperty(WEATHER_WINDOW, 'Current.UVIndex')
        setProperty(WEATHER_WINDOW, 'Current.OutlookIcon')
        setProperty(WEATHER_WINDOW, 'Current.FanartCode')

        #and all the properties for the forecast
        for count in range(0,7):
            setProperty(WEATHER_WINDOW, 'Day%i.Title'       % count)
            setProperty(WEATHER_WINDOW, 'Day%i.HighTemp'    % count)
            setProperty(WEATHER_WINDOW, 'Day%i.LowTemp'     % count)
            setProperty(WEATHER_WINDOW, 'Day%i.Outlook'     % count)
            setProperty(WEATHER_WINDOW, 'Day%i.OutlookIcon' % count)
            setProperty(WEATHER_WINDOW, 'Day%i.FanartCode'  % count)

    except Exception as inst:
        log("********** OzWeather Couldn't clear all the properties, sorry!!", inst)


################################################################################
# set the location and radar code properties

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
        setProperty(WEATHER_WINDOW, 'Location1', '')
    if location_set2 != '':
        locations += 1
        setProperty(WEATHER_WINDOW, 'Location2', location_set2)
    else:
        setProperty(WEATHER_WINDOW, 'Location2', '')
    if location_set3 != '':
        locations += 1
        setProperty(WEATHER_WINDOW, 'Location3', location_set3)
    else:
        setProperty(WEATHER_WINDOW, 'Location3', '')

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
        setProperty(WEATHER_WINDOW, 'Radar1', '')
    if radar_set2 != '':
        radars += 1
        setProperty(WEATHER_WINDOW, 'Radar2', radar_set2)
    else:
        setProperty(WEATHER_WINDOW, 'Radar2', '')
    if radar_set3 != '':
        radars += 1
        setProperty(WEATHER_WINDOW, 'Radar3', radar_set3)
    else:
        setProperty(WEATHER_WINDOW, 'Radar3', '')

    setProperty(WEATHER_WINDOW, 'Radars', str(locations))


################################################################################
# The main forecast retrieval function
# Does either a basic forecast or a more extended forecast with radar etc.
# if the appropriate setting is set

def forecast(url, radarCode):
    log("Called forecast()")

    #pull in the paths
    global RADAR_BACKGROUNDS_PATH, LOOP_IMAGES_PATH

    #make sure updates look neat
    clearProperties()

    #check if we're doing jsut a basic data update or data and images
    extendedFeatures = ADDON.getSetting('ExtendedFeaturesToggle')
    log("Getting weather from " + url + ", Extended features = " + str(extendedFeatures))

    #ok now we want to build the radar images first, looks neater
    if extendedFeatures == "true":
        log("Extended feature powers -> activate!")

        #strings to store the paths we will use
        RADAR_BACKGROUNDS_PATH = xbmc.translatePath("special://profile/addon_data/weather.ozweather/radarbackgrounds/" + radarCode + "/");
        LOOP_IMAGES_PATH = xbmc.translatePath("special://profile/addon_data/weather.ozweather/currentloop/" + radarCode + "/");

        log("Build radar images")
        buildImages(radarCode)
        radar = ""
        radar = ADDON.getSetting('Radar%s' % sys.argv[1])
        setProperty(WEATHER_WINDOW, 'Radar', radar)

    #and now get and set all the temperatures etc.
    log("Get the forecast data from weatherzone.com.au: " + url)
    try:
        data = common.fetchPage({"link":url})
    except Exception as inst:
        log("Error, couldn't retrieve weather page from WeatherZone - error: ", inst)
    if data != '':
        propertiesPDOM(data["content"], extendedFeatures)
    else:
        log("Weatherzone returned empty data??!")

################################################################################
# Downloads a radar background given a BOM radar code like IDR023 & filename
# Converts the image from indexed colour to RGBA colour

def downloadBackground(radarCode, fileName):
    global RADAR_BACKGROUNDS_PATH, LOOP_IMAGES_PATH

    outFileName = fileName

    #the legend file doesn't have the radar code int he filename
    if fileName == "IDR.legend.0.png":
        outFileName = "legend.png"
    else:
        #append the radar code
        fileName = radarCode + "." + fileName

    #are the backgrounds stale?
    if xbmcvfs.exists( RADAR_BACKGROUNDS_PATH + outFileName ):
        fileCreation = os.path.getmtime( RADAR_BACKGROUNDS_PATH + outFileName)
        now = time.time()
        weekAgo = now - 7*60*60*24 # Number of seconds in a week
        #log ("filec " + str(fileCreation) + " dayAgo " + str(dayAgo))
        if fileCreation < weekAgo:
            log("Background older than one week - let's refresh - " + outFileName)
            os.remove(RADAR_BACKGROUNDS_PATH + outFileName)

    #download the backgrounds only if we don't have them yet
    if not xbmcvfs.exists( RADAR_BACKGROUNDS_PATH + outFileName ):

        log("Downloading missing background image...." + outFileName)

        #import PIL only if we need it so the add on can be run for data only
        #on platforms without PIL
        log("Importing PIL as extra features are activated.")
        from PIL import Image
        #ok get ready to retrieve some images
        image = urllib.URLopener()

        #the legend image showing the rain scale
        try:
            imageFileIndexed = RADAR_BACKGROUNDS_PATH + "idx." + fileName
            imageFileRGB = RADAR_BACKGROUNDS_PATH + outFileName
            try:
                image.retrieve(FTPSTUB + fileName, imageFileIndexed )
            except:
                log("ftp failed, let's try http instead...")
                try:
                    image.retrieve(HTTPSTUB + fileName, imageFileIndexed )
                except:
                    log("http failed too.. sad face :( ")
                    #jump to the outer exception
                    raise
            #got here, we must have an image
            log("Downloaded background texture...now converting from indexed to RGB - " + fileName)
            im = Image.open( imageFileIndexed )
            rgbimg = im.convert('RGBA')
            rgbimg.save(imageFileRGB, "PNG")
            os.remove(imageFileIndexed)
        except Exception as inst:
            log("Error, couldn't retrieve " + fileName + " - error: ", inst)
            #ok try and get it via http instead?
            #try REALLY hard to get at least the background image
            try:
                #ok so something is wrong with image conversion - probably a PIL issue, so let's just get a minimal BG image
                if "background.png" in fileName:
                    if not '00004' in fileName:
                        image.retrieve(FTPSTUB + fileName, imageFileRGB )
                    else:
                        #national radar loop uses a different BG for some reason...
                        image.retrieve(FTPSTUB + 'IDE00035.background.png', imageFileRGB )
            except Exception as inst2:
                log("No, really, -> Error, couldn't retrieve " + fileName + " - error: ", inst2)


def prepareBackgrounds(radarCode):

    log("Called prepareBackgrounds()")

    downloadBackground(radarCode, "IDR.legend.0.png")
    downloadBackground(radarCode, "background.png")
    downloadBackground(radarCode, "locations.png")
    downloadBackground(radarCode, "range.png")
    downloadBackground(radarCode, "topography.png")
    downloadBackground(radarCode, "catchments.png")


################################################################################
# Builds the radar images given a BOM radar code like IDR023
# the background images are permanently cached (user can manually delete if
# they need to)
# the radar images are downloaded with each update (~60kb each time)

def buildImages(radarCode):

    log("Called buildImages with radarCode: " + radarCode)

    #remove the temporary files - we only want fresh radar files
    #this results in maybe ~60k used per update.
    if xbmcvfs.exists( LOOP_IMAGES_PATH ):
        log("Removing previous radar files")
        shutil.rmtree( LOOP_IMAGES_PATH , ignore_errors=True)

    #we need make the directories to store stuff if they don't exist
    if not xbmcvfs.exists( RADAR_BACKGROUNDS_PATH ):
        os.makedirs( RADAR_BACKGROUNDS_PATH )
    if not xbmcvfs.exists( LOOP_IMAGES_PATH ):
        os.makedirs( LOOP_IMAGES_PATH )

    log("Prepare the backgrounds if necessary...")
    prepareBackgrounds(radarCode)

    #Ok so we have the backgrounds...now it is time get the loop
    #first we retrieve a list of the available files via ftp
    #ok get ready to retrieve some images

    log("Download the radar loop")
    image = urllib.URLopener()
    files = []

    log("Log in to BOM FTP")
    ftp = ftplib.FTP("ftp.bom.gov.au")
    ftp.login("anonymous", "anonymous@anonymous.org")
    ftp.cwd("/anon/gen/radar/")

    log("Get files list")
    #connected, so let's get the list
    try:
        files = ftp.nlst()
    except ftplib.error_perm, resp:
        if str(resp) == "550 No files found":
            log("No files in BOM ftp directory!")
        else:
            log("Something wrong in the ftp bit of radar images")

    log("Download the files...")
    #ok now we need just the matching radar files...
    loopPicNames = []
    for f in files:
        if radarCode in f:
            loopPicNames.append(f)

    #download the actual images, might as well get the longest loop they have
    for f in loopPicNames:
        #ignore the composite gif...
        if f[-3:] == "png":
            imageToRetrieve = "ftp://anonymous:someone%40somewhere.com@ftp.bom.gov.au//anon/gen/radar/" + f
            log("Retrieving radar image: " + imageToRetrieve)
            try:
                image.retrieve(imageToRetrieve, LOOP_IMAGES_PATH + "/" + f )
            except Exception as inst:
                log("Failed to retrieve radar image: " + imageToRetrieve + ", oh well never mind!", inst )


################################################################################
# this is the main scraper function that uses parseDOM to scrape the
# data from the weatherzone site.

def propertiesPDOM(page, extendedFeatures):

    log("Use PDOM to pull weather forecast data")
    ####CURRENT DATA
    try:
        #pull data from the current observations table
        ret = common.parseDOM(page, "div", attrs = { "class": "details_lhs" })
        observations = common.parseDOM(ret, "td", attrs = { "class": "hilite bg_yellow" })
        #Observations now looks like - ['18.3&deg;C', '4.7&deg;C', '18.3&deg;C', '41%', 'SSW 38km/h', '48km/h', '1015.7hPa', '-', '0.0mm / -']
        log("Observations Retrieved: " + str(observations))
        temperature = observations[0].strip( '&deg;C' )
        log(" TEMP " + str(temperature))
        dewPoint = observations[1].strip( '&deg;C' )
        feelsLike = observations[2].strip( '&deg;C')
        humidity = observations[3].strip( '%')
        windTemp = observations[4].partition(' ');
        windDirection = windTemp[0]
        windSpeed = windTemp[2].strip( 'km/h')
        #there's no UV so we get that from the forecast, see below
    except Exception as inst:
        log("********** OzWeather Couldn't Parse Data, sorry!!", inst)
        setProperty(WEATHER_WINDOW, 'Current.Condition', "Error w. Current Data!")
        setProperty(WEATHER_WINDOW, 'Current.ConditionLong', "Error - Couldn't retrieve current weather data from WeatherZone - this is usually just a temporary problem with their server and with any luck they'll fix it soon!")
        setProperty(WEATHER_WINDOW, "Weather.IsFetched", "false")
    ####END CURRENT DATA

    ####FORECAST DATA
    try:
        #pull the basic data from the forecast table
        ret = common.parseDOM(page, "div", attrs = { "class": "boxed_blue_nopad" })
        #create lists of each of the maxes, mins, and descriptions
        #Get the days UV in text form like 'Extreme' and number '11'
        UVchunk = common.parseDOM(ret, "td", attrs = { "style": "text-align: center;" })
        UVtext = common.parseDOM(UVchunk, "span")
        UVnumber = common.parseDOM(UVchunk, "span", ret = "title")
        UV = UVtext[0] + ' (' + UVnumber[0] + ')'
        #get the 7 day max min forecasts
        maxMin = common.parseDOM(ret, "td")
        #for count, element in enumerate(maxMin):
        #   print "********" , count , "^^^" , str(element)
        maxList = stripList(maxMin[7:14],'&deg;C');
        minList = stripList(maxMin[14:21],'&deg;C');
        #and the short forecasts
        shortDesc = common.parseDOM(ret, "td", attrs = { "class": "bg_yellow" })
        shortDesc = common.parseDOM(ret, "span", attrs = { "style": "font-size: 0.9em;" })
        shortDesc = shortDesc[0:7]

        log(" shortDesc is " + str(shortDesc))

        for count, desc in enumerate(shortDesc):
            shortDesc[count] = shortDesc[count].title().replace( '-<br />','')
            shortDesc[count] = shortDesc[count].title().replace( '-<Br />','')
            shortDesc[count] = shortDesc[count].title().replace( 'ThunderStorms','Thunderstorms')
            shortDesc[count] = shortDesc[count].title().replace( 'windy','Windy')

        #log the collected data, helpful for finding errors
        log("Collected data: shortDesc [" + str(shortDesc) + "] maxList [" + str(maxList) +"] minList [" + str(minList) + "]")

        #and the names of the days
        days = common.parseDOM(ret, "span", attrs = { "style": "font-size: larger;" })
        days = common.parseDOM(ret, "span", attrs = { "class": "bold" })
        days = days[0:7]
        for count, day in enumerate(days):
            days[count] = DAYS[day]

        #get the longer current forecast for the day
        # or just use the short one if this is disabled in settings
        if extendedFeatures == "true":
            longDayCast = common.parseDOM(page, "div", attrs = { "class": "top_left" })
            longDayCast = common.parseDOM(longDayCast, "p" )
            longDayCast = common.stripTags(longDayCast[0])
            longDayCast = longDayCast.replace( '\t','')
            longDayCast = longDayCast.replace( '\r',' ')
            longDayCast = longDayCast.replace( '&amp;','&')
            longDayCast = longDayCast[:-1]
        else:
            longDayCast = shortDesc[0]

        #if for some reason the codes change return a neat 'na' response
        try:
            weathercode = WEATHER_CODES[shortDesc[0]]
        except:
            weathercode = 'na'

    except Exception as inst:
        log("********** OzWeather Couldn't Parse Data, sorry!!", inst)
        setProperty(WEATHER_WINDOW, 'Current.Condition', "Error w. Current Data!")
        setProperty(WEATHER_WINDOW, 'Current.ConditionLong', "Error - Couldn't retrieve forecast weather data from WeatherZone - this is usually just a temporary problem with their server and with any luck they'll fix it soon!")
        setProperty(WEATHER_WINDOW, "Weather.IsFetched", "false")
    #END FORECAST DATA

    #ABC VIDEO URL
    try:
        log("Trying to get ABC weather video URL")
        abcURL = "http://www.abc.net.au/news/abcnews24/weather-in-90-seconds/"
        req = urllib2.Request(abcURL)
        response = urllib2.urlopen(req)
        htmlSource = str(response.read())
        pattern_video = "http://mpegmedia.abc.net.au/news/weather/video/(.+?)video3.flv"
        video = re.findall( pattern_video, htmlSource )
        try:
            url = "http://mpegmedia.abc.net.au/news/weather/video/" + video[0] + "video3.flv"
            setProperty(WEATHER_WINDOW, 'Video.1',url)
        except Exception as inst:
            log("Couldn't get ABC video URL from page", inst)

    except Exception as inst:
        log("********** Couldn't get ABC video page", inst)
    #END ABC VIDEO URL

    # set all the XBMC window properties.
    # wrap it in a try: in case something goes wrong, it's better than crashing out...

    #SET PROPERTIES
    try:
        #now set all the XBMC current weather properties
        setProperty(WEATHER_WINDOW, 'Current.Condition'     , shortDesc[0])
        setProperty(WEATHER_WINDOW, 'Current.ConditionLong' , longDayCast)
        setProperty(WEATHER_WINDOW, 'Current.Temperature'   , temperature)
        setProperty(WEATHER_WINDOW, 'Current.Wind'          , windSpeed)
        setProperty(WEATHER_WINDOW, 'Current.WindDirection' , windDirection)
        setProperty(WEATHER_WINDOW, 'Current.Humidity'      , humidity)
        setProperty(WEATHER_WINDOW, 'Current.FeelsLike'     , feelsLike)
        setProperty(WEATHER_WINDOW, 'Current.DewPoint'      , dewPoint)
        setProperty(WEATHER_WINDOW, 'Current.UVIndex'       , UV)
        setProperty(WEATHER_WINDOW, 'Current.OutlookIcon'   , '%s.png' % weathercode)
        setProperty(WEATHER_WINDOW, 'Current.FanartCode'    , weathercode)

        #and all the properties for the forecast
        for count, desc in enumerate(shortDesc):
            try:
                weathercode = WEATHER_CODES[shortDesc[count]]
            except:
                weathercode = 'na'

            day = days[count]
            setProperty(WEATHER_WINDOW, 'Day%i.Title'       % count, day)
            setProperty(WEATHER_WINDOW, 'Day%i.HighTemp'    % count, maxList[count])
            setProperty(WEATHER_WINDOW, 'Day%i.LowTemp'     % count, minList[count])
            setProperty(WEATHER_WINDOW, 'Day%i.Outlook'     % count, desc)
            setProperty(WEATHER_WINDOW, 'Day%i.OutlookIcon' % count, '%s.png' % weathercode)
            setProperty(WEATHER_WINDOW, 'Day%i.FanartCode'  % count, weathercode)

    except Exception as inst:
        log("********** OzWeather Couldn't set all the properties, sorry!!", inst)

    #Ok, if we got here we're done
    setProperty(WEATHER_WINDOW, "Weather.IsFetched", "true")

    #END SET PROPERTIES


##############################################
### NOW ACTUALLTY RUN THIS PUPPY - this is main() in the old language...

footprints()

socket.setdefaulttimeout(100)

#the being called from the settings section where the user enters their postcodes
if sys.argv[1].startswith('Location'):
    keyboard = xbmc.Keyboard('', LANGUAGE(30195), False)
    keyboard.doModal()
    if (keyboard.isConfirmed() and keyboard.getText() != ''):
        text = keyboard.getText()

        log("Doing locations search for " + text)
        #need to submit the postcode to the weatherzone search
        searchURL = WEATHERZONE_URL + '/search/'
        user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
        host = 'www.weatherzone.com.au'
        headers = { 'User-Agent' : user_agent, 'Host' : host }
        values = {'q' : text, 't' : '3' }
        data = urllib.urlencode(values)
        req = urllib2.Request(searchURL, data, headers)
        response = urllib2.urlopen(req)
        resultPage = str(response.read())
        #was there only one match?  If so it returns the page for that match so we need to check the URL
        responseurl = response.geturl()
        log("Response page url: " + responseurl)
        if not responseurl.endswith('weatherzone.com.au/search/'):
                #we were redirected to an actual result page
            locationName = common.parseDOM(resultPage, "h1", attrs = { "class": "unenclosed" })
            locationName = locationName[0].split('Weather')
            locations = [locationName[0] + ', ' + text]
            locationids = [responseurl]
            log("Single result " + str(locations) + " URL " + str(locationids))
        else:
            #we got back a page to choose a more specific location
            try:
                locations=[]
                locationids=[]
                middle = common.parseDOM(resultPage, "div", attrs = { "id": "structure_middle" })
                skimmed = common.parseDOM(middle, "ul", attrs = { "class": "typ2" })
                #ok now get two lists - one of the friendly names
                #and a matchin one of the URLs to store
                locations = common.parseDOM(skimmed[0], "a")
                templocs = common.parseDOM(skimmed[0], "a", ret="href")
                #build the full urls
                locationids = []
                for count, loc in enumerate(templocs):
                    locationids.append(WEATHERZONE_URL + '/' + loc)
                #if we did not get enough data back there are no locations with this postcode
                if len(locations)<=1:
                    log("No locations found with this postcode")
                    locations = []
                    locationids = []
                log("Multiple result " + str(locations) + " URLs " + str(locationids))
            except:
                log("Error - middle: " + str(middle) + " skimmed " + str(skimmed))


        #now get them to choose an actual location
        dialog = xbmcgui.Dialog()
        if locations != []:
            selected = dialog.select(xbmc.getLocalizedString(396), locations)
            if selected != -1:
                ADDON.setSetting(sys.argv[1], locations[selected])
                ADDON.setSetting(sys.argv[1] + 'id', locationids[selected])
        else:
            dialog.ok(ADDONNAME, xbmc.getLocalizedString(284))


#script is being called in general use, not from the settings page
#get the currently selected location and grab it's forecast
else:

    #retrieve the currently set location & radar
    location = ""
    location = ADDON.getSetting('Location%sid' % sys.argv[1])
    radar = ""
    radar = ADDON.getSetting('Radar%s' % sys.argv[1])
    #now get a forecast
    forecast(location, radar)

#refresh the locations and set the weather provider property
refresh_locations()
setProperty(WEATHER_WINDOW, 'WeatherProvider', 'BOM Australia via WeatherZone')
setProperty(WEATHER_WINDOW, 'WeatherVersion', ADDONNAME + "-" + VERSION)

#and close out...
footprints(startup=False)