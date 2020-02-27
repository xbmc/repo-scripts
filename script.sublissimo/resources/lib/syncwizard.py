# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import sys
import script
import xbmcaddon
import logging
from resources.lib import kodiutils
from resources.lib import kodilogging
from script import *

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString
logger = logging.getLogger(ADDON.getAddonInfo('id'))

class SyncWizard(xbmc.Player) :
    def __init__ (self):
        xbmc.Player.__init__(self)
        self.starting_time = None
        self.ending_time = None
        self.flag = False

    def add(self, subtitlefile, filename):
        self.subtitlefile = subtitlefile
        self.filename = filename

    def select_line_subtitle(self, start, end):
        start_index_found = False
        start_index, end_index = 0, 0
        if start:
            for index, line in enumerate(self.subtitlefile):
                if len(line) == 30 or len(line) == 31:
                    if line[0] == "0" and line[17] == "0":
                        start_index = index - 1
                        start_index_found = True
                if start_index_found:
                    if len(line) == 1 and line[0] == "\n":
                        end_index = index
                        break
                    if len(line) == 2 and line[-1] == "\n" and line[0] == "\r":
                        end_index = index
                        break
            return start_index, end_index

        if end:
            for x in range(len(self.subtitlefile)-1 ,-1, -1):
                if len(self.subtitlefile[x]) == 30 or len(self.subtitlefile[x]) == 31:
                    if self.subtitlefile[x][0] == "0" and self.subtitlefile[x][17] == "0":
                        start_index = x - 1
                        break
            end_index = len(self.subtitlefile)
        return start_index, end_index

    def exit(self):
        script.show_dialog(self.subtitlefile, self.filename)

    def ttt(self):
        script.tryout(self.starting_time, self.ending_time, self.subtitlefile, self.filename)

    def onPlayBackPaused(self):
        current_time = xbmc.Player().getTime()
        if not self.starting_time:
            class_time = script.make_timelines_classical(current_time*1000)
            # Paused at, continue, select, skip f, skip b, exit, view first sub
            res = xbmcgui.Dialog().select(_(32073) + str(class_time),
                    [_(32074), _(32075), _(32076), _(32077), _(32078), _(32079)])
            if res == 1:
                self.starting_time = current_time
                answer = xbmcgui.Dialog().yesno(_(32082), _(32083) +
                        str(class_time), yeslabel=_(32024), nolabel= _(32025))
                if not answer:
                    self.starting_time = None
                self.flag = False
            if res == 2:
                xbmc.Player().seekTime(current_time - 1)
                self.flag = False
                xbmc.Player().pause()
            if res == 3:
                xbmc.Player().seekTime(current_time + 1)
                self.flag = False
                xbmc.Player().pause()
            if res == 0 or res == -1:
                # xbmc.Player().pause()
                self.flag = False
            if res == 4:
                xbmc.Player().stop()
                self.exit()
            if res == 5:
                start_index, end_index = self.select_line_subtitle(True, False)
                #Currentfirst, ok, delete
                answer = xbmcgui.Dialog().yesno(_(32018),
                                    "".join(self.subtitlefile[start_index:end_index]),
                                    yeslabel=_(32012), nolabel= _(32009))
                if not answer:
                    del self.subtitlefile[start_index:end_index]
                    start_index, end_index = self.select_line_subtitle(True, False)
                    #First subtitles is now
                    xbmcgui.Dialog().ok(_(32019),
                                        "".join(self.subtitlefile[start_index:end_index]))
        if not self.flag:
            xbmc.Player().pause()
            self.flag = True
        else:
            if self.starting_time:
                class_time = script.make_timelines_classical(self.starting_time*1000)
                class_time2 = script.make_timelines_classical(current_time*1000)
                res = xbmcgui.Dialog().select(_(32085) + class_time + _(32073) + str(class_time2),
                                    [_(32074), _(32081),_(32076), _(32077),
                                     _(32084), _(32078), _(32080)])
                if res == 1:
                    self.ending_time = current_time
                    start = script.make_timelines_classical(self.starting_time*1000)
                    end = script.make_timelines_classical(self.ending_time*1000)
                    answer = xbmcgui.Dialog().yesno(_(32086), _(32087) +
                                        str(start) + "\n" + _(32088) +
                                        str(end), yeslabel=_(32089), nolabel=_(32090))
                    if not answer:
                        self.ending_time = None
                    xbmc.Player().pause()
                    self.flag = False
                if res == 2:
                    xbmc.Player().seekTime(current_time - 1)
                    # self.flag = False
                    xbmc.Player().pause()
                    xbmc.Player().pause()
                if res == 3:
                    xbmc.Player().seekTime(current_time + 1)
                    xbmc.Player().pause()
                    xbmc.Player().pause()
                    # self.flag = False
                    # xbmc.Player().pause()
                if res == 4:
                    self.starting_time = None
                    self.flag = False
                if res == 0 or res == -1:
                    # pass
                    # self.flag = False
                    xbmc.Player().pause()
                if res == 5:
                    xbmc.Player().stop()
                    self.exit()
                if res == 6:
                    start_index, end_index = self.select_line_subtitle(False, True)
                    #Current last, ok, delete
                    answer = xbmcgui.Dialog().yesno(_(32021),
                                        "".join(self.subtitlefile[start_index:end_index]),
                                        yeslabel=_(32012), nolabel=_(32009))
                    if not answer:
                        del self.subtitlefile[start_index:end_index]
                        start_index, end_index = self.select_line_subtitle(False, True)
                        #Last sub is now
                        xbmcgui.Dialog().ok(_(32022),
                                        "".join(self.subtitlefile[start_index:end_index]))

        if self.ending_time and self.starting_time:
            xbmc.Player().stop()
            self.ttt()
