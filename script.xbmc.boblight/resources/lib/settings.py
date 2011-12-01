'''
    Boblight for XBMC
    Copyright (C) 2011 Team XBMC

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import sys
import time
import xbmc
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__settings__   = sys.modules[ "__main__" ].__settings__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__icon__       = sys.modules[ "__main__" ].__icon__
sys.path.append (__cwd__)

from boblight import *

#general
global g_networkaccess
global g_hostip
global g_hostport
#movie/musicvideo/other
global g_saturation 
global g_value 
global g_speed 
global g_autospeed 
global g_interpolation 
global g_threshold
global g_timer
global g_category
global g_bobdisable
global g_staticBobActive
global g_overwrite_cat
global g_overwrite_cat_val

#init globals with defaults
def settings_initGlobals():
  global g_networkaccess
  global g_hostip
  global g_hostport  
  global g_saturation 
  global g_value 
  global g_speed 
  global g_autospeed 
  global g_interpolation 
  global g_threshold
  global g_networkaccess
  global g_hostip
  global g_hostport  
  global g_timer
  global g_category
  global g_bobdisable
  global g_staticBobActive
  global g_overwrite_cat
  global g_overwrite_cat_val

  g_networkaccess  = False
  g_hostip         = "127.0.0.1"
  g_hostport       = None
  g_saturation     = -1.0 
  g_value          = -1.0
  g_speed          = -1.0
  g_autospeed      = -1.0
  g_interpolation  = -1
  g_threshold      = -1.0
  g_networkaccess  = __settings__.getSetting("networkaccess") == "true"
  g_hostip         = __settings__.getSetting("hostip")
  g_hostport       = int(__settings__.getSetting("hostport"))  
  g_timer          = time.time()
  g_category       = "movie"
  g_bobdisable     = -1
  g_staticBobActive = False
  g_overwrite_cat = False
  g_overwrite_cat_val = 0
  
  if not g_networkaccess:
    g_hostip   = None
    g_hostport = -1

def settings_getHostIp():
  global g_hostip
  return g_hostip

def settings_getHostPort():
  global g_hostport
  return g_hostport 

def settings_getBobDisable():
  global g_bobdisable
  return g_bobdisable

def settings_isStaticBobActive():
  global g_staticBobActive
  return g_staticBobActive

#configures boblight for the initial bling bling
def settings_confForBobInit():
  saturation,value,speed,autospeed,interpolation,threshold = settings_setupForStatic()
  bob_setoption("saturation    " + str(saturation))
  bob_setoption("value         " + str(value))
  bob_setoption("speed         " + str(speed))
  bob_setoption("autospeed     " + str(autospeed))
  bob_setoption("interpolation " + str(interpolation))
  bob_setoption("threshold     " + str(threshold))

#returns the settings category based on the currently played media
#returns "movie" if a movies is played, "musicvideo" if a musicvideo is played", "other" else
def settings_getSettingCategory():                 
  ret = "other"

  playing = xbmc.getCondVisibility("Player.HasVideo")

  if playing:		#we play something
    ret = "movie"
    musicvideo = xbmc.getCondVisibility("VideoPlayer.Content(musicvideos)")
    if musicvideo:
      ret = "musicvideo"

  if g_overwrite_cat and ret != "other":				#fix his out when other isn't the static light anymore
    if g_overwrite_cat_val == 0:
      ret = "movie"
    else:
      ret = "musicvideo"

  return ret
  
#check for new settings and handle them if anything changed
#only checks if the last check is 5 secs old
#returns if a reconnect is needed due to settings change
def settings_checkForNewSettings():
#todo  for now impl. stat on addon.getAddonInfo('profile')/settings.xml and use mtime
#check for new settings every 5 secs
  global g_timer
  reconnect = False

  if time.time() - g_timer > 5:
    reconnect = settings_setup()
    g_timer = time.time()
  return reconnect

#handle boblight configuration from the "Movie" category
#returns the new settings
def settings_setupForMovie(): 
  preset = int(__settings__.getSetting("movie_preset"))

  if preset == 1:       #preset smooth
    saturation    = 3.0
    value         = 10.0
    speed         = 20.0
    autospeed     = 0.0 
    interpolation = 0
    threshold     = 0.0
  elif preset == 2:     #preset action
    saturation    = 3.0
    value         = 10.0
    speed         = 80.0
    autospeed     = 0.0  
    interpolation = 0
    threshold     = 0.0
  elif preset == 0:     #custom
    saturation      =  float(__settings__.getSetting("movie_saturation"))
    value           =  float(__settings__.getSetting("movie_value"))
    speed           =  float(__settings__.getSetting("movie_speed"))
    autospeed       =  float(__settings__.getSetting("movie_autospeed"))
    interpolation   =  __settings__.getSetting("movie_interpolation") == "true"
    threshold       =  float(__settings__.getSetting("movie_threshold"))
  return (saturation,value,speed,autospeed,interpolation,threshold)

#handle boblight configuration from the "MusicVideo" category
#returns the new settings
def settings_setupForMusicVideo():
  preset = int(__settings__.getSetting("musicvideo_preset"))

  if preset == 1:       #preset Ballad
    saturation    = 3.0
    value         = 10.0
    speed         = 20.0  
    autospeed     = 0.0
    interpolation = 1
    threshold     = 0.0
  elif preset == 2:     #preset Rock
    saturation    = 3.0
    value         = 10.0
    speed         = 80.0
    autospeed     = 0.0  
    interpolation = 0
    threshold     = 0.0
  elif preset == 0:     #custom
    saturation      =  float(__settings__.getSetting("musicvideo_saturation"))
    value           =  float(__settings__.getSetting("musicvideo_value"))
    speed           =  float(__settings__.getSetting("musicvideo_speed"))
    autospeed       =  float(__settings__.getSetting("movie_autospeed"))
    interpolation   =  __settings__.getSetting("musicvideo_interpolation") == "true"
    threshold       =  float(__settings__.getSetting("musicvideo_threshold"))
  return (saturation,value,speed,autospeed,interpolation,threshold)

#handle boblight configuration from the "other" category
#returns the new settings
def settings_setupForOther():
# FIXME don't use them for now - reactivate when boblight works on non rendered scenes (e.x. menu)
#  saturation      =  float(__settings__.getSetting("other_saturation"))
#  value           =  float(__settings__.getSetting("other_value"))
#  speed           =  float(__settings__.getSetting("other_speed"))
#  autospeed       =  float(__settings__.getSetting("other_autospeed"))
#  interpolation   =  __settings__.getSetting("other_interpolation") == "true"
#  threshold       =  float(__settings__.getSetting("other_threshold"))
  return settings_setupForStatic()

#handle boblight configuration for static lights
#returns the new settings
def settings_setupForStatic():
  saturation    = 4.0
  value         = 1.0
  speed         = 50.0
  autospeed     = 0.0 
  interpolation = 1
  threshold     = 0.0
  return (saturation,value,speed,autospeed,interpolation,threshold)

  
#handle all settings in the general tab according to network access
#returns true if reconnect is needed due to network changes
def settings_handleNetworkSettings():
  global g_networkaccess
  global g_hostip
  global g_hostport
  reconnect = False

  networkaccess = __settings__.getSetting("networkaccess") == "true"
  hostip        = __settings__.getSetting("hostip")
  hostport      = int(__settings__.getSetting("hostport"))

  #server settings
  #we need to reconnect if networkaccess bool changes
  #or if network access is enabled and ip or port have changed
  if g_networkaccess != networkaccess or ((g_hostip != hostip or g_hostport != hostport) and g_networkaccess) :
    print "boblight: changed networkaccess to " + str(networkaccess)
    g_networkaccess = networkaccess

    if not networkaccess:
      g_hostip = None
      g_hostport = -1
    else:
      if g_hostip != hostip:
        print "boblight: changed hostip to " + str(hostip)
        g_hostip = hostip
    
      if g_hostport != hostport:
        print "boblight: changed hostport to " + str(hostport)
        g_hostport = hostport
    reconnect = True
  return reconnect

#handle all settings according to the static bg light
#this is used until category "other" can do real boblight
#when no video is rendered
#category - the category we are in currently
def settings_handleStaticBgSettings(category):
  global g_staticBobActive
  other_static_bg     = __settings__.getSetting("other_static_bg") == "true"
  other_static_red    = int(float(__settings__.getSetting("other_static_red")))
  other_static_green  = int(float(__settings__.getSetting("other_static_green")))
  other_static_blue   = int(float(__settings__.getSetting("other_static_blue")))
  
  if category == "other" and other_static_bg and not g_bobdisable:#for now enable static light on other if settings want this
    bob_set_priority(128)                                  #allow lights to be turned on
    rgb = (c_int * 3)(other_static_red,other_static_green,other_static_blue)
    bob_set_static_color(byref(rgb))
    g_staticBobActive = True
  else:
    g_staticBobActive = False

#handles the boblight configuration of all categorys
#and applies changed settings to boblight
#"movie","musicvideo" and "other
#returns if a setting has been changed
def settings_handleGlobalSettings(category):
  global g_saturation 
  global g_value 
  global g_speed 
  global g_autospeed 
  global g_interpolation 
  global g_threshold
  settingChanged = False

  #call the right setup function according to categroy
  #switch case in python - dictionary with function pointers
  option = { "movie"      : settings_setupForMovie,
             "musicvideo" : settings_setupForMusicVideo,
             "other"      : settings_setupForOther,
  }
  saturation,value,speed,autospeed,interpolation,threshold = option[category]()

  #setup boblight - todo error checking
  if g_saturation != saturation:  
    ret = bob_setoption("saturation    " + str(saturation))
    settingChanged = True
    print "boblight: changed saturation to " + str(saturation) + "(ret " + str(ret) + ")"
    g_saturation = saturation
  
  if g_value != value:  
    ret = bob_setoption("value         " + str(value))
    settingChanged = True
    print "boblight: changed value to " + str(value) + "(ret " + str(ret) + ")"
    g_value = value

  if g_speed != speed:  
    ret = bob_setoption("speed         " + str(speed))
    settingChanged = True
    print "boblight: changed speed to " + str(speed) + "(ret " + str(ret) + ")"
    g_speed = speed

  if g_autospeed != autospeed:  
    ret = bob_setoption("autospeed     " + str(autospeed))
    settingChanged = True
    print "boblight: changed autospeed to " + str(autospeed) + "(ret " + str(ret) + ")"
    g_autospeed = autospeed

  if g_interpolation != interpolation:  
    ret = bob_setoption("interpolation " + str(interpolation))
    settingChanged = True
    print "boblight: changed interpolation to " + str(interpolation) + "(ret " + str(ret) + ")"
    g_interpolation = interpolation

  if g_threshold != threshold:  
    ret = bob_setoption("threshold     " + str(threshold))
    settingChanged = True
    print "boblight: changed threshold to " + str(threshold) + "(ret " + str(ret) + ")"
    g_threshold = threshold
  return settingChanged

#handle change of category we are in
#"movie","musicvideo" or "other"
#returns if category has changed  
def settings_handleCategory(category):
  global g_category
  categoryChanged = False

  if g_category != category:
    categoryChanged = True				#don't change notify when category changes
    print "boblight: use settings for " + category
    g_category = category   
  return categoryChanged

#handle bob disable setting
#sets the global g_bobdisable and prints
#toast dialog on disable
def settings_handleDisableSetting():
  global g_bobdisable
  bobdisable  = __settings__.getSetting("bobdisable") == "true"  
    
  if g_bobdisable != bobdisable:
    if bobdisable:
      text = __settings__.getLocalizedString(503)
      xbmc.executebuiltin("XBMC.Notification(%s,%s,%s,%s)" % (__scriptname__,text,10,__icon__))
      print "boblight: boblight disabled"
    else:
      print "boblight: boblight enabled"
    g_bobdisable = bobdisable 

#handles all settings of boblight and applies them as needed
#returns if a reconnect is needed due to settings changes
def settings_setup():  
  global g_overwrite_cat
  global g_overwrite_cat_val
  reconnect = False
  settingChanged = False
  categoryChanged = False

  g_overwrite_cat = __settings__.getSetting("overwrite_cat") == "true"
  g_overwrite_cat_val = int(__settings__.getSetting("overwrite_cat_val"))

  category = settings_getSettingCategory()
  categoryChanged = settings_handleCategory(category)
  reconnect = settings_handleNetworkSettings()
  settingChanged = settings_handleGlobalSettings(category)
  settings_handleStaticBgSettings(category)
  settings_handleDisableSetting()

  #notify user via toast dialog when a setting was changed (beside category changes)
  if settingChanged and not categoryChanged:
    text = __settings__.getLocalizedString(502)
    xbmc.executebuiltin("XBMC.Notification(%s,%s,%s,%s)" % (__scriptname__,text,10,__icon__))

  return reconnect
  
