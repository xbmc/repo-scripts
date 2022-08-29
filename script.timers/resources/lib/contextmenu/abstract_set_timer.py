import time
from datetime import datetime

import xbmc
import xbmcaddon
import xbmcgui
from resources.lib.contextmenu import pvr_utils
from resources.lib.player.mediatype import VIDEO
from resources.lib.timer import storage
from resources.lib.timer.timer import (END_TYPE_DURATION, END_TYPE_NO,
                                       FADE_OFF, MEDIA_ACTION_START_STOP,
                                       SYSTEM_ACTION_NONE, Timer)
from resources.lib.utils import datetime_utils, vfs_utils
from resources.lib.utils.settings_utils import trigger_settings_changed_event

CONFIRM_ESCAPE = -1
CONFIRM_NO = 0
CONFIRM_YES = 1
CONFIRM_EDIT = 2


class AbstractSetTimer:

    addon = None

    def __init__(self, label: str, path: str, timerid=-1) -> None:

        self.addon = xbmcaddon.Addon()

        if not self.is_supported(label, path):
            yes = xbmcgui.Dialog().yesno(heading=self.addon.getLocalizedString(
                32027), message=self.addon.getLocalizedString(32118),
                yeslabel=self.addon.getLocalizedString(32102),
                nolabel=self.addon.getLocalizedString(32022))
            if yes:
                self.addon.openSettings()
            return

        timerid = self.ask_timer(timerid)
        if timerid == None:
            return

        timer, is_epg = self._get_timer_preselection(timerid, label, path)
        if timer == None:
            return

        ok = self.perform_ahead(timer)
        if not ok:
            return

        label = self.ask_label(timer.label, path, is_epg, timer)
        if label == None:
            return
        else:
            timer.label = label

        days = self.ask_days(timer.label, path, is_epg, timer)
        if days == None:
            return
        else:
            timer.days = days

        starttime = self.ask_starttime(timer.label, path, is_epg, timer)
        if starttime == None:
            return
        else:
            timer.start = starttime

        duration = self.ask_duration(timer.label, path, is_epg, timer)
        if duration == None:
            return
        else:
            timer.duration = duration
            timer.end = datetime_utils.format_from_seconds(
                (datetime_utils.parse_time(starttime) + datetime_utils.parse_time(duration)).seconds)
            timer.end_type = END_TYPE_NO if timer.duration == datetime_utils.DEFAULT_TIME else END_TYPE_DURATION

        system_action, media_action = self.ask_action(
            timer.label, path, is_epg, timer)
        if system_action == None or media_action == None:
            return
        else:
            timer.system_action = system_action
            timer.media_action = media_action

        repeat, resume = self.ask_repeat_resume(timer)
        if repeat == None or resume == None:
            return
        else:
            timer.repeat = repeat
            timer.resume = resume

        fade, vol_min, vol_max = self.ask_fader(timer)
        if fade == None:
            return
        else:
            timer.fade = fade
            timer.vol_min = vol_min
            timer.vol_max = vol_max

        confirm = self.confirm(timer)
        if confirm in [CONFIRM_ESCAPE, CONFIRM_NO]:
            return

        else:
            self.apply(timer)
            self.post_apply(timer, confirm)

    def is_supported(self, label: str, path: str) -> bool:

        if vfs_utils.is_favourites(path):
            path = vfs_utils.get_favourites_target(path)

        if label == "..":
            return False
        elif not path:
            return False
        elif vfs_utils.is_pvr(path):
            return vfs_utils.is_pvr_channel(path) or vfs_utils.is_pvr_recording(path) or xbmc.getCondVisibility("Window.IsVisible(tvguide)|Window.IsVisible(radioguide)")
        else:
            return vfs_utils.is_script(path) or vfs_utils.is_external(path) or not vfs_utils.is_folder(path) or vfs_utils.has_items_in_path(path)

    def perform_ahead(self, timer: Timer) -> bool:

        return True

    def ask_label(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        return label

    def ask_timer(self, timerid: int) -> int:

        return storage.get_next_id()

    def ask_days(self, label: str, path: str, is_epg: bool, timer: Timer) -> 'list[int]':

        if is_epg:
            return timer.days

        else:
            return [datetime.today().weekday()]

    def ask_starttime(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        if is_epg:
            return timer.start

        else:
            return time.strftime("%H:%M", time.localtime())

    def ask_duration(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        return datetime_utils.DEFAULT_TIME

    def ask_action(self, label: str, path: str, is_epg: bool, timer: Timer) -> 'tuple[int, int]':

        return SYSTEM_ACTION_NONE, MEDIA_ACTION_START_STOP

    def ask_repeat_resume(self, timer: Timer) -> 'tuple[bool, bool]':

        return False, False

    def ask_fader(self, timer: Timer) -> 'tuple[int, int, int]':

        return FADE_OFF, timer.vol_min, timer.vol_max

    def confirm(self, timer: Timer) -> int:

        return CONFIRM_YES

    def post_apply(self, timer: Timer, confirm: int) -> None:

        if confirm == CONFIRM_YES:
            lines = list()
            lines.append(timer.periods_to_human_readable())
            if timer.system_action:
                lines.append("%s: %s" % (self.addon.getLocalizedString(32081),
                                         self.addon.getLocalizedString(32081 + timer.system_action)))

            xbmcgui.Dialog().notification(heading=timer.label,
                                          message="\n".join(lines), icon=vfs_utils.get_asset_path("icon.png"))

    def _get_timer_preselection(self, timerid: int, label: str, path: str) -> 'tuple[Timer,bool]':

        timer = storage.load_timer_from_storage(timerid)
        if not timer:
            timer = Timer(timerid)
            timer.vol_min = self.addon.getSettingInt("vol_min_default")
            timer.vol_max = self.addon.getSettingInt("vol_default")

        timer.label = label

        is_epg = False
        if pvr_utils.get_current_epg_view():
            pvr_channel_path = pvr_utils.get_pvr_channel_path(
                pvr_utils.get_current_epg_view(), xbmc.getInfoLabel("ListItem.ChannelNumberLabel"))

            if pvr_channel_path:
                is_epg = True
                timer.label = "%s | %s" % (
                    xbmc.getInfoLabel("ListItem.ChannelName"), label)
                timer.path = pvr_channel_path
                startDate = datetime_utils.parse_xbmc_shortdate(
                    xbmc.getInfoLabel("ListItem.Date").split(" ")[0])
                timer.days = [startDate.weekday()]
                timer.start = xbmc.getInfoLabel("ListItem.StartTime")
                duration = xbmc.getInfoLabel("ListItem.Duration")
                if len(duration) == 5:
                    timer.duration = "00:%s" % duration[:2]

                elif len(duration) == 9:
                    return None, False

                else:
                    timer.duration = duration[:5]

        td_start = datetime_utils.parse_time(timer.start)
        if not is_epg:

            if not timer.days or timer.days == [datetime_utils.WEEKLY]:
                t_now, td_now = datetime_utils.get_now()
                timer.days.append(t_now.weekday() if not td_start.seconds or td_start.seconds >
                                  td_now.seconds else (t_now.weekday() + 1) % 7)

            if vfs_utils.is_favourites(path):
                timer.path = vfs_utils.get_favourites_target(path)
            else:
                timer.path = path

            timer.duration = timer.get_duration()

        timer.end = datetime_utils.format_from_seconds(
            (td_start + datetime_utils.parse_time(timer.duration)).seconds)

        if vfs_utils.is_script(timer.path):
            timer.media_type = "script"
        else:
            timer.media_type = vfs_utils.get_media_type(timer.path) or VIDEO

        return timer, is_epg

    def apply(self, timer: Timer) -> None:

        storage.save_timer(timer=timer)
        trigger_settings_changed_event()
