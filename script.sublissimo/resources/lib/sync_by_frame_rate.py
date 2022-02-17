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

class SyncWizardFrameRate(xbmc.Player):
    def __init__ (self):
        super(xbmc.Player, self).__init__(self)
        self.proper_exit = False

    def add(self, subtitle):
        self.subtitle = subtitle
        self.backup = copy.deepcopy(self.subtitle)

    def exit(self):
        self.proper_exit = True
        self.subtitle.delete_temp_file()
        self.stop()

    def get_frame_rate(self):
        self.frame_rate = xbmc.getInfoLabel('Player.Process(VideoFPS)')
        xbmcgui.Dialog().ok(_(32106), _(32120) + str(self.frame_rate))
        self.give_frame_rate(True)

    def apply_new_rate(self, factor, from_pause):
        if from_pause:
            self.flag = False
        old_start_timestamp = self.subtitle[0].return_starting_time()
        old_ending_timestamp = self.subtitle[-1].return_starting_time()
        new_start_timestamp = self.subtitle[0].return_starting_time(factor)
        new_ending_timestamp = self.subtitle[-1].return_starting_time(factor)
        res = xbmcgui.Dialog().yesno(_(32107), _(32108) + str(old_start_timestamp)
                                      + "\n" + _(32109) + str(old_ending_timestamp)
                                      + "\n" + _(34110) + str(new_start_timestamp)
                                      + "\n" + _(32110) + str(new_ending_timestamp)
                                      + "\n", yeslabel=_(32012), nolabel= _(32008))
        if not res:
            self.give_frame_rate(False)
        else:
            self.subtitle.stretch_subtitle(factor)
            temp_file = self.subtitle.write_temp_file()
            self.setSubtitles(temp_file)
            xbmcgui.Dialog().ok(_(32050),_(32102))

    def start(self):
        self.give_frame_rate(False)

    def give_frame_rate(self, from_pause):
        # get frame_rate from video, calculate manually,  Exit to main menu,
        options = ["23.976 --> 25.000", "25.000 --> 23.976",
                   "24.000 --> 25.000", "25.000 --> 24.000",
                   "23.976 --> 24.000", "24.000 --> 23.976",
                   _(32104), _(32112), _(32078)]
        # Video frame rate
        factors = [(25/23.976), (23.976/25), (25/24), (24/25), (24/23.976), (23.976/24)]
        menuchoices = [0, 1, 2, 3, 4, 5]
        menuchoice = xbmcgui.Dialog().select(_(32105), options)
        if menuchoice in menuchoices:
            self.apply_new_rate(factors[menuchoice], from_pause)
        if menuchoice == 6:
            self.get_frame_rate()
        if menuchoice == 7:
            xbmcgui.Dialog().ok(_(32114), _(32115))
            response = xbmcgui.Dialog().input(_(32113))
            calculated_factor = eval(str(response))
            self.apply_new_rate(calculated_factor, from_pause)
        if menuchoice in (8, -1):
            self.stop()
            script.show_dialog(self.subtitle)

    def exit_menu(self):
        self.exit()
        options = [_(32096), _(32097), _(32098), _(32099)]
        choice = xbmcgui.Dialog().contextmenu(options)
        if choice == 0:
            script.show_dialog(self.subtitle)
        if choice == 1:
            saving_and_exiting.save_the_file(self.subtitle)
        if choice in (2, -1):
            script.show_dialog(self.backup)
        if choice == 3:
            saving_and_exiting.exiting(self.subtitle)

    def onPlayBackPaused(self):
        if not self.proper_exit:
            options = [_(32074), _(32100), _(31000), _(32101), _(32096), _(32098)]
            choice = xbmcgui.Dialog().contextmenu(options)
            if choice == (0, -1):
                self.pause()
            if choice == 1:
                self.add(self.backup)
                self.give_frame_rate(True)
                self.pause()
            if choice == 2:
                xbmcgui.Dialog().multiselect(_(32010), str(self.subtitle).split("\n"))
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

    def onPlayBackStopped(self):
        if not self.proper_exit:
            self.exit_menu()

    def onPlayBackEnded(self):
        if not self.proper_exit:
            self.exit_menu()
