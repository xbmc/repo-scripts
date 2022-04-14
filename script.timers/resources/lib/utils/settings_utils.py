import time

import xbmcaddon

_ON_SETTING_CHANGE_EVENTS = "onSettingChangeEvents"
_SETTING_CHANGE_EVENTS_MAX_SECS = 5
_SETTING_CHANGE_EVENTS_ACTIVE = 0


def deactivateOnSettingsChangedEvents() -> None:

    addon = xbmcaddon.Addon()
    addon.setSetting(_ON_SETTING_CHANGE_EVENTS, str(int(time.time())))


def activateOnSettingsChangedEvents() -> None:

    addon = xbmcaddon.Addon()
    addon.setSetting(_ON_SETTING_CHANGE_EVENTS,
                     str(_SETTING_CHANGE_EVENTS_ACTIVE))


def isSettingsChangedEvents() -> bool:

    addon = xbmcaddon.Addon()
    current = int("0%s" % addon.getSetting(_ON_SETTING_CHANGE_EVENTS))
    now = int(time.time())
    return now - current > _SETTING_CHANGE_EVENTS_MAX_SECS
