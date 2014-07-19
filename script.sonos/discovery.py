# -*- coding: utf-8 -*-
import sys
import os
import traceback
import xbmc
import xbmcaddon
import xbmcgui

__addon__ = xbmcaddon.Addon(id='script.sonos')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__version__ = __addon__.getAddonInfo('version')
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)


# Import the common settings
from settings import Settings
from settings import log
from settings import SocoLogging

import soco

log('script version %s started' % __version__)


###########################################################################
# This file will perform the lookup of a Sonos speaker and set it in
# the settings
###########################################################################
if __name__ == '__main__':

    # Set up the logging before using the Sonos Device
    if __addon__.getSetting("logEnabled") == "true":
        SocoLogging.enable()

    # Display the busy icon while searching for files
    xbmc.executebuiltin("ActivateWindow(busydialog)")

    try:
        sonos_devices = soco.discover()
    except:
        log("SonosDiscovery: Exception when getting devices")
        log("SonosDiscovery: %s" % traceback.format_exc())
        sonos_devices = []

    speakers = {}

    for device in sonos_devices:
        ip = device.ip_address
        log("SonosDiscovery: Getting info for IP address %s" % ip)

        playerInfo = None

        # Try and get the player info, if it fails then it is not a valid
        # player and we should continue to the next
        try:
            playerInfo = device.get_speaker_info()
        except:
            log("SonosDiscovery: IP address %s is not a valid player" % ip)
            log("SonosDiscovery: %s" % traceback.format_exc())
            continue

        # If player  info was found, then print it out
        if playerInfo is not None:
            # What is the name of the zone that this speaker is in?
            zone_name = playerInfo['zone_name']
            displayName = ip
            if (zone_name is not None) and (zone_name != ""):
                log("SonosDiscovery: Zone of %s is \"%s\"" % (ip, zone_name))
                displayName = "%s     [%s]" % (ip, zone_name)
            else:
                log("SonosDiscovery: No zone for IP address %s" % ip)
            speakers[displayName] = (ip, zone_name)

    # Remove the busy dialog
    xbmc.executebuiltin("Dialog.Close(busydialog)")

    # Check to see if there are any speakers
    if len(speakers) < 1:
        xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), __addon__.getLocalizedString(32014))
    else:
        # Now prompt the user to pick one of the speakers
        select = xbmcgui.Dialog().select(__addon__.getLocalizedString(32001), speakers.keys())

        if select != -1:
            selectedDisplayName = speakers.keys()[select]
            log("SonosDiscovery: Entry chosen = %s" % selectedDisplayName)
            chosenIPAddress = speakers.get(selectedDisplayName)[0]
            chosenZoneName = speakers.get(selectedDisplayName)[1]
            # Set the selected item into the settings
            Settings.setIPAddress(chosenIPAddress)
            Settings.setZoneName(chosenZoneName)
