import datetime
import os
import sys

# prevent Error: Failed to import _strptime because the import lockis held by another thread.
# see https://www.raspberrypi.org/forums/viewtopic.php?t=166912
import _strptime
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.timer.scheduler import CHECK_INTERVAL, Scheduler

addon = xbmcaddon.Addon()
addon_dir = xbmcvfs.translatePath(addon.getAddonInfo('path'))


def play(timer):

    path = addon.getSetting("timer_%i_filename" % timer).strip()
    if path != "":
        icon_file = os.path.join(
            addon_dir, "resources", "assets", "icon_sleep.png")

        xbmcgui.Dialog().notification(addon.getLocalizedString(
            32027), addon.getLocalizedString(32110) % addon.getLocalizedString(32009 + timer),
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

    # prevent Error: Failed to import _strptime because the import locks held by another thread.
    # see https://www.raspberrypi.org/forums/viewtopic.php?t=166912
    datetime.datetime.strptime("2016", "%Y")

    if len(sys.argv) == 3 and sys.argv[1] == "play":
        play(int(sys.argv[2]))

    elif len(sys.argv) == 2 and sys.argv[1] == "reset_volume":
        reset_volume()

    else:
        scheduler = Scheduler(addon)

        if xbmc.getCondVisibility("system.platform.windows") and "true" == addon.getSetting("windows_unlock"):
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)

        scheduler.start()

        if xbmc.getCondVisibility("system.platform.windows") and "true" == addon.getSetting("windows_unlock"):
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
