from datetime import datetime

import xbmcaddon
import xbmcgui
from resources.lib.utils import datetime_utils
from resources.lib.utils.settings_utils import (
    activate_on_settings_changed_events, deactivate_on_settings_changed_events)


def set_pause() -> None:

    addon = xbmcaddon.Addon()
    duration = xbmcgui.Dialog().numeric(
        2, addon.getLocalizedString(32106), "01:00")
    if duration == "":
        return
    else:
        today = datetime.today()
        duration = ("0%s" % duration.strip())[-5:]
        end = today + datetime_utils.parse_time(duration)
        _set(from_=today, until=end)


def reset_pause() -> None:

    _set(from_=None, until=None)


def _set(from_: datetime, until: datetime) -> None:

    if not until:
        date_from = "2001-01-01"
        time_from = "00:01"
        date_until = "2001-01-01"
        time_until = "00:01"
    else:
        date_from = from_.strftime("%Y-%m-%d")
        time_from = from_.strftime("%H:%M")
        date_until = until.strftime("%Y-%m-%d")
        time_until = until.strftime("%H:%M")

    addon = xbmcaddon.Addon()
    deactivate_on_settings_changed_events()
    addon.setSetting("pause_date_from", date_from)
    addon.setSetting("pause_time_from", time_from)
    addon.setSetting("pause_date_until", date_until)
    addon.setSetting("pause_time_until", time_until)
    activate_on_settings_changed_events()

    xbmcgui.Dialog().notification(addon.getLocalizedString(32027), addon.getLocalizedString(32166)
                                  if not until or until < datetime.today() else addon.getLocalizedString(32165) % until.strftime("%Y-%m-%d %H:%M"))
