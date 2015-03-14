# -*- coding: utf-8 -*-
import sys
import os
import traceback
import socket
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
    log("SonosDiscovery: Searching for Sonos devices")

    # Set up the logging before using the Sonos Device
    SocoLogging.enable()

    # Display the busy icon while searching for files
    xbmc.executebuiltin("ActivateWindow(busydialog)")

    # Use the default method to search for Sonos Devices
    try:
        sonos_devices = soco.discover(timeout=5)
    except:
        log("SonosDiscovery: Exception when getting devices", xbmc.LOGERROR)
        log("SonosDiscovery: %s" % traceback.format_exc(), xbmc.LOGERROR)
        sonos_devices = []

    # If there are multiple network devices, then this may not have picked up
    # the correct network device to broadcast on, so try another way
    if (sonos_devices is None) or (len(sonos_devices) < 1):
        try:
            # Try and find the address ourselves
            interfaceAddr = socket.gethostbyname(socket.gethostname())
            log("SonosDiscovery: Searching for devices using gethostname %s" % interfaceAddr)
            if interfaceAddr not in [None, '']:
                sonos_devices = soco.discover(timeout=5, interface_addr=interfaceAddr)
        except:
            log("SonosDiscovery: Exception when getting devices", xbmc.LOGERROR)
            log("SonosDiscovery: %s" % traceback.format_exc(), xbmc.LOGERROR)
            sonos_devices = []

    # If still not found, try yet another method
    if (sonos_devices is None) or (len(sonos_devices) < 1):
        try:
            # Try and find the address ourselves
            interfaceAddr = socket.gethostbyname(socket.getfqdn())
            log("SonosDiscovery: Searching for devices using getfqdn %s" % interfaceAddr)
            if interfaceAddr not in [None, '']:
                sonos_devices = soco.discover(timeout=5, interface_addr=interfaceAddr)
        except:
            log("SonosDiscovery: Exception when getting devices", xbmc.LOGERROR)
            log("SonosDiscovery: %s" % traceback.format_exc(), xbmc.LOGERROR)
            sonos_devices = []

    # If still not found, try the last option
    if (sonos_devices is None) or (len(sonos_devices) < 1):
        try:
            # Try and find the address ourselves by going to a web page
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("sonos.com", 80))
            interfaceAddr = s.getsockname()[0]
            s.close()
            log("SonosDiscovery: Searching for devices using web search %s" % interfaceAddr)
            if interfaceAddr not in [None, '']:
                sonos_devices = soco.discover(timeout=5, interface_addr=interfaceAddr)
        except:
            log("SonosDiscovery: Exception when getting devices", xbmc.LOGERROR)
            log("SonosDiscovery: %s" % traceback.format_exc(), xbmc.LOGERROR)
            sonos_devices = []

    speakers = {}

    # Check for the case where discovery did not return anything
    if sonos_devices is None:
        log("SonosDiscovery: Search returned None")
        sonos_devices = []

    for device in sonos_devices:
        ip = device.ip_address
        log("SonosDiscovery: Getting info for IP address %s" % ip)

        playerInfo = None

        # Try and get the player info, if it fails then it is not a valid
        # player and we should continue to the next
        try:
            playerInfo = device.get_speaker_info()
        except:
            log("SonosDiscovery: IP address %s is not a valid player" % ip, xbmc.LOGERROR)
            log("SonosDiscovery: %s" % traceback.format_exc(), xbmc.LOGERROR)
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
            # Record if this is the group coordinator, as when there are several
            # speakers in the group, we need to send messages to the group
            # coordinator for things to work correctly
            isCoordinator = device.is_coordinator
            if isCoordinator:
                log("SonosDiscovery: %s is the group coordinator" % ip)
                displayName = "%s - %s" % (displayName, __addon__.getLocalizedString(32031))
            else:
                log("SonosDiscovery: %s is not the group coordinator" % ip)

            speakers[displayName] = (ip, zone_name, isCoordinator)

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
            chosenIsCoordinator = speakers.get(selectedDisplayName)[2]

            # Warn the user if they have selected something that is not the zone coordinator
            if not chosenIsCoordinator:
                xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001),
                                    "%s %s:" % (chosenIPAddress, __addon__.getLocalizedString(32032)),
                                    "          \"%s\"" % chosenZoneName,
                                    __addon__.getLocalizedString(32033))
            # Set the selected item into the settings
            Settings.setIPAddress(chosenIPAddress)
            Settings.setZoneName(chosenZoneName)
