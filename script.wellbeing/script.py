import re
import sys
import time

import xbmc
import xbmcaddon
import xbmcgui

addon = xbmcaddon.Addon()

if __name__ == "__main__":

    if len(sys.argv) > 1 and sys.argv[1] == "status":

        pass

    elif len(sys.argv) > 1 and sys.argv[1] == "action=reset":

        addon.setSettingInt("sum", -1)

    elif len(sys.argv) > 1 and sys.argv[1] == "reset":

        time.sleep(1)  # wait for settings to be saved
        addon.setSettingInt("sum", -1)

    elif len(sys.argv) > 1 and sys.argv[1] == "action=limit" and sys.args[2].startswith("limit="):

        time_ = sys.argv[2][6:]
        if re.match(r"^\d{1,2}:\d{2}$", time_):
            xbmc.log(f"script.wellbeing: setting time limit to '{time_}'", xbmc.LOGINFO)
            addon.setSetting("limit", time_)
        elif time_.isdigit():
            xbmc.log(f"script.wellbeing: converting time '{time_}' to mm:ss", xbmc.LOGINFO)
            addon.setSetting("limit", f"{(int(time_) // 60):02d}:{(int(time_) % 60):02d}")
        else:
            xbmc.log(f"script.wellbeing: invalid time format '{time_}'", xbmc.LOGERROR)

    elif len(sys.argv) > 1 and sys.argv[1] == "limit":

        time.sleep(1)  # wait for settings to be saved
        time_ = xbmcgui.Dialog().numeric(
            2, addon.getLocalizedString(32075), addon.getSetting("limit_%i" % time.localtime().tm_wday))
        if time_:
            addon.setSetting("limit", time_)

    else:
        addon.openSettings()
