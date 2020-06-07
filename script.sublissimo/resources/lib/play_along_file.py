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

class PlayAlongFile(xbmc.Player):
    def __init__ (self):
        xbmc.Player.__init__(self)
        self.flag = True
        self.proper_exit = False

    def add(self, subtitlefile, filename):
        self.subtitlefile = subtitlefile
        self.filename = filename

    def delete_temp_file(self, pause):
        temp_file = self.filename[:-4] + "_temp.srt"
        if xbmcvfs.exists(temp_file):
            xbmcvfs.delete(temp_file)
        if pause:
            self.proper_exit = True
            self.stop()

    def activate_sub(self):
        new_file_name = self.filename[:-4] + "_temp.srt"
        with closing(File(new_file_name, 'w')) as fo:
            fo.write("".join(self.subtitlefile))
        self.setSubtitles(new_file_name)
        xbmcgui.Dialog().ok(_(32122), _(32121))

    def onPlayBackPaused(self):
        if not self.proper_exit:
        # Continue, Save and continue playing, Save and Exit, Exit to main menu, Exit completely
            options = [_(32074), _(31000), _(32101), _(32111), _(32078), _(32099)]
            choice = xbmcgui.Dialog().contextmenu(options)
            if choice == 0 or choice == -1:
                self.flag = False
            if choice == 1:
                xbmcgui.Dialog().multiselect(_(32010), self.subtitlefile)
                self.flag = False
            if choice == 2:
                self.flag = False
                self.proper_exit = True
                script.save_the_file(self.subtitlefile, self.filename, True)
            if choice == 3:
                self.delete_temp_file(True)
                script.save_the_file(self.subtitlefile, self.filename)
            if choice == 4:
                self.delete_temp_file(True)
                script.show_dialog(self.subtitlefile, self.filename)
            if choice == 5:
                self.delete_temp_file(True)
                script.exiting(self.subtitlefile, self.filename)
            if not self.flag:
                self.pause()
                self.flag = True

    def onPlayBackStopped(self):
        if not self.proper_exit:
            # Save subtitles, Exit to main menu, Exit completely
            options = [_(31008), _(32078), _(32099)]
            choice = xbmcgui.Dialog().contextmenu(options)
            if choice == 0:
                self.delete_temp_file(True)
                script.save_the_file(self.subtitlefile, self.filename)
            if choice == 1:
                self.delete_temp_file(True)
                script.show_dialog(self.subtitlefile, self.filename)
            if choice == 2 or choice == -1:
                self.delete_temp_file(True)
                script.exiting(self.subtitlefile, self.filename)
                
    def onPlayBackEnded(self):
        if not self.proper_exit:
            # Save subtitles, Exit to main menu, Exit completely
            options = [_(31008), _(32078), _(32099)]
            choice = xbmcgui.Dialog().contextmenu(options)
            if choice == 0:
                self.delete_temp_file(True)
                script.save_the_file(self.subtitlefile, self.filename)
            if choice == 1:
                self.delete_temp_file(True)
                script.show_dialog(self.subtitlefile, self.filename)
            if choice == 2 or choice == -1:
                self.delete_temp_file(True)
                script.exiting(self.subtitlefile, self.filename)                
                
