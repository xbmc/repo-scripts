# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcaddon


__addon__ = xbmcaddon.Addon(id='script.videoextras')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import log


#########################
# Main
#########################
if __name__ == '__main__':
    currentPath = xbmc.getInfoLabel("ListItem.FilenameAndPath")

    if currentPath in [None, ""]:
        currentPath = xbmc.getInfoLabel("ListItem.Path")

    log("VideoExtras: Context menu called for %s" % currentPath)

    cmd = 'RunScript(script.videoextras,display,"%s")' % currentPath
    xbmc.executebuiltin(cmd)
