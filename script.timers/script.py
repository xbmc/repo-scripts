import sys

import xbmc
import xbmcaddon

from resources.lib.timer import util

addon = xbmcaddon.Addon()

if __name__ == "__main__":

    if len(sys.argv) == 3 and sys.argv[1] == "play":
        util.preview(addon=addon, timer=int(sys.argv[2]))

    elif len(sys.argv) == 2 and sys.argv[1] == "reset_volume":
        util.reset_volume(addon=addon)

    else:
        addon = xbmcaddon.Addon()
        xbmc.executebuiltin("Addon.OpenSettings(%s)" %
                            addon.getAddonInfo('id'))
