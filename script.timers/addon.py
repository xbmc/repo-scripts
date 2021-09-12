import datetime

# prevent Error: Failed to import _strptime because the import lockis held by another thread.
# see https://www.raspberrypi.org/forums/viewtopic.php?t=166912
import _strptime
import xbmc
import xbmcaddon

from resources.lib.timer.scheduler import CHECK_INTERVAL, Scheduler

addon = xbmcaddon.Addon()


if __name__ == "__main__":

    # prevent Error: Failed to import _strptime because the import locks held by another thread.
    # see https://www.raspberrypi.org/forums/viewtopic.php?t=166912
    datetime.datetime.strptime("2016", "%Y")

    scheduler = Scheduler(addon)

    if xbmc.getCondVisibility("system.platform.windows") and "true" == addon.getSetting("windows_unlock"):
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)

    scheduler.start()

    if xbmc.getCondVisibility("system.platform.windows") and "true" == addon.getSetting("windows_unlock"):
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
