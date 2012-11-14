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
# *  along with XBMC; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *


import os, sys
import urllib
from xml.dom import minidom
import xbmcgui, xbmcaddon
from time import strftime, strptime


__addon__      = xbmcaddon.Addon()
__cwd__        = __addon__.getAddonInfo('path')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__author__     = __addon__.getAddonInfo('author')
__language__   = __addon__.getLocalizedString

__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")

sys.path.append (__resource__)

from utilities import *

DEVELOPER_KEY  = "75b745967f114856110511"
NUMBER_OF_DAYS = 4
SEARCH_URL     = "http://free.worldweatheronline.com/feed/search.ashx?key=%s&query=%s&format=xml"
LOCATION_URL   = "http://free.worldweatheronline.com/feed/weather.ashx?q=%s&format=xml&num_of_days=%i&key=%s"

WEATHER_WINDOW = xbmcgui.Window( 12600 )

def set_property(property, value):
  WEATHER_WINDOW.setProperty(property, value)

def clear_properties():
    log("clear_properties")
    set_property("Current.Condition"       , "")
    set_property("Current.Temperature"     , "")
    set_property("Current.Wind"            , "")
    set_property("Current.Humidity"        , "")
    set_property("Current.winddirection"   , "")
    set_property("Current.OutlookIcon"     , "")
    set_property("Current.FanartCode"      , "")
    set_property("Current.FeelsLike"       , "")
    set_property("Current.DewPoint"        , "")
    set_property("Current.UVIndex"         , "")
    
    for i in range(4):
      set_property("Day%i.Title"       % i , "")
      set_property("Day%i.HighTemp"    % i , "")
      set_property("Day%i.LowTemp"     % i , "")
      set_property("Day%i.Outlook"     % i , "")
      set_property("Day%i.OutlookIcon" % i , "")
      set_property("Day%i.FanartCode"  % i , "")

def refresh_locations():
  log("refresh_locations")
  location_set1 = __addon__.getSetting( "Location1" )
  location_set2 = __addon__.getSetting( "Location2" )
  location_set3 = __addon__.getSetting( "Location3" )
  locations = 0
  
  if location_set1 != "":
    locations += 1
    set_property('Location1'   , location_set1) # set location 1, XBMC needs this
  else:
    set_property('Location1'   , "")  
  if location_set2 != "":
    locations += 1 
    set_property('Location2'   , location_set2) # set location 2, XBMC needs this
  else:
    set_property('Location2'   , "")
  if location_set3 != "":
    locations += 1
    set_property('Location3'   , location_set3) # set location 3, XBMC needs this
  else:
    set_property('Location3'   , "")

  set_property('Locations',str(locations))      # set total number of locations, XBMC needs this

def fetch(url):
  log("fetch data from 'worldweatheronline.com'")
  socket = urllib.urlopen( url )
  result = socket.read()
  socket.close()
  xmldoc = minidom.parseString(result)
  return xmldoc
  
def get_elements(xml, tag):
   return xml.getElementsByTagName(tag)[0].firstChild.wholeText

def location(string):
  log("search for '%s'" % (string,))
  loc = []
  query   = fetch( SEARCH_URL % (DEVELOPER_KEY, string))
  locations = query.getElementsByTagName("result")
  for location in locations:
    try:
      loc.append("%s,%s,%s" % (get_elements(location, "areaName"), get_elements(location, "region"), get_elements(location, "country")))
    except:
      loc.append("%s,%s" % (get_elements(location, "areaName"), get_elements(location, "country")))
  return loc

def forecast(city):
  log("get forecast for '%s'" % (city,))
  query    = fetch( LOCATION_URL % (city, NUMBER_OF_DAYS, DEVELOPER_KEY))
  current  = query.getElementsByTagName("current_condition")[0]
  celsius  = get_elements(current,"temp_C")
  humidity = get_elements(current,"humidity")
  wind     = get_elements(current,"windspeedKmph")
  code     = get_elements(current,"weatherCode")
  desc     = get_elements(current,"weatherDesc")
  
  set_property("Current.Condition"       , desc)                                    # current condition in words
  set_property("Current.Temperature"     , celsius)                                 # temp in C, no need to set F, XBMC will convert it
  set_property("Current.Wind"            , wind)                                    # wind speed in Km/h, no need for mph as XBMC will do the conversion
  set_property("Current.Humidity"        , humidity)                                # Humidity in %
  set_property("Current.winddirection"   , get_elements(current,"winddir16Point"))  # wind direction
  set_property("Current.FeelsLike"       , getFeelsLike(int(celsius), int(wind)))   # Feels like
  set_property("Current.DewPoint"        , getDewPoint(int(celsius), int(humidity)))# Dew Point
  if (desc.startswith("Clear")):                                                    # condition icon, utilities.py has more on this
    set_property("Current.OutlookIcon"     , "%s.png" % "31")                       # fanart icon, utilities.py has more on this
    set_property("Current.FanartCode"      , "31")                                  # check for "Clear" and set the night image
  else:                                                                             # otherwise set sunny one
    set_property("Current.OutlookIcon"     , "%s.png" % WEATHER_CODES[code])        # 
    set_property("Current.FanartCode"      , WEATHER_CODES[code])                   # 
  set_property("Current.UVIndex"         , "")                                      # UV Index, not in WWO so we set blank 

  weather = query.getElementsByTagName("weather")
  i = 0  
  for day in weather:
    code = get_elements(day,"weatherCode")
    date = strptime(get_elements(day,"date"), '%Y-%m-%d')
    set_property("Day%i.Title"       % i , DAYS[int(strftime('%w', date))])         # Day of the week
    set_property("Day%i.HighTemp"    % i , get_elements(day,"tempMaxC"))            # Max Temp for that day, C only XBMC will do the conversion
    set_property("Day%i.LowTemp"     % i , get_elements(day,"tempMinC"))            # Min temperature for that day, C only XBMC will do the conversion
    set_property("Day%i.Outlook"     % i , get_elements(day,"weatherDesc"))         # days condition in words    
    set_property("Day%i.OutlookIcon" % i , "%s.png" % WEATHER_CODES[code])          # condition icon, utilities.py has more on this
    set_property("Day%i.FanartCode"  % i , WEATHER_CODES[code])                     # fanart icon, utilities.py has more on this
    i += 1

 
if sys.argv[1].startswith("Location"):                                              # call from addon settings to set the location                                       
  kb = xbmc.Keyboard("", xbmc.getLocalizedString(14024), False)                     #           (Location1, Location2 or Location3)
  kb.doModal()
  if (kb.isConfirmed() and kb.getText() != ""):
    text = kb.getText()
    locations = location(text)
    dialog = xbmcgui.Dialog()
    ret = dialog.select(xbmc.getLocalizedString(396), locations)
    if ret > -1:
      __addon__.setSetting( sys.argv[1], locations[ret] )
      log("addon setting - [%s] set to value [%s]" % (sys.argv[1], locations[ret],))
    
elif sys.argv[1] == "1" or sys.argv[1] == "2" or sys.argv[1] == "3":               # call from XBMC to collect data
                                                                                   #         for location 1, 2 or 3 
  location = __addon__.getSetting( "Location%s" % sys.argv[1])
  if location != "":
    log("addon called by XBMC for location '%s'" % (location,))
    forecast(location)
  else:
    clear_properties()   

refresh_locations()
set_property("WeatherProvider", "WorldWeatherOnline.com")                          # set name of the provider, this will be visible in the Weather page



