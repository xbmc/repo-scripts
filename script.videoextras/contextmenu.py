# -*- coding: utf-8 -*-
import xbmc

# Import the common settings
from resources.lib.settings import log


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
