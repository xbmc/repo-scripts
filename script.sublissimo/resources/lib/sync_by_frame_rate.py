from __future__ import division
import xbmc
import xbmcgui
import sys
import script
import xbmcaddon
import logging
from script import *


ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString
logger = logging.getLogger(ADDON.getAddonInfo('id'))

class SyncWizardFrameRate(xbmc.Player):
    def __init__ (self):
        xbmc.Player.__init__(self)
        self.proper_exit = False
        self.flag = False

    def add(self, subtitlefile, filename):
        self.subtitlefile = subtitlefile
        self.filename = filename
        self.new_subtitlefile = []

    def get_frame_rate(self):
        self.frame_rate = xbmc.getInfoLabel('Player.Process(VideoFPS)')
        xbmcgui.Dialog().ok(_(32106), _(32120) + str(self.frame_rate))
        self.give_frame_rate(True)

    def delete_temp_file(self):
        temp_file = self.filename[:-4] + "_temp.srt"
        if xbmcvfs.exists(temp_file):
             xbmcvfs.delete(temp_file)

    def write_and_display_temp_file(self, new_subtitlefile, temp):
        if temp:
            new_file_name = self.filename[:-4] + "_temp.srt"
        else:
            self.delete_temp_file()
            new_file_name = self.filename[:-4] + "_edited.srt"
        with closing(File(new_file_name, 'w')) as fo:
            fo.write("".join(new_subtitlefile))
        self.new_subtitlefile = new_subtitlefile
        self.setSubtitles(new_file_name)
        if temp:
            frame_rate_input = xbmcgui.Dialog().ok(_(32050),_(32102))

    def rearrange(self, new_factor, from_pause):
        if from_pause:
            self.flag = False
        cur_sub = Subtitle(self.subtitlefile)
        old_starting_time, old_ending_time = cur_sub.make_timelines_decimal()
        old_start_timestamp = script.make_timelines_classical(old_starting_time)
        old_ending_timestamp = script.make_timelines_classical(old_ending_time)        
        new_start_timestamp = script.make_timelines_classical(new_factor * old_starting_time)
        new_ending_timestamp = script.make_timelines_classical(new_factor * old_ending_time)
        res = xbmcgui.Dialog().yesno(_(32107), _(32108) + str(old_start_timestamp) 
                                      + "\n" + _(32109) + str(old_ending_timestamp) 
                                      + "\n" + _(34110) + str(new_start_timestamp) 
                                      + "\n" + _(32110) + str(new_ending_timestamp) 
                                      + "\n", yeslabel=_(32012), nolabel= _(32008))
        if not res:
            self.give_frame_rate()
        new_subtitlefile = cur_sub.create_new_times(False, new_factor, 0)
        xbmcgui.Dialog().multiselect(_(32010), new_subtitlefile)
        self.write_and_display_temp_file(new_subtitlefile, True)

    def give_frame_rate(self, from_pause):
        # get frame_rate from video, calculate manually,  Exit to main menu,
        options = ["23.976 --> 25.000", "25.000 --> 23.976", "24.000 --> 25.000", "25.000 --> 24.000",
                   "23.976 --> 24.000", "24.000 --> 23.976", _(32104), _(32112), _(32078)]
        # Video frame rate
        menuchoice = xbmcgui.Dialog().select(_(32105), options)
        if menuchoice == 0:
            chosen_factor = (25/23.976)
            self.rearrange(chosen_factor, from_pause)
        if menuchoice == 1:
            chosen_factor = (23.976/25)
            self.rearrange(chosen_factor, from_pause)
        if menuchoice == 2:
            chosen_factor = (25/24)
            self.rearrange(chosen_factor, from_pause)
        if menuchoice == 3:
            chosen_factor = (24/25)
            self.rearrange(chosen_factor, from_pause)
        if menuchoice == 4:
            chosen_factor = (24/23.976)
            self.rearrange(chosen_factor, from_pause)
        if menuchoice == 5:
            chosen_factor = (23.976/24)
            self.rearrange(chosen_factor, from_pause)
        if menuchoice == 6:
            self.get_frame_rate()
        if menuchoice == 7:
            xbmcgui.Dialog().ok(_(32114), _(32115))
            response = xbmcgui.Dialog().input(_(32113))
            calculated_factor = eval(str(response))
            self.rearrange(calculated_factor, from_pause)
        if menuchoice == 8 or menuchoice == -1:
            self.stop()
            script.show_dialog(self.subtitlefile, self.filename)

    def onPlayBackPaused(self):
        if self.proper_exit:
            pass
        else:
            choice = xbmcgui.Dialog().contextmenu([_(32074), _(32100), _(31000), _(32101), _(32096), _(32098)])
            if choice == 0 or choice == -1:
                self.flag = False
            if choice == 1:
                self.give_frame_rate(True)
                #self.flag = False
            if choice == 2:
                xbmcgui.Dialog().multiselect(_(32010), self.new_subtitlefile)
            if choice == 3:
                self.proper_exit = True
                self.flag = True
                script.save_the_file(self.new_subtitlefile, self.filename, True)
            if choice == 4:
                self.proper_exit = True
                self.stop()
                if self.new_subtitlefile:
                    self.delete_temp_file()
                    script.show_dialog(self.new_subtitlefile, self.filename)
                else:
                    self.delete_temp_file()
                    script.show_dialog(self.subtitlefile, self.filename)
            if choice == 5:
                self.proper_exit = True
                self.delete_temp_file()
                self.stop()
                script.show_dialog(self.subtitlefile, self.filename)
            if not self.flag:
                self.pause()
                self.flag = True

    def onPlayBackStopped(self):
        if not self.proper_exit:
            xbmcgui.Dialog().contextmenu([_(32096), _(32097), _(32098), _(32099)])
            if choice == 0:
                if self.new_subtitlefile:
                    self.delete_temp_file()
                    script.show_dialog(self.new_subtitlefile, self.filename)
                else:
                    self.delete_temp_file()
                    script.show_dialog(self.subtitlefile, self.filename)
            if choice == 1:
                script.save_the_file(self.new_subtitlefile, self.filename)
                #self.write_and_display_temp_file(self.new_subtitlefile, False)
            if choice == 2 or choice == -1:
                self.delete_temp_file()
                self.proper_exit = True
                script.show_dialog(self.subtitlefile, self.filename)
            if choice == 3:
                self.delete_temp_file()
                script.exiting(self.new_subtitlefile, self.filename)
