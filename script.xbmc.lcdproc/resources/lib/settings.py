'''
    XBMC LCDproc addon
    Copyright (C) 2012 Team XBMC
    Copyright (C) 2012 Daniel 'herrnst' Scheller
    
    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
    
    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import string
import sys
import time
import xbmc

__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__settings__   = sys.modules[ "__main__" ].__settings__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__icon__       = sys.modules[ "__main__" ].__icon__
sys.path.append (__cwd__)

#general
global g_hostip
global g_hostport
global g_timer
global g_heartbeat
global g_scrolldelay
global g_scrollmode
global g_settingsChanged
global g_dimonscreensaver
global g_dimonshutdown
global g_navtimeout
global g_refreshrate
global g_hideconnpopups

#init globals with defaults
def settings_initGlobals():
  global g_hostip
  global g_hostport  
  global g_timer
  global g_heartbeat
  global g_scrolldelay
  global g_scrollmode
  global g_settingsChanged
  global g_dimonscreensaver
  global g_dimonshutdown
  global g_navtimeout
  global g_refreshrate
  global g_hideconnpopups

  g_hostip           = "127.0.0.1"
  g_hostport         = 13666
  g_timer            = time.time()   
  g_heartbeat        = False
  g_scrolldelay      = 1
  g_scrollmode       = "0"
  g_settingsChanged  = True
  g_dimonscreensaver = False
  g_dimonshutdown    = False
  g_navtimeout       = 3
  g_refreshrate      = 1
  g_hideconnpopups   = True

def settings_getHostIp():
  global g_hostip
  return g_hostip

def settings_getHostPort():
  global g_hostport
  return g_hostport 

def settings_getHeartBeat():
  global g_heartbeat
  return g_heartbeat

def settings_getScrollDelay():
  global g_scrolldelay
  return g_scrolldelay

def settings_getScrollMode():
  global g_scrollmode
  return g_scrollmode

def settings_getLCDprocScrollMode():
  global g_scrollmode
  if g_scrollmode == "1":
    return "h"
  return "m"

def settings_getDimOnScreensaver():
  global g_dimonscreensaver
  return g_dimonscreensaver

def settings_getDimOnShutdown():
  global g_dimonshutdown
  return g_dimonshutdown

def settings_getNavTimeout():
  global g_navtimeout
  return g_navtimeout

def settings_getRefreshRate():
  global g_refreshrate
  return g_refreshrate

def settings_getHideConnPopups():
  global g_hideconnpopups
  return g_hideconnpopups

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
  
def settings_didSettingsChange():
  global g_settingsChanged
  settingsChanged = g_settingsChanged
  g_settingsChanged = False
  return settingsChanged
  
#handle all settings in the general tab according to network access
#returns true if reconnect is needed due to network changes
def settings_handleNetworkSettings():
  global g_hostip
  global g_hostport
  global g_heartbeat

  reconnect = False

  hostip    = __settings__.getSetting("hostip")
  hostport  = int(__settings__.getSetting("hostport"))
  heartbeat = __settings__.getSetting("heartbeat") == "true"

  #server settings
  #we need to reconnect if networkaccess bool changes
  #or if network access is enabled and ip or port have changed
  if g_hostip != hostip or g_hostport != hostport or g_heartbeat != heartbeat:
    if g_hostip != hostip:
      print "lcd: changed hostip to " + str(hostip)
      g_hostip = hostip
      reconnect = True

    if g_hostport != hostport:

      # make sure valid port number was given
      if hostport > 0 and hostport < 65536:
        print "lcd: changed hostport to " + str(hostport)
        g_hostport = hostport
        reconnect = True
      else:
        print "lcd: invalid hostport value " + str(hostport) + ", resetting to old value " + str(g_hostport)

      __settings__.setSetting("hostport", str(g_hostport))

    if g_heartbeat != heartbeat:
      print "lcd: toggled heartbeat bool"
      g_heartbeat = heartbeat
      reconnect = True

  return reconnect

def settings_handleLcdSettings():
  global g_scrolldelay
  global g_scrollmode
  global g_heartbeat
  global g_settingsChanged
  global g_dimonscreensaver
  global g_dimonshutdown
  global g_navtimeout
  global g_refreshrate
  global g_hideconnpopups

  g_settingsChanged = False

  scrolldelay = int(float(string.replace(__settings__.getSetting("scrolldelay"), ",", ".")))
  scrollmode = __settings__.getSetting("scrollmode")
  dimonscreensaver = __settings__.getSetting("dimonscreensaver") == "true"
  dimonshutdown = __settings__.getSetting("dimonshutdown") == "true"
  navtimeout = int(float(string.replace(__settings__.getSetting("navtimeout"), ",", ".")))
  refreshrate = int(float(string.replace(__settings__.getSetting("refreshrate"), ",", ".")))
  hideconnpopups = __settings__.getSetting("hideconnpopups") == "true"
 
  if g_scrolldelay != scrolldelay:
    g_scrolldelay = scrolldelay
    g_settingsChanged = True

  if g_scrollmode != scrollmode:
    g_scrollmode = scrollmode
    g_settingsChanged = True

  if g_dimonscreensaver != dimonscreensaver:
    g_dimonscreensaver = dimonscreensaver
    g_settingsChanged = True

  if g_dimonshutdown != dimonshutdown:
    g_dimonshutdown = dimonshutdown
    g_settingsChanged = True
    
  if g_navtimeout != navtimeout:
    g_navtimeout = navtimeout
    g_settingsChanged = True    

  if g_refreshrate != refreshrate:
    g_refreshrate = refreshrate

    if refreshrate < 1:
      g_refreshrate = 1

    g_settingsChanged = True    

  if g_hideconnpopups != hideconnpopups:
    g_hideconnpopups = hideconnpopups
    g_settingsChanged = True

#handles all settings and applies them as needed
#returns if a reconnect is needed due to settings changes
def settings_setup():  
  reconnect = False
  reconnect = settings_handleNetworkSettings()
  settings_handleLcdSettings()

  return reconnect
  
