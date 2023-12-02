import xbmcaddon
import xbmcgui
from resources.lib.timer.timer import Timer
from resources.lib.utils.vfs_utils import get_asset_path


def showNotification(timer: Timer, msg_id: int, icon="icon_timers.png") -> None:

    if timer.notify:
        addon = xbmcaddon.Addon()
        icon_path = get_asset_path(icon)
        xbmcgui.Dialog().notification(
            timer.label, addon.getLocalizedString(msg_id), icon_path)
