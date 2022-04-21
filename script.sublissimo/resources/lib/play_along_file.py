import xbmc
import xbmcgui
import xbmcaddon
# import logging
# import sys
# import copy

from create_classical_times import create_classical_times
import script
import saving_and_exiting

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString

class PlayAlongFile(xbmc.Player):
    def __init__(self):
        super(xbmc.Player, self).__init__(self)
        self.proper_exit = False
        self.subtitle = None

    def add(self, subtitle):
        self.subtitle = subtitle

    def exit(self):
        self.subtitle.delete_temp_file()
        self.proper_exit = True
        self.stop()

    def jump_to_subtitle(self):
        subtitle_in_strings, indexes = self.subtitle.easy_list_selector()
        line = xbmcgui.Dialog().select(_(32010), subtitle_in_strings)
        target = int(self.subtitle[indexes[line]].startingtime/1000)
        if target > self.getTotalTime():
            target = self.getTotalTime() - 120
        self.seekTime(int(target))
        self.pause()

    def start(self):
        new_file_name = self.subtitle.write_temp_file()
        self.setSubtitles(new_file_name)
        xbmcgui.Dialog().ok(_(32122), _(32121))

    def exit_menu(self):
        # Save subtitles, Exit to main menu, Exit completely
        options = [_(31008), _(32078), _(32099)]
        choice = xbmcgui.Dialog().contextmenu(options)
        if choice == 0:
            self.exit()
            saving_and_exiting.save_the_file(self.subtitle)
        if choice == 1:
            self.exit()
            script.show_dialog(self.subtitle)
        if choice in (2, -1):
            self.exit()
            saving_and_exiting.exiting(self.subtitle)

    def onPlayBackPaused(self):
        if not self.proper_exit:
            # Continue, Scroll subtitle, JumpToSubtitle, Save and continue playing,
            # Save and Exit, Exit to main menu, Exit completely
            options = [_(32074), _(31000), _(35042),_(32101),
                       _(32111), _(32078), _(32099)]
            choice = xbmcgui.Dialog().contextmenu(options)
            if choice in (0, -1):
                self.pause()
                # pass
            if choice == 1:
                xbmcgui.Dialog().multiselect(_(32010), str(self.subtitle).split("\n"))
                self.pause()
                self.pause()
            if choice == 2:
                self.jump_to_subtitle()
            if choice == 3:
                self.proper_exit = True
                saving_and_exiting.save_the_file(self.subtitle, True)
            if choice == 4:
                self.exit()
                saving_and_exiting.save_the_file(self.subtitle)
            if choice == 5:
                self.exit()
                script.show_dialog(self.subtitle)
            if choice == 6:
                self.exit()
                saving_and_exiting.exiting(self.subtitle)

    def onPlayBackStopped(self):
        if not self.proper_exit:
            self.exit_menu()

    def onPlayBackEnded(self):
        if not self.proper_exit:
            self.exit_menu()
