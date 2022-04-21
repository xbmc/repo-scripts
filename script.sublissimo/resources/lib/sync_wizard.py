import xbmc
import xbmcgui
import xbmcaddon
import copy

from create_classical_times import create_classical_times
import script
import saving_and_exiting

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString

class SyncWizard(xbmc.Player):
    def __init__ (self):
        super(xbmc.Player, self).__init__(self)
        self.proper_exit = False
        self.ready_to_sync = False
        self.starting_time = None
        self.ending_time = None
        self.start_index = 0
        self.end_index = -1

    def add(self, subtitle):
        self.subtitle = subtitle
        self.backup = copy.deepcopy(self.subtitle)

    def start(self):
        pass

    def jump_to_subtitle(self, index):
        target = self.subtitle[index].startingtime/1000
        if target > self.getTotalTime():
            target = self.getTotalTime() - 120
        self.seekTime(target)
        self.pause()

    def exit(self):
        self.proper_exit = True
        self.subtitle.delete_temp_file()
        self.stop()

    def delete_subtitle(self, index):
        answer = xbmcgui.Dialog().yesno(_(32018), str(self.subtitle[index]),
                            yeslabel=_(32012), nolabel= _(32009))
        if not answer:
            del self.subtitle[index]

    def select_subtitle_to_sync_with(self):
        subtitle_in_strings, indexes = self.subtitle.easy_list_selector()
        line = xbmcgui.Dialog().select(_(32010), subtitle_in_strings)
        return indexes[line]

    def ask_and_sync_to_times(self):
        start = create_classical_times(self.starting_time*1000)
        end = create_classical_times(self.ending_time*1000)
        answer = xbmcgui.Dialog().yesno(_(32086), _(32087) +
                            str(start) + "\n" + _(32088) +
                            str(end), yeslabel=_(32089), nolabel=_(32090))
        if answer:
            # self.ending_time = None
            self.send_times()
            temp_file = self.subtitle.write_temp_file()
            self.setSubtitles(temp_file)
            xbmcgui.Dialog().ok(_(32122), _(32121))
            return True
        # else:
        return False

    def send_times(self):
        self.subtitle.sync_chosen_lines_to_chosen_times(self.starting_time*1000,
                                                        self.ending_time*1000,
                                                        self.start_index,
                                                        self.end_index)

    def place_first_subtitle(self):
        current_time = self.getTime()
        class_time = create_classical_times(current_time*1000)
        # Paused at, continue, select, skip f, skip b, exit, view first sub
        options = [_(32074), _(32075), _(32076), _(35049), _(32124), _(32079), _(35046), _(32078)]
        if self.start_index != 0:
            options[5] = _(35043)
        res = xbmcgui.Dialog().select(_(32073) + str(class_time), options)
        if res in (0, -1):
            pass
        if res == 1:
            self.starting_time = current_time
            if self.ending_time:
                if not self.ask_and_sync_to_times():
                    self.starting_time = None
            else:
                answer = xbmcgui.Dialog().yesno(_(32082), _(35050).format(
                                self.subtitle[self.start_index].text(),
                                str(class_time)),
                                yeslabel=_(32024),
                                nolabel= _(32025))
                if not answer:
                    self.starting_time = None
        if res == 2:
            self.seekTime(current_time - 1)
            self.pause()
        if res == 3:

            self.seekTime(current_time - 0.1)
            self.pause()
        if res == 4:
            self.jump_to_subtitle(self.start_index)
        if res == 5:
            self.delete_subtitle(self.start_index)
            self.pause()
        if res == 6:
            self.start_index = self.select_subtitle_to_sync_with()
            self.pause()
        if res == 7:
            self.proper_exit = True
            self.stop()
            script.show_dialog(self.backup)
        self.pause()

    def place_last_subtitle(self):
        current_time = self.getTime()
        class_time = create_classical_times(self.starting_time*1000)
        class_time2 = create_classical_times(current_time*1000)
        options = [_(32074), _(32081), _(32076), _(32077), _(32125),
                   _(32084), _(32080), _(35045), _(32078)]
        if self.end_index != -1:
            options[6] = _(35044)
        res = xbmcgui.Dialog().select(_(32085) + class_time + _(32073) + str(class_time2), options)
                 # f"{_(32085)}{class_time}{_(32073)}{str(class_time2)}", options)
        if res in (0, -1):
            pass
        if res == 1:
            self.ending_time = current_time
            if not self.ask_and_sync_to_times():
                self.ending_time = None
        if res == 2:
            self.seekTime(current_time - 1)
            self.pause()
        if res == 3:
            self.seekTime(current_time + 1)
            self.pause()
        if res == 4:
            self.jump_to_subtitle(self.end_index)
        if res == 5:
            self.starting_time = None
            self.pause()
        if res == 6:
            self.delete_subtitle(self.end_index)
            self.pause()
        if res == 7:
            self.end_index = self.select_subtitle_to_sync_with()
            self.pause()
        if res == 8:
            self.stop()
            self.proper_exit = True
            script.show_dialog(self.backup)
        self.pause()


    def result_menu(self):
        if not self.proper_exit:
        # Continue, Scroll subtitle, JumpToSubtitle, Save and continue playing, Exit to main menu,
            options = [_(32074), _(31000), _(35042), _(32101),
                       _(32096), _(32098), _(35047), _(35048)]
            choice = xbmcgui.Dialog().contextmenu(options)
            if choice in (0, -1):
                self.pause()
            if choice == 1:
                xbmcgui.Dialog().multiselect(_(32010), str(self.subtitle).split("\n"))
                self.pause()
            if choice == 2:
                index = self.select_subtitle_to_sync_with()
                self.seekTime(self.subtitle[index].startingtime/1000)
                self.pause()
            if choice == 3:
                self.proper_exit = True
                saving_and_exiting.save_the_file(self.subtitle, True)
            if choice == 4:
                self.exit()
                script.show_dialog(self.subtitle)
            if choice == 5:
                self.exit()
                script.show_dialog(self.backup)
            if choice == 6:
                self.starting_time = None
                self.jump_to_subtitle(self.start_index)
                self.pause()
            if choice == 7:
                self.ending_time = None
                self.jump_to_subtitle(self.end_index)
                self.pause()

    def onPlayBackPaused(self):
        if not self.proper_exit:
            if not self.starting_time:
                self.place_first_subtitle()
            elif self.starting_time and not self.ending_time:
                self.place_last_subtitle()
            elif self.ending_time and self.starting_time:
                self.result_menu()

    def onPlayBackStopped(self):
        if not self.proper_exit:
            self.exit()
            script.show_dialog(self.subtitle)

    def onPlayBackEnded(self):
        if not self.proper_exit:
            self.exit()
            script.show_dialog(self.subtitle)
