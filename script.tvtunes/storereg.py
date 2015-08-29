# -*- coding: utf-8 -*-
import os
import sys
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui


__addon__ = xbmcaddon.Addon(id='script.tvtunes')
__addonid__ = __addon__.getAddonInfo('id')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)


from settings import log
from settings import dir_exists


##################################
# Main of the TvTunes Service
##################################
if __name__ == '__main__':
    log("StoreReg: Starting TvTunes Store Registration %s" % __addon__.getAddonInfo('version'))

    # Prompt the user for the location of the registration file
    fileLocation = xbmcgui.Dialog().browseSingle(1, __addon__.getLocalizedString(32116), 'files')

    if fileLocation not in ["", None]:
        log("StoreReg: Registration file selected: %s" % fileLocation)

        # Make sure the target directory exists
        if not dir_exists(xbmc.translatePath('special://profile/addon_data/%s' % __addonid__).decode("utf-8")):
            xbmcvfs.mkdir(xbmc.translatePath('special://profile/addon_data/%s' % __addonid__).decode("utf-8"))

        # Get the location the file is to be copied to
        tvtunesStoreFileName = xbmc.translatePath('special://profile/addon_data/%s/tvtunes-store-reg.xml' % __addonid__).decode("utf-8")

        log("StoreReg: Target location of registration file: %s" % tvtunesStoreFileName)

        # Copy the file into the target location
        copy = xbmcvfs.copy(fileLocation, tvtunesStoreFileName)
        if copy:
            log("StoreReg: Registration file copy successful")
        else:
            log("StoreReg: Registration file copy failed")
            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32116), __addon__.getLocalizedString(32117))
    else:
        log("StoreReg: No registration file selected")
