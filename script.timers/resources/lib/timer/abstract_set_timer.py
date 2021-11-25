import time
from datetime import datetime

import xbmc
import xbmcaddon
from resources.lib.timer import util
from resources.lib.timer.timer import (ACTION_START_STOP, END_TYPE_DURATION,
                                           END_TYPE_NO, END_TYPE_TIME)

DURATION_NO = util.DEFAULT_TIME

CONFIRM_ESCAPE = -1
CONFIRM_NO = 0
CONFIRM_YES = 1
CONFIRM_EDIT = 2


class AbstractSetTimer:

    addon = None
    listitem = None

    def __init__(self, listitem):

        self.addon = xbmcaddon.Addon()
        self.listitem = listitem

        timer = self.ask_timer()
        if timer == None:
            return

        preselection = self._get_timer_preselection(timer, listitem)
        path = preselection["path"]

        ok = self.perform_ahead(preselection)
        if not ok:
            return

        label = self.ask_label(listitem, preselection)
        if label == None:
            return
        else:
            preselection["label"] = label

        activation = self.ask_activation(listitem, preselection)
        if activation == None:
            return
        else:
            preselection["activation"] = activation

        starttime = self.ask_starttime(listitem, preselection)
        if starttime == None:
            return
        else:
            preselection["starttime"] = starttime

        duration = self.ask_duration(listitem, preselection)
        if duration == None:
            return
        else:
            preselection["duration"] = duration
            preselection["endtime"] = util.format_from_seconds(
                (util.parse_time(starttime) + util.parse_time(duration)).seconds)

        action = self.ask_action(listitem, preselection)
        if action == None:
            return
        else:
            preselection["action"] = action

        confirm = self.confirm(preselection)
        if confirm in [CONFIRM_ESCAPE, CONFIRM_NO]:
            return

        else:
            self._apply(preselection)
            self.post_apply(preselection, confirm)

    def perform_ahead(self, preselection):

        return True

    def ask_label(self, listitem, preselection):

        return listitem.getLabel()

    def ask_timer(self):

        return None

    def ask_activation(self, listitem, preselection):

        if preselection["epg"]:
            return preselection["activation"]

        else:
            return str(datetime.today().weekday())

    def ask_starttime(self, listitem, preselection):

        if preselection["epg"]:
            return preselection["starttime"]

        else:
            return time.strftime("%H:%M", time.localtime())

    def ask_duration(self, listitem, preselection):

        return DURATION_NO

    def ask_action(self, listitem, preselection):

        return ACTION_START_STOP

    def confirm(self, preselection):

        return CONFIRM_YES

    def _apply(self, selection):

        timer = selection["timer"]

        util.deactivateOnSettingsChangedEvents(self.addon)
        self.addon.setSetting("timer_%s" % timer, str(selection["activation"]))
        self.addon.setSetting("timer_%s_label" % timer, selection["label"])
        self.addon.setSetting("timer_%s_start" % timer, selection["starttime"])
        self.addon.setSetting("timer_%s_end_type" % timer,
                              END_TYPE_DURATION if selection["duration"] != DURATION_NO else END_TYPE_NO)
        self.addon.setSetting("timer_%s_duration" %
                              timer, selection["duration"])
        self.addon.setSetting("timer_%s_end" % timer, selection["endtime"])
        self.addon.setSetting("timer_%s_action" % timer, selection["action"])
        self.addon.setSetting("timer_%s_filename" % timer, selection["path"])
        if selection["fade"] is not None:
            self.addon.setSetting("timer_%s_fade" % timer, str(selection["fade"]))

        util.activateOnSettingsChangedEvents(self.addon)

    def post_apply(self, selection, confirm):

        pass

    def _get_timer_preselection(self, timer, listitem):

        is_epg = False
        if util.get_current_epg_view():
            startDate = util.parse_xbmc_shortdate(
                xbmc.getInfoLabel("ListItem.Date").split(" ")[0])
            activation = startDate.weekday()
            startTime = xbmc.getInfoLabel("ListItem.StartTime")
            duration = xbmc.getInfoLabel("ListItem.Duration")
            duration = "00:%s" % duration[:2] if len(
                duration) == 5 else duration[:5]
            path = util.get_pvr_channel_path(
                util.get_current_epg_view(), xbmc.getInfoLabel("ListItem.ChannelNumberLabel"))
            is_epg = path != None

        if not is_epg:
            activation = int(self.addon.getSetting("timer_%i" % timer))
            path = listitem.getPath()
            startTime = self.addon.getSetting("timer_%i_start" % timer)
            if self.addon.getSetting("timer_%i_end_type" % timer) == END_TYPE_DURATION:
                duration = self.addon.getSetting("timer_%i_duration" % timer)

            elif self.addon.getSetting("timer_%i_end_type" % timer) == END_TYPE_TIME:
                duration = util.time_duration_str(self.addon.getSetting(
                    "timer_%i_start" % timer), self.addon.getSetting("timer_%i_end" % timer))

            else:
                duration = DURATION_NO

        endTime = util.format_from_seconds(
            (util.parse_time(startTime) + util.parse_time(duration)).seconds)

        action = self.addon.getSetting("timer_%i_action" % timer)

        return {
            "path": path,
            "label": listitem.getLabel(),
            "timer": timer,
            "activation": activation,
            "starttime": startTime,
            "duration": duration,
            "endtime": endTime,
            "action": action,
            "epg": is_epg,
            "fade" : None
        }
