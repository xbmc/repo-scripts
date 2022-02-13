import xbmcaddon
from resources.lib.timer import util
from resources.lib.timer.scheduler import TIMERS


def migrate():

    addon = xbmcaddon.Addon()

    util.deactivateOnSettingsChangedEvents(addon)

    settingsVersion = addon.getSettingInt("settingsVersion")

    # migrate version 1 -> 2
    if settingsVersion == 1:
        for i in range(TIMERS):
            i_schedule = addon.getSettingInt("timer_%i" % i)
            if i_schedule == 25:
                addon.setSettingInt("timer_%i" % i, 0)
            elif i_schedule == 26:
                addon.setSettingInt("timer_%i" % i, 17)
            elif i_schedule >= 1 and i_schedule <= 15:
                addon.setSettingInt("timer_%i" % i, i_schedule + 1)
            elif i_schedule >= 16 and i_schedule <= 24:
                addon.setSettingInt("timer_%i" % i, i_schedule + 2)

    addon.setSettingInt("settingsVersion", 2)
    util.activateOnSettingsChangedEvents(addon)
