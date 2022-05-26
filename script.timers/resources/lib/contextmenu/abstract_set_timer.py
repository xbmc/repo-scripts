import time
from datetime import datetime

import xbmc
import xbmcaddon
import xbmcgui
from resources.lib.contextmenu import pvr_utils
from resources.lib.timer.timer import (END_TYPE_DURATION, END_TYPE_NO,
                                       FADE_OFF, MEDIA_ACTION_START_STOP,
                                       SYSTEM_ACTION_NONE, TIMER_WEEKLY, Timer)
from resources.lib.utils import datetime_utils, vfs_utils

CONFIRM_ESCAPE = -1
CONFIRM_NO = 0
CONFIRM_YES = 1
CONFIRM_EDIT = 2


class AbstractSetTimer:

    _addon = None

    def __init__(self, label: str, path: str, timerid=-1) -> None:

        self.addon = xbmcaddon.Addon()

        if not self.is_supported(label, path):
            xbmcgui.Dialog().ok(self.addon.getLocalizedString(
                32027), self.addon.getLocalizedString(32118))
            return

        timerid = self.ask_timer(timerid)
        if timerid == None:
            return

        timer, is_epg = self._get_timer_preselection(timerid, label, path)

        ok = self.perform_ahead(timer)
        if not ok:
            return

        label = self.ask_label(label, path, is_epg, timer)
        if label == None:
            return
        else:
            timer.s_label = label

        days = self.ask_days(label, path, is_epg, timer)
        if days == None:
            return
        else:
            timer.days = days

        starttime = self.ask_starttime(label, path, is_epg, timer)
        if starttime == None:
            return
        else:
            timer.s_start = starttime

        duration = self.ask_duration(label, path, is_epg, timer)
        if duration == None:
            return
        else:
            timer.s_duration = duration
            timer.s_end = datetime_utils.format_from_seconds(
                (datetime_utils.parse_time(starttime) + datetime_utils.parse_time(duration)).seconds)
            timer.i_end_type = END_TYPE_NO if timer.s_duration == datetime_utils.DEFAULT_TIME else END_TYPE_DURATION

        system_action, media_action = self.ask_action(
            label, path, is_epg, timer)
        if system_action == None or media_action == None:
            return
        else:
            timer.i_system_action = system_action
            timer.i_media_action = media_action

        repeat, resume = self.ask_repeat_resume(timer)
        if repeat == None or resume == None:
            return
        else:
            timer.b_repeat = repeat
            timer.b_resume = resume

        confirm = self.confirm(timer)
        if confirm in [CONFIRM_ESCAPE, CONFIRM_NO]:
            return

        else:
            self._apply(timer)
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

        return timerid

    def ask_days(self, label: str, path: str, is_epg: bool, timer: Timer) -> 'list[int]':

        if is_epg:
            return timer.days

        else:
            return [datetime.today().weekday()]

    def ask_starttime(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        if is_epg:
            return timer.s_start

        else:
            return time.strftime("%H:%M", time.localtime())

    def ask_duration(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        return datetime_utils.DEFAULT_TIME

    def ask_action(self, label: str, path: str, is_epg: bool, timer: Timer) -> 'tuple[int, int]':

        return SYSTEM_ACTION_NONE, MEDIA_ACTION_START_STOP

    def ask_repeat_resume(self, timer: Timer) -> 'tuple[bool, bool]':

        return False, False

    def confirm(self, timer: Timer) -> int:

        return CONFIRM_YES

    def post_apply(self, timer: Timer, confirm: int) -> None:

        pass

    def days_to_short(self, days: 'list[int]') -> str:

        l = list()
        for d in range(7):
            if d in days:
                l.append(self.addon.getLocalizedString(32210 + d))

        if TIMER_WEEKLY in days:
            l.append("...")

        return ", ".join(l)

    def _get_timer_preselection(self, timerid: int, label: str, path: str) -> 'tuple[Timer,bool]':

        timer = Timer.init_from_settings(timerid)
        timer.s_label = label
        timer.i_fade = FADE_OFF

        is_epg = False
        if pvr_utils.get_current_epg_view():
            pvr_channel_path = pvr_utils.get_pvr_channel_path(
                pvr_utils.get_current_epg_view(), xbmc.getInfoLabel("ListItem.ChannelNumberLabel"))

            if pvr_channel_path:
                is_epg = True
                timer.s_path = pvr_channel_path
                startDate = datetime_utils.parse_xbmc_shortdate(
                    xbmc.getInfoLabel("ListItem.Date").split(" ")[0])
                timer.days = [startDate.weekday()]
                timer.s_start = xbmc.getInfoLabel("ListItem.StartTime")
                duration = xbmc.getInfoLabel("ListItem.Duration")
                timer.s_duration = "00:%s" % duration[:2] if len(
                    duration) == 5 else duration[:5]

        if not is_epg:

            if TIMER_WEEKLY not in timer.days:
                t_now, td_now = datetime_utils.get_now()
                timer.days = [t_now.tm_wday]

            if vfs_utils.is_favourites(path):
                timer.s_path = vfs_utils.get_favourites_target(path)
            else:
                timer.s_path = path

            timer.s_duration = timer.get_duration()

        timer.s_end = datetime_utils.format_from_seconds(
            (datetime_utils.parse_time(timer.s_start) + datetime_utils.parse_time(timer.s_duration)).seconds)

        if vfs_utils.is_script(timer.s_path):
            timer.s_mediatype = "script"
        else:
            timer.s_mediatype = vfs_utils.get_media_type(timer.s_path)

        return timer, is_epg

    def _apply(self, timer: Timer) -> None:

        timer.save_to_settings()
