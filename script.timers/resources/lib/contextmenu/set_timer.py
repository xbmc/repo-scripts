import xbmcgui
from resources.lib.contextmenu.abstract_set_timer import (CONFIRM_EDIT,
                                                          DURATION_NO,
                                                          AbstractSetTimer)
from resources.lib.contextmenu.selection import Selection
from resources.lib.timer.scheduler import TIMERS
from resources.lib.timer.timer import (MEDIA_ACTION_START,
                                       MEDIA_ACTION_START_STOP,
                                       SYSTEM_ACTION_NONE, TIMER_DAYS_PRESETS,
                                       TIMER_OFF)


class SetTimer(AbstractSetTimer):

    def ask_timer(self) -> int:

        options = [self.addon.getLocalizedString(32102)]
        options += ["%i: %s (%s%s)" % (
            i - 1,
            self.addon.getSettingString("timer_%i_label" % i),
            self.addon.getLocalizedString(
                32200 + self.addon.getSettingInt("timer_%i" % i)),
            ", %s" % self.addon.getSetting("timer_%i_start" % i) if self.addon.getSettingInt(
                "timer_%i" % i) != TIMER_OFF else "",
        ) for i in range(2, TIMERS)]

        selection = xbmcgui.Dialog().select(
            self.addon.getLocalizedString(32103), options, preselect=0)
        if selection == -1:
            return None
        elif selection == 0:
            self.addon.openSettings()
            return None
        else:
            return selection + 1

    def ask_activation(self, listitem: xbmcgui.ListItem, preselection: Selection) -> int:

        if preselection.epg:
            return preselection.activation

        options = [self.addon.getLocalizedString(32200 + i)
                   for i in range(1, len(TIMER_DAYS_PRESETS))]

        selection = xbmcgui.Dialog().select(
            self.addon.getLocalizedString(32104), options, preselect=preselection.activation - 1)
        if selection == -1:
            return None
        else:
            return selection + 1

    def ask_starttime(self, listitem: xbmcgui.ListItem, preselection: Selection) -> str:

        if preselection.epg:
            return preselection.startTime

        start = xbmcgui.Dialog().numeric(
            2, self.addon.getLocalizedString(32105), preselection.startTime)
        if start == "":
            return None
        else:
            return ("0%s" % start.strip())[-5:]

    def ask_duration(self, listitem: xbmcgui.ListItem, preselection: Selection) -> str:

        if preselection.epg:
            return preselection.duration

        duration = xbmcgui.Dialog().numeric(
            2, self.addon.getLocalizedString(32106), preselection.duration)
        if duration == "":
            return None
        else:
            return ("0%s" % duration.strip())[-5:]

    def ask_repeat_resume(self, preselection: Selection) -> 'tuple[bool, bool]':

        return False, preselection.duration != DURATION_NO

    def ask_action(self, listitem: xbmcgui.ListItem, preselection: Selection) -> 'tuple[int, int]':

        return SYSTEM_ACTION_NONE, MEDIA_ACTION_START_STOP if preselection.duration != DURATION_NO else MEDIA_ACTION_START

    def confirm(self, preselection: Selection) -> int:

        line1 = preselection.label

        line2 = (self.addon.getLocalizedString(32024) if preselection.duration != DURATION_NO else self.addon.getLocalizedString(32025)) % (
            self.addon.getLocalizedString(32200 + preselection.activation),
            preselection.startTime,
            preselection.endTime if preselection.duration != DURATION_NO else "")

        line3 = "%s: %s" % (self.addon.getLocalizedString(32070),
                            self.addon.getLocalizedString(
                                32072) if preselection.duration != DURATION_NO else self.addon.getLocalizedString(32073)
                            )

        line4 = "%s: %s" % (self.addon.getLocalizedString(32091),
                            self.addon.getLocalizedString(32120 + self.addon.getSettingInt("timer_%i_fade" % preselection.timer)))

        return xbmcgui.Dialog().yesnocustom(self.addon.getLocalizedString(32107) % self.addon.getLocalizedString(32004 + preselection.timer),
                                            "\n".join(
                                                [line1, line2, line3, line4]),
                                            self.addon.getLocalizedString(
                                                32021),
                                            self.addon.getLocalizedString(
                                                32022),
                                            self.addon.getLocalizedString(32023))

    def post_apply(self, selection: Selection, confirm: int) -> None:

        if confirm == CONFIRM_EDIT:
            self.addon.openSettings()
