import time
from datetime import datetime

import xbmc
import xbmcaddon
import xbmcgui
from resources.lib.contextmenu import pvr_utils
from resources.lib.contextmenu.selection import Selection
from resources.lib.timer.timer import (END_TYPE_DURATION, END_TYPE_NO,
                                       END_TYPE_TIME, MEDIA_ACTION_START_STOP,
                                       SYSTEM_ACTION_NONE)
from resources.lib.utils import datetime_utils, settings_utils, vfs_utils

DURATION_NO = datetime_utils.DEFAULT_TIME

CONFIRM_ESCAPE = -1
CONFIRM_NO = 0
CONFIRM_YES = 1
CONFIRM_EDIT = 2


class AbstractSetTimer:

    addon = None
    listitem = None

    def __init__(self, listitem: xbmcgui.ListItem) -> None:

        self.addon = xbmcaddon.Addon()
        self.listitem = listitem

        if not self.is_listitem_valid(listitem):
            xbmcgui.Dialog().ok(self.addon.getLocalizedString(
                32027), self.addon.getLocalizedString(32034))
            return

        timer = self.ask_timer()
        if timer == None:
            return

        preselection = self._get_timer_preselection(timer, listitem)

        ok = self.perform_ahead(preselection)
        if not ok:
            return

        label = self.ask_label(listitem, preselection)
        if label == None:
            return
        else:
            preselection.label = label

        activation = self.ask_activation(listitem, preselection)
        if activation == None:
            return
        else:
            preselection.activation = activation

        starttime = self.ask_starttime(listitem, preselection)
        if starttime == None:
            return
        else:
            preselection.startTime = starttime

        duration = self.ask_duration(listitem, preselection)
        if duration == None:
            return
        else:
            preselection.duration = duration
            preselection.endTime = datetime_utils.format_from_seconds(
                (datetime_utils.parse_time(starttime) + datetime_utils.parse_time(duration)).seconds)

        system_action, media_action = self.ask_action(
            listitem, preselection)
        if system_action == None or media_action == None:
            return
        else:
            preselection.systemAction = system_action
            preselection.mediaAction = media_action

        repeat, resume = self.ask_repeat_resume(preselection)
        if repeat == None or resume == None:
            return
        else:
            preselection.repeat = repeat
            preselection.resume = resume

        confirm = self.confirm(preselection)
        if confirm in [CONFIRM_ESCAPE, CONFIRM_NO]:
            return

        else:
            self._apply(preselection)
            self.post_apply(preselection, confirm)

    def is_listitem_valid(self, listitem: xbmcgui.ListItem) -> bool:

        path = listitem.getPath()
        if listitem.getLabel() == "..":
            return False
        elif vfs_utils.is_pvr(path):
            return vfs_utils.is_pvr_channel(path) or vfs_utils.is_pvr_recording(path) or xbmc.getCondVisibility("Window.IsVisible(tvguide)|Window.IsVisible(radioguide)")
        else:
            return vfs_utils.has_items_in_path(path) or not vfs_utils.is_folder(path)

    def perform_ahead(self, preselection: Selection) -> bool:

        return True

    def ask_label(self, listitem: xbmcgui.ListItem, preselection: Selection) -> str:

        return listitem.getLabel()

    def ask_timer(self) -> int:

        return None

    def ask_activation(self, listitem: xbmcgui.ListItem, preselection: Selection) -> int:

        if preselection.epg:
            return preselection.activation

        else:
            return datetime.today().weekday() + 1

    def ask_starttime(self, listitem: xbmcgui.ListItem, preselection: Selection) -> str:

        if preselection.epg:
            return preselection.startTime

        else:
            return time.strftime("%H:%M", time.localtime())

    def ask_duration(self, listitem: xbmcgui.ListItem, preselection: Selection) -> str:

        return DURATION_NO

    def ask_action(self, listitem: xbmcgui.ListItem, preselection: Selection) -> 'tuple[int, int]':

        return SYSTEM_ACTION_NONE, MEDIA_ACTION_START_STOP

    def ask_repeat_resume(self, preselection: Selection) -> 'tuple[bool, bool]':

        return False, False

    def confirm(self, preselection: Selection) -> int:

        return CONFIRM_YES

    def _apply(self, selection: Selection):

        settings_utils.deactivateOnSettingsChangedEvents()

        timer = selection.timer
        self.addon.setSettingInt("timer_%s" % timer, selection.activation)
        self.addon.setSettingString("timer_%s_label" %
                                    timer, selection.label)
        self.addon.setSettingString("timer_%s_start" %
                                    timer, selection.startTime)
        self.addon.setSettingInt("timer_%s_end_type" % timer,
                                 END_TYPE_DURATION if selection.duration != DURATION_NO else END_TYPE_NO)
        self.addon.setSetting("timer_%s_duration" %
                              timer, selection.duration)
        self.addon.setSettingString("timer_%s_end" %
                                    timer, selection.endTime)
        self.addon.setSettingInt("timer_%s_system_action" %
                                 timer, selection.systemAction)
        self.addon.setSettingInt("timer_%s_media_action" %
                                 timer, selection.mediaAction)
        self.addon.setSettingString(
            "timer_%s_filename" % timer, selection.path)
        self.addon.setSettingBool(
            "timer_%s_repeat" % timer, selection.repeat)
        self.addon.setSettingBool(
            "timer_%s_resume" % timer, selection.resume)

        if selection.fade is not None:
            self.addon.setSettingInt("timer_%s_fade" %
                                     timer, selection.fade)

        settings_utils.activateOnSettingsChangedEvents()

    def post_apply(self, selection: Selection, confirm: int) -> None:

        pass

    def _get_timer_preselection(self, timer: int, listitem: xbmcgui.ListItem):

        selection = Selection()
        selection.timer = timer
        selection.label = listitem.getLabel()

        if pvr_utils.get_current_epg_view():
            startDate = datetime_utils.parse_xbmc_shortdate(
                xbmc.getInfoLabel("ListItem.Date").split(" ")[0])
            selection.activation = startDate.weekday() + 1
            selection.startTime = xbmc.getInfoLabel("ListItem.StartTime")
            duration = xbmc.getInfoLabel("ListItem.Duration")
            selection.duration = "00:%s" % duration[:2] if len(
                duration) == 5 else duration[:5]
            selection.path = pvr_utils.get_pvr_channel_path(
                pvr_utils.get_current_epg_view(), xbmc.getInfoLabel("ListItem.ChannelNumberLabel"))
            selection.epg = selection.path != None

        if not selection.epg:
            selection.activation = self.addon.getSettingInt("timer_%i" % timer)
            selection.path = listitem.getPath()
            selection.startTime = self.addon.getSetting(
                "timer_%i_start" % timer)
            if self.addon.getSettingInt("timer_%i_end_type" % timer) == END_TYPE_DURATION:
                selection.duration = self.addon.getSettingString(
                    "timer_%i_duration" % timer)

            elif self.addon.getSettingInt("timer_%i_end_type" % timer) == END_TYPE_TIME:
                selection.duration = datetime_utils.time_duration_str(self.addon.getSettingString(
                    "timer_%i_start" % timer), self.addon.getSetting("timer_%i_end" % timer))

            else:
                selection.duration = DURATION_NO

        selection.endTime = datetime_utils.format_from_seconds(
            (datetime_utils.parse_time(selection.startTime) + datetime_utils.parse_time(selection.duration)).seconds)

        selection.systemAction = self.addon.getSettingInt(
            "timer_%i_system_action" % timer)
        selection.mediaAction = self.addon.getSettingInt(
            "timer_%i_media_action" % timer)

        selection.repeat = self.addon.getSettingBool("timer_%i_repeat" % timer)
        selection.resume = self.addon.getSettingBool("timer_%i_resume" % timer)
        selection.fade = None

        return selection
