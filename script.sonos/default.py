# -*- coding: utf-8 -*-
import sys
import os
import traceback
import xbmc
import xbmcaddon
import xbmcgui

__addon__     = xbmcaddon.Addon(id='script.sonos')
__addonid__   = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__cwd__       = __addon__.getAddonInfo('path').decode("utf-8")
__version__   = __addon__.getAddonInfo('version')
__icon__      = __addon__.getAddonInfo('icon')
__resource__  = xbmc.translatePath( os.path.join( __cwd__, 'resources' ).encode("utf-8") ).decode("utf-8")
__lib__  = xbmc.translatePath( os.path.join( __resource__, 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

from soco import SoCo
from soco import SonosDiscovery
from soco import SoCoException


def log(txt):
    if __addon__.getSetting( "logEnabled" ) == "true":
        if isinstance (txt,str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

log('script version %s started' % __version__)

##############################
# Stores Addon Settings
##############################
class Settings():

    @staticmethod
    def getIPAddress():
        return __addon__.getSetting("ipAddress")

    @staticmethod
    def getNotificationDisplayDuration():
        # Convert to milliseconds before returning
        return int(float(__addon__.getSetting("notifDisplayDuration"))) * 1000

    @staticmethod
    def getNotificationCheckFrequency():
        # Convert to milliseconds before returning
        return int(float(__addon__.getSetting("notifCheckFrequency"))) * 1000

    @staticmethod
    def useXbmcNotifDialog():
        return __addon__.getSetting("xbmcNotifDialog") == 'true'




###########################################################################
# NOTE
# ====
# This section is all temporary - it is just to show what future versions
# will be able to do
###########################################################################

if __name__ == '__main__':
    
    ipAddress = Settings.getIPAddress()

    log("Sonos: IP Address = %s" % ipAddress)

    # Make sure the IP Address has been set
    if ipAddress != "0.0.0.0":
        sonosDevice = SoCo(ipAddress)

        # Display a simple selection dialog for now
        menuItems = ['Play', 'Pause', 'Stop', 'Next Track', 'Previous', 'LED On', 'LED Off', 'Exit']

        select = xbmcgui.Dialog().select(__addon__.getLocalizedString(32001), menuItems)

        try:
            # Play was requested
            if select == 0:
                log("Sonos: Play Requested")
                sonosDevice.play()
            
            # Pause was requested
            elif select == 1:
                log("Sonos: Pause Requested")
                sonosDevice.pause()
    
            # Stop was requested
            elif select == 2:
                log("Sonos: Stop Requested")
                sonosDevice.stop()
    
            # Next was requested
            elif select == 3:
                log("Sonos: Next Track Requested")
                sonosDevice.next()
    
            # Previous was requested
            elif select == 4:
                log("Sonos: Previous Track Requested")
                sonosDevice.previous()
    
            # Turn Status Light On
            elif select == 5:
                log("Sonos: LED On Requested")
                sonosDevice.status_light(True)
    
            # Turn Status Light Off
            elif select == 6:
                log("Sonos: LED Off Requested")
                sonosDevice.status_light(False)

        except:
            # Failed to connect to the Sonos Speaker
            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), ("Error from speaker %s" % ipAddress))
            log("Sonos: Exception Details: %s" % traceback.format_exc())

    else:
        xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), "IP Address Not Set")
        
