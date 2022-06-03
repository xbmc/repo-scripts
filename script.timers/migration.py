import xbmc
import xbmcaddon

from resources.lib.timer.scheduler import TIMERS
from resources.lib.utils.settings_utils import (
    activateOnSettingsChangedEvents, deactivateOnSettingsChangedEvents)


def migrate_from_1_to_2(addon: xbmcaddon.Addon) -> int:

    xbmc.log(
        "[script.timers] migrate settings from early version to version 2", xbmc.LOGINFO)

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

    return 2


def migrate_from_2_to_3(addon: xbmcaddon.Addon) -> int:

    xbmc.log("[script.timers] migrate settings to version 3", xbmc.LOGINFO)

    def _migrate_action(timer, system_action: int, media_action: int) -> None:

        addon.setSetting("timer_%i_system_action" % timer, str(system_action))
        addon.setSetting("timer_%i_media_action" % timer, str(media_action))

    for i in range(TIMERS):

        # splitting media and system actions
        action = int("0%s" % addon.getSetting("timer_%i_action" % i))
        if action == 0:
            _migrate_action(i, 0, 0)

        elif action == 1:
            _migrate_action(i, 0, 1)

        elif action == 2:
            _migrate_action(i, 0, 2)

        elif action == 3:
            _migrate_action(i, 0, 3)

        elif action == 4:
            _migrate_action(i, 0, 5)

        elif action == 5:
            _migrate_action(i, 0, 6)

        elif action == 6:
            _migrate_action(i, 1, 0)

        elif action == 7:
            _migrate_action(i, 2, 0)

        elif action == 8:
            _migrate_action(i, 3, 0)

        elif action == 9:
            _migrate_action(i, 4, 0)

        elif action == 10:
            _migrate_action(i, 5, 0)

        else:
            xbmc.log(
                "[script.timers] Unknown action %s in former settings. Set no action at all." % str(action), xbmc.LOGWARNING)
            _migrate_action(i, 0, 0)

    return 3


def migrate_from_3_to_4(addon: xbmcaddon.Addon) -> int:

    RANGE_ONCE_TIMERS = 7

    TIMER_DAYS_PRESETS = [
        [],                      # off
        [0],                     # mon
        [1],                     # tue
        [2],                     # wed
        [3],                     # thu
        [4],                     # fri
        [5],                     # sat
        [6],                     # sun
        [0],                     # mons
        [1],                     # tues
        [2],                     # weds
        [3],                    # thus
        [4],                    # fris
        [5],                    # sats
        [6],                    # suns
        [0, 1, 2, 3],           # mon-thu
        [0, 1, 2, 3, 4],        # mon-fri
        [0, 1, 2, 3, 4, 5],     # mon-sat
        [1, 2, 3, 4],           # tue-fri
        [3, 4, 5],              # thu-sat
        [4, 5],                 # fri-sat
        [4, 5, 6],              # fri-sun
        [5, 6],                 # sat-sun
        [5, 6, 0],              # sat-mon
        [6, 0, 1, 2],           # sun-wed
        [6, 0, 1, 2, 3],        # sun-thu
        [0, 1, 2, 3, 4, 5, 6]   # everyday
    ]

    xbmc.log("[script.timers] migrate settings to version 4", xbmc.LOGINFO)

    for i in range(TIMERS):

        # rename filename -> path
        path = addon.getSetting("timer_%i_filename" % i)
        addon.setSetting("timer_%i_path" % i, path)

        # days: enum -> multiselect
        schedule = int("0%s" % addon.getSetting("timer_%i" % i))
        if schedule > 0:
            days = "|".join([str(d) for d in TIMER_DAYS_PRESETS[schedule]])
            if days and schedule > RANGE_ONCE_TIMERS:
                days += "|7"

            addon.setSetting("timer_%i_days" % i, days)

        else:
            addon.setSetting("timer_%i_days" % i, "")

    return 4


def migrate() -> None:

    addon = xbmcaddon.Addon()

    deactivateOnSettingsChangedEvents()

    settingsVersion = addon.getSettingInt("settingsVersion")

    if settingsVersion == 1:
        settingsVersion = migrate_from_1_to_2(addon)

    if settingsVersion == 2:
        settingsVersion = migrate_from_2_to_3(addon)

    if settingsVersion == 3:
        settingsVersion = migrate_from_3_to_4(addon)

    addon.setSettingInt("settingsVersion", settingsVersion)
    activateOnSettingsChangedEvents()
