import datetime

import xbmc
import xbmcgui

from resources.lib import ADDON, hue
from resources.lib.language import get_string as _


def validate_settings():
    _validate_schedule()
    _validate_ambilight()


def _validate_ambilight():
    xbmc.log(f"[script.service.hue] Validate ambilight config. Enabled: {ADDON.getSettingBool('group3_enabled')}")
    if ADDON.getSettingBool("group3_enabled"):
        light_ids = ADDON.getSetting("group3_Lights")
        if light_ids == "-1":
            xbmc.log("[script.service.hue] No ambilights selected")
            hue.notification(_("Hue Service"), _("No lights selected for Ambilight."), icon=xbmcgui.NOTIFICATION_ERROR)
            ADDON.setSettingBool("group3_enabled", False)


def _validate_schedule():
    xbmc.log(f"[script.service.hue] Validate schedule. Schedule Enabled: {ADDON.getSettingBool('enableSchedule')}")
    if ADDON.getSettingBool("enableSchedule"):
        try:
            convert_time(ADDON.getSettingBool("startTime"))
            convert_time(ADDON.getSettingBool("endTime"))
            # xbmc.log("[script.service.hue] Time looks valid")
        except ValueError as e:
            xbmc.log(f"[script.service.hue] Invalid time settings: {e}")
            hue.notification(_("Hue Service"), _("Invalid start or end time, schedule disabled"), icon=xbmcgui.NOTIFICATION_ERROR)
            ADDON.setSettingBool("EnableSchedule", False)


def convert_time(time):
    hour = int(time.split(":")[0])
    minute = int(time.split(":")[1])
    return datetime.time(hour, minute)
