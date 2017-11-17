import os
import sys
import xbmc
import xbmcaddon

addon = xbmcaddon.Addon()
addonpath = xbmc.translatePath(addon.getAddonInfo('path')).decode('utf-8')
sys.path.append(os.path.join(addonpath, u'resources', u'lib'))

import playrandom
from pykodi import get_pathinfo

# DEPRECATED: StringCompare and SubString in addon.xml is deprecated in Krypton, gone in Leia,
#  but both options resolve to False when unrecognized so the result is the same for all versions

if __name__ == '__main__':
    path = sys.listitem.getfilename()
    label = sys.listitem.getLabel()
    watchmode = xbmc.getInfoLabel('Control.GetLabel(10)')
    if path and label:
        pathinfo = {'full path': path, 'label': label, 'watchmode': watchmode}
        pathinfo.update(get_pathinfo(path))
        playrandom.play(pathinfo)
