# -*- coding: utf-8 -*-
import sys
import xbmc

if sys.version_info >= (2, 7):
    import json
else:
    import simplejson as json

# Import the common settings
from settings import log


# Class that provides utility methods to lookup Addon information
class Collector:

    # Method to get all the screensavers that are installed and not marked as broken
    @staticmethod
    def getInstalledScreensavers():
        log("getInstalledScreensavers")

        # Make the call to find out all the screensaver addons that are installed
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": { "type": "xbmc.ui.screensaver", "enabled": true, "properties": ["broken"] }, "id": 1}')

        json_response = json.loads(json_query)

        screensavers = []

        if ("result" in json_response) and ('addons' in json_response['result']):
            # Check each of the screensavers that are installed on the system
            for addonItem in json_response['result']['addons']:
                addonName = addonItem['addonid']
                # Need to skip the 2 build in screensavers are they can not be triggered
                # and are a bit dull, so should not be in the mix
                if addonName in ['screensaver.xbmc.builtin.black', 'screensaver.xbmc.builtin.dim']:
                    log("RandomScreensaver: Skipping built-in screensaver: %s" % addonName)
                    continue

                # Need to skip the operation type screensaver, things like screensavers that
                # send to sleep and prompt for a Pin
                if addonName in ['script.pinsentry', 'script.sleep']:
                    log("RandomScreensaver: Skipping operation screensaver: %s" % addonName)
                    continue

                # Skip ourselves as we don't want to random a random!
                if addonName in ['screensaver.random']:
                    log("RandomScreensaver: Detected ourself: %s" % addonName)
                    continue

                # Need to ensure we skip any screensavers that are flagged as broken
                if addonItem['broken']:
                    log("RandomScreensaver: Skipping broken screensaver: %s" % addonName)
                    continue

                # Now we are left with only the addon screensavers
                log("RandomScreensaver: Detected Screensaver Addon: %s" % addonName)
                screensavers.append(addonName)

        return screensavers

    # Get the screensavers that can not be launched as a script
    @staticmethod
    def getUnsupportedScreensavers(screensavers):
        log("getUnsupportedScreensavers")

        # Ideally we would check each addon we have already identified using the Addons.GetAddonDetails
        # API, however that will only return the primary type, and we are actually looking for
        # the script option as just one of the supported types
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": { "type": "xbmc.python.script" }, "id": 1}')

        json_response = json.loads(json_query)

        scriptaddons = []
        # Extract the addon ids from the response
        if ("result" in json_response) and ('addons' in json_response['result']):
            # Check each of the screensavers that are installed on the system
            for addonItem in json_response['result']['addons']:
                addonName = addonItem['addonid']
                scriptaddons.append(addonName)

        # Now check each of the addons we have to see if they support being launched as a script
        unsupportedScreensavers = []
        for screensaverAddon in screensavers:
            if screensaverAddon not in scriptaddons:
                log("RandomScreensaver: Screensaver %s does not support launching as a script" % screensaverAddon)
                unsupportedScreensavers.append(screensaverAddon)

        return unsupportedScreensavers
