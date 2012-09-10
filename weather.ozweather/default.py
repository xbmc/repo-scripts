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

# plugin constants
#create an add on instation and store the reference
__addon__       = xbmcaddon.Addon()

#store some handy constants
__addonname__   = __addon__.getAddonInfo('name')
__addonid__     = __addon__.getAddonInfo('id')
__author__      = __addon__.getAddonInfo('author')
__version__     = __addon__.getAddonInfo('version')
__cwd__         = __addon__.getAddonInfo('path')
__language__    = __addon__.getLocalizedString
__useragent__   = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"
__plugin__ = __addonname__ + "-" + __version__
__resource__   = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
sys.path.append (__resource__)

#parseDOM setup
common = CommonFunctions
common.plugin = __plugin__
dbg = False # Set to false if you don't want debugging
dbglevel = 3

#import the tables that map conditions to icon number and short days to long days
from utilities import *

#Handy Strings
WEATHER_WINDOW  = xbmcgui.Window(12600)
WeatherZoneURL = 'http://www.weatherzone.com.au'
ftpStub = "ftp://anonymous:someone%40somewhere.com@ftp.bom.gov.au//anon/gen/radar_transparencies/"
httpStub = "http://www.bom.gov.au/products/radar_transparencies/"
radarBackgroundsPath = ""
loopImagesPath = ""


################################################################################
# strip given chararacters from all members of a given list

def striplist(l, chars):
    return([x.strip(chars) for x in l])

################################################################################
# log messages neatly to the XBMC master log

def log(message, inst=None):
    if inst is None:
      xbmc.log(__plugin__ + ": " + message)
    else:
      xbmc.log(__plugin__ + ": Exception: " + message + "[" + str(inst) +"]")

################################################################################
# Just sets window properties we can refer to later in the MyWeather.xml skin file

def set_property(name, value = ""):
    WEATHER_WINDOW.setProperty(name, value)

################################################################################
# blank out all the window properties

def clearProperties():
    try:
      set_property('Weather.IsFetched')
      set_property('Radar')
      set_property('Video.1')

      #now set all the XBMC current weather properties
      set_property('Current.Condition')
      set_property('Current.ConditionLong')
      set_property('Current.Temperature')
      set_property('Current.Wind')
      set_property('Current.WindDirection')
      set_property('Current.Humidity')
      set_property('Current.FeelsLike')
      set_property('Current.DewPoint')
      set_property('Current.UVIndex')
      set_property('Current.OutlookIcon')
      set_property('Current.FanartCode')

      #and all the properties for the forecast
      for count in range(0,7):
          set_property('Day%i.Title'       % count)
          set_property('Day%i.HighTemp'    % count)
          set_property('Day%i.LowTemp'     % count)
          set_property('Day%i.Outlook'     % count)
          set_property('Day%i.OutlookIcon' % count)
          set_property('Day%i.FanartCode'  % count)

    except Exception as inst:
      log("********** OzWeather Couldn't clear all the properties, sorry!!", inst)


################################################################################
# set the location and radar code properties

def refresh_locations():
    location_set1 = __addon__.getSetting('Location1')
    location_set2 = __addon__.getSetting('Location2')
    location_set3 = __addon__.getSetting('Location3')
    location_set4 = __addon__.getSetting('Location4')
    location_set5 = __addon__.getSetting('Location5')
    location_set6 = __addon__.getSetting('Location6')
    locations = 0
    if location_set1 != '':
        locations += 1
        set_property('Location1', location_set1)
    else:
        set_property('Location1', '')
    if location_set2 != '':
        locations += 1
        set_property('Location2', location_set2)
    else:
        set_property('Location2', '')
    if location_set3 != '':
        locations += 1
        set_property('Location3', location_set3)
    else:
        set_property('Location3', '')
    if location_set4 != '':
        locations += 1
        set_property('Location4', location_set4)
    else:
        set_property('Location4', '')
    if location_set5 != '':
        locations += 1
        set_property('Location5', location_set5)
    else:
        set_property('Location5', '')
    if location_set6 != '':
        locations += 1
        set_property('Location6', location_set6)
    else:
        set_property('Location6', '')
    set_property('Locations', str(locations))

    radar_set1 = __addon__.getSetting('Radar1')
    radar_set2 = __addon__.getSetting('Radar2')
    radar_set3 = __addon__.getSetting('Radar3')
    radar_set4 = __addon__.getSetting('Radar4')
    radar_set5 = __addon__.getSetting('Radar5')
    radar_set6 = __addon__.getSetting('Radar6')
    radars = 0
    if radar_set1 != '':
        radars += 1
        set_property('Radar1', radar_set1)
    else:
        set_property('Radar1', '')
    if radar_set2 != '':
        radars += 1
        set_property('Radar2', radar_set2)
    else:
        set_property('Radar2', '')
    if radar_set3 != '':
        radars += 1
        set_property('Radar3', radar_set3)
    else:
        set_property('Radar3', '')
    if radar_set4 != '':
        radars += 1
        set_property('Radar4', radar_set4)
    else:
        set_property('Radar4', '')
    if radar_set5 != '':
        radars += 1
        set_property('Radar5', radar_set5)
    else:
        set_property('Radar5', '')
    if radar_set6 != '':
        radars += 1
        set_property('Radar6', radar_set6)
    else:
        set_property('Radar6', '')
    set_property('Radars', str(locations))


################################################################################
# The main forecast retrieval function
# Does either a basic forecast or a more extended forecast with radar etc.
# if the appropriate setting is set

def forecast(url, radarCode):
    #pull in the paths
    global radarBackgroundsPath, loopImagesPath

    #make sure updates look neat
    clearProperties()

    #check if we're doing jsut a basic data update or data and images
    extendedFeatures = __addon__.getSetting('ExtendedFeaturesToggle')
    log("Getting weather from " + url + ", Extended features = " + str(extendedFeatures))

    #ok now we want to build the radar images first, looks neater
    if extendedFeatures == "true":
      log("Extended feature powers -> activate!")

      #strings to store the paths we will use
      radarBackgroundsPath = xbmc.translatePath("special://profile/addon_data/weather.ozweather/radarbackgrounds/" + radarCode + "/");
      loopImagesPath = xbmc.translatePath("special://profile/addon_data/weather.ozweather/currentloop/" + radarCode + "/");

      buildImages(radarCode)
      radar = ""
      radar = __addon__.getSetting('Radar%s' % sys.argv[1])
      set_property('Radar', radar)

    #and now get and set all the temperatures etc.
    try:
      data = common.fetchPage({"link":url})
    except Exception as inst:
      log("Error, couldn't retrieve weather page from WeatherZone - error: ", inst)
    if data != '':
       propertiesPDOM(data["content"], extendedFeatures)


################################################################################
# Downloads a radar background given a BOM radar code like IDR023 & filename
# Converts the image from indexed colour to RGBA colour

def downloadBackground(radarCode, fileName):
    global radarBackgroundsPath, loopImagesPath

    #import PIL only if we need it so the add on can be run for data only
    #on platforms without PIL
    #log("Importing PIL as extra features are activated.")
    from PIL import Image

    #ok get ready to retrieve some images
    image = urllib.URLopener()

    outFileName = fileName

    #the legend file doesn't have the radar code int he filename
    if fileName == "IDR.legend.0.png":
      outFileName = "legend.png"
    else:
      #append the radar code
      fileName = radarCode + "." + fileName

    #are the backgrounds stale?
    if xbmcvfs.exists( radarBackgroundsPath + outFileName ):
      fileCreation = os.path.getmtime( radarBackgroundsPath + outFileName)
      now = time.time()
      dayAgo = now - 60*60*24 # Number of seconds in a day
      #log ("filec " + str(fileCreation) + " dayAgo " + str(dayAgo))
      if fileCreation < dayAgo:
        log("Background older than one day - let's refresh - " + outFileName)
        os.remove(radarBackgroundsPath + outFileName)

    #download the backgrounds only if we don't have them yet
    if not xbmcvfs.exists( radarBackgroundsPath + outFileName ):
        #the legend image showing the rain scale
        try:
          imageFileIndexed = radarBackgroundsPath + "idx." + fileName
          imageFileRGB = radarBackgroundsPath + outFileName
          try:
            image.retrieve(ftpStub + fileName, imageFileIndexed )
          except:
            log("ftp failed, let's try http instead...")
            try:
              image.retrieve(httpStub + fileName, imageFileIndexed )
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
                image.retrieve(ftpStub + fileName, imageFileRGB )
              else:
                #national radar loop uses a different BG for some reason...
                image.retrieve(ftpStub + 'IDE00035.background.png', imageFileRGB )
          except Exception as inst2:
            log("No, really, -> Error, couldn't retrieve " + fileName + " - error: ", inst2)


def prepareBackgrounds(radarCode):
    global radarBackgroundsPath, loopImagesPath

    downloadBackground(radarCode, "IDR.legend.0.png")
    downloadBackground(radarCode, "background.png")
    downloadBackground(radarCode, "locations.png")
    downloadBackground(radarCode, "range.png")
    downloadBackground(radarCode, "topography.png")
    downloadBackground(radarCode, "catchments.png")
    #downloadBackground(radarCode, "waterways.png")
    #downloadBackground(radarCode, "wthrDistricts.png")
    #downloadBackground(radarCode, "rail.png")
    #downloadBackground(radarCode, "roads.png")



################################################################################
# Builds the radar images given a BOM radar code like IDR023
# the background images are permanently cached (user can manually delete if
# they need to)
# the radar images are downloaded with each update (~60kb each time)

def buildImages(radarCode):

    #remove the temporary files - we only want fresh radar files
    #this results in maybe ~60k used per update.
    if xbmcvfs.exists( loopImagesPath ):
      shutil.rmtree( loopImagesPath , ignore_errors=True)

    #we need make the directories to store stuff if they don't exist
    if not xbmcvfs.exists( radarBackgroundsPath ):
      os.makedirs( radarBackgroundsPath )
    if not xbmcvfs.exists( loopImagesPath ):
      os.makedirs( loopImagesPath )

    prepareBackgrounds(radarCode)

    #Ok so we have the backgrounds...now it is time get the loop
    #first we retrieve a list of the available files via ftp
    #ok get ready to retrieve some images
    image = urllib.URLopener()
    files = []

    ftp = ftplib.FTP("ftp.bom.gov.au")
    ftp.login("anonymous", "anonymous@anonymous.org")
    ftp.cwd("/anon/gen/radar/")

    #connected, so let's get the list
    try:
        files = ftp.nlst()
    except ftplib.error_perm, resp:
        if str(resp) == "550 No files found":
            log("No files in BOM ftp directory!")
        else:
            log("Something wrong in the ftp bit of radar images")

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
            image.retrieve(imageToRetrieve, loopImagesPath + "/" + f )
         except Exception as inst:
            log("Failed to retrieve radar image: " + imageToRetrieve + ", oh well never mind!", inst )


################################################################################
# this is the main scraper function that uses parseDOM to scrape the
# data from the weatherzone site.

def propertiesPDOM(page, extendedFeatures):

    ####CURRENT DATA
    try:
      #pull data from the current observations table
      ret = common.parseDOM(page, "div", attrs = { "class": "details_lhs" })
      observations = common.parseDOM(ret, "td", attrs = { "class": "hilite bg_yellow" })
      #Observations now looks like - ['18.3&deg;C', '4.7&deg;C', '18.3&deg;C', '41%', 'SSW 38km/h', '48km/h', '1015.7hPa', '-', '0.0mm / -']
      temperature = str.strip(observations[0], '&deg;C')
      dewPoint = str.strip(observations[1], '&deg;C')
      feelsLike = str.strip(observations[2], '&deg;C')
      humidity = str.strip(observations[3], '%')
      windTemp = observations[4].partition(' ');
      windDirection = windTemp[0]
      windSpeed = str.strip(windTemp[2], 'km/h')
      #there's no UV so we get that from the forecast, see below
    except Exception as inst:
      log("********** OzWeather Couldn't Parse Data, sorry!!", inst)
      set_property('Current.Condition', "Error w. Current Data!")
      set_property('Current.ConditionLong', "Error - Couldn't retrieve current weather data from WeatherZone - this is usually just a temporary problem with their server and with any luck they'll fix it soon!")
      set_property("Weather.IsFetched", "false")
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
      maxList = striplist(maxMin[7:14],'&deg;C');
      minList = striplist(maxMin[14:21],'&deg;C');
      #and the short forecasts
      shortDesc = common.parseDOM(ret, "td", attrs = { "class": "bg_yellow" })
      shortDesc = common.parseDOM(ret, "span", attrs = { "style": "font-size: 0.9em;" })
      shortDesc = shortDesc[0:7]

      for count, desc in enumerate(shortDesc):
        shortDesc[count] = str.replace(shortDesc[count].title(), '-<br />','')

      #log the collected data, helpful for finding errors
      #log("Collected data: shortDesc [" + str(shortDesc) + "] maxList [" + str(maxList) +"] minList [" + str(minList) + "]")

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
          #print '@@@@@@@@@ Long 1', longDayCast
          longDayCast = common.parseDOM(longDayCast, "p" )
          #print '@@@@@@@@@ Long 2', longDayCast
          #new method - just strip the crap (e.g. tabs) out of the string and use a colon separator for the 'return' as we don't have much space
          longDayCast = common.stripTags(longDayCast[0])
          #print longDayCast
          longDayCast = str.replace(longDayCast, '\t','')
          longDayCast = str.replace(longDayCast, '\r',' ')
          longDayCast = str.replace(longDayCast, '&amp;','&')
          #print '@@@@@@@@@ Long 4', longDayCast
          longDayCast = longDayCast[:-1]
          #print '@@@@@@@@@@@@@@@@' , longDayCast[-5:]
          #if longDayCast[-5:] != "winds":
          #  longDayCast = longDayCast + " fire danger."
      else:
          longDayCast = shortDesc[0]

      #if for some reason the codes change return a neat 'na' response
      try:
          weathercode = WEATHER_CODES[shortDesc[0]]
      except:
          weathercode = 'na'

    except Exception as inst:
      log("********** OzWeather Couldn't Parse Data, sorry!!", inst)
      set_property('Current.Condition', "Error w. Current Data!")
      set_property('Current.ConditionLong', "Error - Couldn't retrieve forecast weather data from WeatherZone - this is usually just a temporary problem with their server and with any luck they'll fix it soon!")
      set_property("Weather.IsFetched", "false")
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
        set_property('Video.1',url)
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
      set_property('Current.Condition'     , shortDesc[0])
      set_property('Current.ConditionLong' , longDayCast)
      set_property('Current.Temperature'   , temperature)
      set_property('Current.Wind'          , windSpeed)
      set_property('Current.WindDirection' , windDirection)
      set_property('Current.Humidity'      , humidity)
      set_property('Current.FeelsLike'     , feelsLike)
      set_property('Current.DewPoint'      , dewPoint)
      set_property('Current.UVIndex'       , UV)
      set_property('Current.OutlookIcon'   , '%s.png' % weathercode)
      set_property('Current.FanartCode'    , weathercode)

      #and all the properties for the forecast
      for count, desc in enumerate(shortDesc):
          try:
              weathercode = WEATHER_CODES[shortDesc[count]]
          except:
              weathercode = 'na'

          day = days[count]
          set_property('Day%i.Title'       % count, day)
          set_property('Day%i.HighTemp'    % count, maxList[count])
          set_property('Day%i.LowTemp'     % count, minList[count])
          set_property('Day%i.Outlook'     % count, desc)
          set_property('Day%i.OutlookIcon' % count, '%s.png' % weathercode)
          set_property('Day%i.FanartCode'  % count, weathercode)

    except Exception as inst:
      log("********** OzWeather Couldn't set all the properties, sorry!!", inst)

    #Ok, if we got here we're done
    set_property("Weather.IsFetched", "true")

    #END SET PROPERTIES


##############################################
### NOW ACTUALLTY RUN THIS PUPPY - this is main() in the old language...

socket.setdefaulttimeout(100)

#the being called from the settings section where the user enters their postcodes
if sys.argv[1].startswith('Location'):
    keyboard = xbmc.Keyboard('', 'Enter your 4 digit postcode e.g. 3000', False)
    keyboard.doModal()
    if (keyboard.isConfirmed() and keyboard.getText() != ''):
        text = keyboard.getText()

        log("Doing locations search for " + text)
        #need to submit the postcode to the weatherzone search
        searchURL = 'http://weatherzone.com.au/search/'
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
            locationName = str.split(locationName[0], ' Weather')
            locations = [locationName[0] + ', ' + text]
            locationids = [responseurl]
            log("Single result " + str(locations) + " URL " + str(locationids))
        else:
            #we got back a page to choose a more specific location
            middle = common.parseDOM(resultPage, "div", attrs = { "id": "structure_middle" })
            skimmed = common.parseDOM(middle, "ul", attrs = { "class": "typ2" })
            #ok now get two lists - one of the friendly names
            #and a matchin one of the URLs to store
            locations = common.parseDOM(skimmed[0], "a")
            templocs = common.parseDOM(skimmed[0], "a", ret="href")
            #build the full urls
            locationids = []
            for count, loc in enumerate(templocs):
                locationids.append(WeatherZoneURL + loc)
            #if we did not get enough data back there are no locations with this postcode
            if len(locations)<=1:
                log("No locations found with this postcode")
                locations = []
                locationids = []
            log("Multiple result " + str(locations) + " URLs " + str(locationids))


        #now get them to choose an actual location
        dialog = xbmcgui.Dialog()
        if locations != []:
            selected = dialog.select(xbmc.getLocalizedString(396), locations)
            if selected != -1:
                __addon__.setSetting(sys.argv[1], locations[selected])
                __addon__.setSetting(sys.argv[1] + 'id', locationids[selected])
        else:
            dialog.ok(__addonname__, xbmc.getLocalizedString(284))


#script is being called in general use, not from the settings page
#get the currently selected location and grab it's forecast
else:

    #retrieve the currently set location & radar
    location = ""
    location = __addon__.getSetting('Location%sid' % sys.argv[1])
    radar = ""
    radar = __addon__.getSetting('Radar%s' % sys.argv[1])
    #now get a forecast
    forecast(location, radar)

#refresh the locations and set the weather provider property
refresh_locations()
set_property('WeatherProvider', 'BOM Australia via WeatherZone')
set_property('WeatherVersion', __plugin__)

