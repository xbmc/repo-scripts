# -*- coding: utf-8 -*-
import sys
import os
import traceback
import xbmc
import xbmcaddon
import xbmcgui

__addon__     = xbmcaddon.Addon(id='script.sonos')
__addonid__   = __addon__.getAddonInfo('id')
__cwd__       = __addon__.getAddonInfo('path').decode("utf-8")
__version__   = __addon__.getAddonInfo('version')
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


###########################################################################
# This file will perform the lookup of a Sonos speaker and set it in
# the settings
###########################################################################

if __name__ == '__main__':
   
    # Display the busy icon while searching for files
    xbmc.executebuiltin( "ActivateWindow(busydialog)" )
    
    # Get all the devices and look at each one, logging it's IP address
    sonos_devices = SonosDiscovery()
    
    try:
        ipAddresses = sonos_devices.get_speaker_ips()
        log("SonosDiscovery: IP Addresses = %s" % str(ipAddresses))
    except:
        log("SonosDiscovery: Exception when getting devices")
        ipAddresses = []

    speakers = {}

    for ip in ipAddresses:
        log("SonosDiscovery: Getting info for IP address %s" % ip)
        # Pass in the IP address of the Sonos Speaker
        device = SoCo(ip)

        playerInfo = None

        # Try and get the player info, if it fails then it is not a valid
        # player and we should continue to the next
        try:
            playerInfo = device.get_speaker_info()
        except:
            log("SonosDiscovery: IP address %s is not a valid player" % ip)
            continue

        # If player  info was found, then print it out
        if playerInfo != None:
            # What is the name of the zone that this speaker is in?
            zone_name = playerInfo['zone_name']
            displayName = ip
            if (zone_name != None) and (zone_name != ""):
                log("SonosDiscovery: Zone of %s is \"%s\"" % (ip, zone_name))
                displayName = "%s     [%s]" % (ip, zone_name)
            else:
                log("SonosDiscovery: No zone for IP address %s" % ip)
            speakers[displayName] = ip

    # Remove the busy dialog
    xbmc.executebuiltin( "Dialog.Close(busydialog)" )

    # Check to see if there are any speakers
    if len(speakers) < 1:
        xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), __addon__.getLocalizedString(32014))
    else:
        # Now prompt the user to pick one of the 
        select = xbmcgui.Dialog().select(__addon__.getLocalizedString(32001), speakers.keys())

        if select != -1:
            selectedDisplayName = speakers.keys()[select]
            log("SonosDiscovery: Entry chosen = %s" % selectedDisplayName)
            chosenIPAddress = speakers.get(selectedDisplayName)
            # Set the selected item into the settings
            __addon__.setSetting("ipAddress", chosenIPAddress)

