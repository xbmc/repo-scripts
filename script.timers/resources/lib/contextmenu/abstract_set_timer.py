import time
from datetime import datetime, timedelta

import xbmc
import xbmcaddon
import xbmcgui
from resources.lib.contextmenu import pvr_utils
from resources.lib.player.mediatype import SCRIPT, VIDEO
from resources.lib.timer.concurrency import determine_overlappings
from resources.lib.timer.storage import Storage
from resources.lib.timer.timer import (END_TYPE_DURATION, END_TYPE_NO,
                                       END_TYPE_TIME, FADE_OFF,
                                       MEDIA_ACTION_START_STOP,
                                       SYSTEM_ACTION_NONE, Timer)
from resources.lib.utils import datetime_utils, vfs_utils
from resources.lib.utils.settings_utils import (CONFIRM_CUSTOM, CONFIRM_ESCAPE,
                                                CONFIRM_NO, CONFIRM_YES,
                                                trigger_settings_changed_event)


class AbstractSetTimer:

    def __init__(self, label: str, path: str, timerid=-1) -> None:

        self.addon = xbmcaddon.Addon()
        self.storage = Storage()

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

        if timer.is_timer_by_date():
            date = self.ask_date(timer.label, path, is_epg, timer)
            if date == None:
                return
            else:
                timer.set_timer_by_date(date)

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
                (datetime_utils.parse_time(starttime) + datetime_utils.parse_time(duration)).total_seconds())

            if is_epg:
                timer.end_type = END_TYPE_TIME
            elif timer.duration == datetime_utils.DEFAULT_TIME:
                timer.end_type = END_TYPE_NO
            else:
                timer.end_type = END_TYPE_DURATION

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

        timer.init()
        now = datetime.today()
        timer.to_timer_by_date(base=now)
        overlappings = determine_overlappings(
            timer, self.storage.load_timers_from_storage(), ignore_extra_prio=True, to_display=True, base=now)
        if overlappings:
            answer = self.handle_overlapping_timers(
                timer, overlapping_timers=overlappings)
            if answer in [CONFIRM_ESCAPE, CONFIRM_CUSTOM]:
                return

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
            return vfs_utils.is_smart_playlist(path) or vfs_utils.is_script(path) or vfs_utils.is_audio_plugin(path) or vfs_utils.is_video_plugin(path) or vfs_utils.is_external(path) or not vfs_utils.is_folder(path) or vfs_utils.has_items_in_path(path)

    def perform_ahead(self, timer: Timer) -> bool:

        return True

    def ask_label(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        return label

    def ask_timer(self, timerid: int) -> int:

        return self.storage.get_next_id()

    def ask_days(self, label: str, path: str, is_epg: bool, timer: Timer) -> 'list[int]':

        if is_epg:
            return timer.days

        else:
            return [datetime.today().weekday()]

    def ask_date(self, label: str, path: str, is_epg: bool, timer: Timer) -> str:

        if is_epg:
            return timer.date

        else:
            return datetime_utils.to_date_str(datetime.today())

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

    def handle_overlapping_timers(self, timer: Timer, overlapping_timers: 'list[Timer]') -> int:

        timer.priority = max(overlapping_timers,
                             key=lambda t: t.priority).priority + 1

        return CONFIRM_YES

    def confirm(self, timer: Timer) -> int:

        return CONFIRM_YES

    def post_apply(self, timer: Timer, confirm: int) -> None:

        if confirm == CONFIRM_YES:
            msg = ("$H\n%s: $P" % self.addon.getLocalizedString(
                32081)) if timer.system_action else "$H"
            xbmcgui.Dialog().notification(heading=timer.label,
                                          message=timer.format(msg), icon=vfs_utils.get_asset_path("icon_timers.png"))

    def _get_timer_preselection(self, timerid: int, label: str, path: str) -> 'tuple[Timer,bool]':

        timer = self.storage.load_timer_from_storage(timerid)
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

                timer.set_timer_by_date(
                    date=datetime_utils.to_date_str(startDate))
                start = datetime_utils.parse_time(
                    xbmc.getInfoLabel("ListItem.StartTime"))
                timer.start, timer.start_offset = datetime_utils.format_from_timedelta(
                    start)

                s_duration = xbmc.getInfoLabel("ListItem.Duration")
                if len(s_duration) == 5:
                    s_duration = "00:%s" % s_duration[:2]

                elif len(s_duration) == 9:
                    return None, False

                else:
                    s_duration = s_duration[:5]

                td_duration = datetime_utils.parse_time(s_duration)
                timer.duration, timer.duration_offset = datetime_utils.format_from_timedelta(
                    td_duration)

        td_start = datetime_utils.parse_time(
            timer.start) + timedelta(seconds=timer.start_offset)
        if not is_epg:

            if not timer.days or timer.days == [datetime_utils.WEEKLY]:
                now = datetime_utils.DateTimeDelta.now()
                timer.days.append(now.dt.weekday() if not td_start.seconds or td_start.seconds >
                                  now.td.seconds else (now.dt.weekday() + 1) % 7)

                timer.date = datetime_utils.to_date_str(now.dt)

            if vfs_utils.is_favourites(path):
                timer.path = vfs_utils.get_favourites_target(path)
            else:
                timer.path = path

            timer.duration = timer.get_duration()

        timer.end, timer.end_offset = datetime_utils.format_from_timedelta(
            td_start + datetime_utils.parse_time(timer.duration) + timedelta(seconds=timer.duration_offset))

        if vfs_utils.is_script(timer.path):
            timer.media_type = SCRIPT
        else:
            timer.media_type = vfs_utils.get_media_type(timer.path) or VIDEO

        return timer, is_epg

    def apply(self, timer: Timer) -> None:

        self.storage.save_timer(timer=timer)
        trigger_settings_changed_event()
