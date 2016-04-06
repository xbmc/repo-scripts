# -*- coding: utf-8 -*-
import sys
import xbmc
import xbmcaddon
import xbmcgui

if sys.version_info >= (2, 7):
    import json
else:
    import simplejson as json

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings

ADDON = xbmcaddon.Addon(id='service.addonsync')


#########################
# Main
#########################
if __name__ == '__main__':
    log("AddonFilter: Include / Exclude Filter (version %s)" % ADDON.getAddonInfo('version'))

    # Get the type of filter that is being applied
    filterType = Settings.getFilterType()

    if filterType == Settings.FILTER_ALL:
        log("AddonFilter: Filter called when there is no filter required")
    else:
        # Make the call to find out all the addons that are installed
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": { "enabled": true, "properties": ["name", "broken"] }, "id": 1}')
        json_response = json.loads(json_query)

        addons = {}

        if ("result" in json_response) and ('addons' in json_response['result']):
            # Check each of the screensavers that are installed on the system
            for addonItem in json_response['result']['addons']:
                addonName = addonItem['addonid']
                # Need to skip the 2 build in screensavers are they can not be triggered
                # and are a bit dull, so should not be in the mix
                if addonName in ['screensaver.xbmc.builtin.black', 'screensaver.xbmc.builtin.dim', 'service.xbmc.versioncheck']:
                    log("AddonFilter: Skipping built-in addons: %s" % addonName)
                    continue

                if addonName.startswith('metadata'):
                    log("AddonFilter: Skipping metadata addon: %s" % addonName)
                    continue
                if addonName.startswith('resource.language'):
                    log("AddonFilter: Skipping resource.language addon: %s" % addonName)
                    continue
                if addonName.startswith('repository'):
                    log("AddonData: Skipping repository addon: %s" % addonName)
                    continue
                if addonName.startswith('skin'):
                    log("AddonData: Skipping skin addon: %s" % addonName)
                    continue

                # Skip ourselves as we don't want to update a slave with a master
                if addonName in ['service.addonsync']:
                    log("AddonFilter: Detected ourself: %s" % addonName)
                    continue

                # Need to ensure we skip any addons that are flagged as broken
                if addonItem['broken']:
                    log("AddonFilter: Skipping broken addon: %s" % addonName)
                    continue

                # Now we are left with only the working addon
                log("AddonFilter: Detected Addon: %s (%s)" % (addonName, addonItem['name']))
                addons[addonItem['name']] = addonName

        if len(addons) < 1:
            log("AddonFilter: No Addons installed")
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32011).encode('utf-8'))
        else:
            # Get the names of the addons and order them
            addonNames = list(addons.keys())
            addonNames.sort()
            selection = None
            try:
                selection = xbmcgui.Dialog().multiselect(ADDON.getLocalizedString(32001), addonNames)
            except:
                # Multi select is only available for releases v16 onwards, fall back to single select
                log("AddonFilter: Multi Select Not Supported, using single select")
                tempSelection = xbmcgui.Dialog().select(ADDON.getLocalizedString(32001), addonNames)
                if tempSelection > -1:
                    selection = []
                    selection.append(tempSelection)

            # Check the cancel selection
            if selection is not None:
                # Clear the previously saved values
                Settings.setExcludedAddons()
                Settings.setIncludedAddons()

                if len(selection) > 0:
                    addonList = []
                    for addonSelection in selection:
                        addonName = addonNames[addonSelection]
                        log("AddonFilter: Selected addon %d (%s)" % (addonSelection, addonName))
                        addonList.append(addons[addonName])

                    # Make a space separated string from the list
                    addonSpaceList = ' '.join(addonList)

                    if filterType == Settings.FILTER_EXCLUDE:
                        Settings.setExcludedAddons(addonSpaceList)
                    else:
                        Settings.setIncludedAddons(addonSpaceList)
