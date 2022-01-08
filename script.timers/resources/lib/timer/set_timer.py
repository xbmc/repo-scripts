import xbmc
import xbmcgui
from resources.lib.timer.abstract_set_timer import (CONFIRM_EDIT, DURATION_NO,
                                                    AbstractSetTimer)
from resources.lib.timer.scheduler import TIMERS
from resources.lib.timer.timer import (ACTION_START, ACTION_START_STOP,
                                       TIMER_DAYS_PRESETS, TIMER_OFF)


class SetTimer(AbstractSetTimer):

    def ask_timer(self):

        options = [self.addon.getLocalizedString(32102)]
        options += ["%i: %s (%s%s)" % (
            i - 1,
            self.addon.getSetting("timer_%i_label" % i),
            self.addon.getLocalizedString(
                32034 + int(self.addon.getSetting("timer_%i" % i))),
            ", %s" % self.addon.getSetting("timer_%i_start" % i) if self.addon.getSetting(
                "timer_%i" % i) != TIMER_OFF else "",
        ) for i in range(2, TIMERS)]

        selection = xbmcgui.Dialog().select(
            self.addon.getLocalizedString(32103), options, preselect=0)
        if selection == -1:
            return None
        elif selection == 0:
            xbmc.executebuiltin("Addon.OpenSettings(%s)" %
                                self.addon.getAddonInfo("id"))
            return None
        else:
            return selection + 1

    def ask_activation(self, listitem, preselection):

        if preselection["epg"]:
            return preselection["activation"]

        options = [self.addon.getLocalizedString(32034 + i)
                   for i in range(len(TIMER_DAYS_PRESETS))]

        selection = xbmcgui.Dialog().select(
            self.addon.getLocalizedString(32104), options, preselect=preselection["activation"])
        if selection == -1:
            return None
        else:
            return selection

    def ask_starttime(self, listitem, preselection):

        if preselection["epg"]:
            return preselection["starttime"]

        start = xbmcgui.Dialog().numeric(
            2, self.addon.getLocalizedString(32105), preselection["starttime"])
        if start == "":
            return None
        else:
            return ("0%s" % start.strip())[-5:]

    def ask_duration(self, listitem, preselection):

        if preselection["epg"]:
            return preselection["duration"]

        duration = xbmcgui.Dialog().numeric(
            2, self.addon.getLocalizedString(32106), preselection["duration"])
        if duration == "":
            return None
        else:
            return ("0%s" % duration.strip())[-5:]

    def ask_action(self, listitem, preselection):

        return ACTION_START_STOP if preselection["duration"] != DURATION_NO else ACTION_START

    def confirm(self, preselection):

        line1 = preselection["label"]

        line2 = (self.addon.getLocalizedString(32024) if preselection["duration"] != DURATION_NO else self.addon.getLocalizedString(32025)) % (
            self.addon.getLocalizedString(32034 + preselection["activation"]),
            preselection["starttime"],
            preselection["endtime"] if preselection["duration"] != DURATION_NO else "")

        line3 = "%s: %s" % (self.addon.getLocalizedString(32070),
                            self.addon.getLocalizedString(
                                32072) if preselection["duration"] != DURATION_NO else self.addon.getLocalizedString(32073)
                            )

        line4 = "%s: %s" % (self.addon.getLocalizedString(32091),
                            self.addon.getLocalizedString(32120 + int(self.addon.getSetting("timer_%i_fade" % preselection["timer"]))))

        return xbmcgui.Dialog().yesnocustom(self.addon.getLocalizedString(32107) % self.addon.getLocalizedString(32009 + preselection["timer"] - 2),
                                            "\n".join(
                                                [line1, line2, line3, line4]),
                                            self.addon.getLocalizedString(
                                                32021),
                                            self.addon.getLocalizedString(
                                                32022),
                                            self.addon.getLocalizedString(32023))

    def post_apply(self, selection, confirm):

        if confirm == CONFIRM_EDIT:
            xbmc.executebuiltin("Addon.OpenSettings(%s)" %
                                self.addon.getAddonInfo("id"))
