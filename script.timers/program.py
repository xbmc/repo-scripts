import os
import sys

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

addon = xbmcaddon.Addon()
addon_dir = xbmcvfs.translatePath(addon.getAddonInfo('path'))


def play(timer):

    path = addon.getSetting("timer_%i_filename" % timer).strip()
    if path != "":
        icon_file = os.path.join(
            addon_dir, "resources", "assets", "icon_sleep.png")

        xbmcgui.Dialog().notification(addon.getLocalizedString(
            32027), addon.getLocalizedString(32110) % addon.getLocalizedString(32004 + timer),
            icon=icon_file)

        xbmc.Player().play(path)

    else:
        xbmcgui.Dialog().notification(addon.getLocalizedString(
            32027), addon.getLocalizedString(32109))


def reset_volume():

    vol_default = int(addon.getSetting("vol_default"))
    xbmc.executebuiltin("SetVolume(%i)" % vol_default)
    xbmcgui.Dialog().notification(addon.getLocalizedString(
        32027), addon.getLocalizedString(32112))


if __name__ == "__main__":

    if len(sys.argv) == 3 and sys.argv[1] == "play":
        play(int(sys.argv[2]))

    elif len(sys.argv) == 2 and sys.argv[1] == "reset_volume":
        reset_volume()

    else:
        addon = xbmcaddon.Addon()
        xbmc.executebuiltin("Addon.OpenSettings(%s)" %
                            addon.getAddonInfo('id'))
