#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime
import sys, re
import random

from xml.dom.minidom import parse, parseString
from resources.lib.Globals import *
from resources.lib.ChannelList import ChannelList
from resources.lib.AdvancedConfig import AdvancedConfig
from resources.lib.FileAccess import FileAccess
from resources.lib.Migrate import Migrate


NUMBER_CHANNEL_TYPES = 8



class ConfigWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.log("__init__")
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.setCoordinateResolution(1)
        self.showingList = True
        self.channel = 0
        self.channel_type = 9999
        self.setting1 = ''
        self.setting2 = ''
        self.savedRules = False
        ADDON_SETTINGS.loadSettings()
        self.doModal()
        self.log("__init__ return")


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('ChannelConfig: ' + msg, level)


    def onInit(self):
        self.log("onInit")

        for i in range(NUMBER_CHANNEL_TYPES):
            try:
                self.getControl(120 + i).setVisible(False)
            except:
                pass

        migratemaster = Migrate()
        migratemaster.migrate()
        self.prepareConfig()
        self.myRules = AdvancedConfig("script.pseudotv.AdvancedConfig.xml", ADDON_INFO, "default")
        self.log("onInit return")


    def onFocus(self, controlId):
        pass


    def onAction(self, act):
        action = act.getId()

        if action == ACTION_PREVIOUS_MENU:
            if self.showingList == False:
                self.cancelChan()
                self.hideChanDetails()
            else:
                self.close()


    def saveSettings(self):
        self.log("saveSettings channel " + str(self.channel))
        chantype = 9999
        chan = str(self.channel)
        set1 = ''
        set2 = ''

        try:
            chantype = int(ADDON_SETTINGS.getSetting("Channel_" + chan + "_type"))
        except:
            self.log("Unable to get channel type")

        setting1 = "Channel_" + chan + "_1"
        setting2 = "Channel_" + chan + "_2"

        if chantype == 0:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(130).getLabel2())
        elif chantype == 1:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(142).getLabel())
        elif chantype == 2:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(152).getLabel())
        elif chantype == 3:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(162).getLabel())
        elif chantype == 4:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(172).getLabel())
        elif chantype == 5:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(182).getLabel())
        elif chantype == 6:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(192).getLabel())

            if self.getControl(194).isSelected():
                ADDON_SETTINGS.setSetting(setting2, str(MODE_ORDERAIRDATE))
        elif chantype == 7:
            ADDON_SETTINGS.setSetting(setting1, self.getControl(200).getLabel())
        elif chantype == 9999:
            ADDON_SETTINGS.setSetting(setting1, '')
            ADDON_SETTINGS.setSetting(setting2, '')

        if self.savedRules:
            self.saveRules(self.channel)

        # Check to see if the user changed anything
        set1 = ''
        set2 = ''

        try:
            set1 = ADDON_SETTINGS.getSetting(setting1)
            set2 = ADDON_SETTINGS.getSetting(setting2)
        except:
            pass

        if chantype != self.channel_type or set1 != self.setting1 or set2 != self.setting2 or self.savedRules:
            ADDON_SETTINGS.setSetting('Channel_' + chan + '_changed', 'True')

        self.log("saveSettings return")


    def cancelChan(self):
        ADDON_SETTINGS.setSetting("Channel_" + str(self.channel) + "_type", str(self.channel_type))
        ADDON_SETTINGS.setSetting("Channel_" + str(self.channel) + "_1", self.setting1)
        ADDON_SETTINGS.setSetting("Channel_" + str(self.channel) + "_2", self.setting2)


    def hideChanDetails(self):
        self.getControl(106).setVisible(False)

        for i in range(NUMBER_CHANNEL_TYPES):
            try:
                self.getControl(120 + i).setVisible(False)
            except:
                pass

        self.setFocusId(102)
        self.getControl(105).setVisible(True)
        self.showingList = True
        self.updateListing(self.channel)
        self.listcontrol.selectItem(self.channel - 1)


    def onClick(self, controlId):
        self.log("onClick " + str(controlId))

        if controlId == 102:        # Channel list entry selected
            self.getControl(105).setVisible(False)
            self.getControl(106).setVisible(True)
            self.channel = self.listcontrol.getSelectedPosition() + 1
            self.changeChanType(self.channel, 0)
            self.setFocusId(110)
            self.showingList = False
            self.savedRules = False
        elif controlId == 110:      # Change channel type left
            self.changeChanType(self.channel, -1)
        elif controlId == 111:      # Change channel type right
            self.changeChanType(self.channel, 1)
        elif controlId == 112:      # Ok button
            self.saveSettings()
            self.hideChanDetails()
        elif controlId == 113:      # Cancel button
            self.cancelChan()
            self.hideChanDetails()
        elif controlId == 114:      # Rules button
            self.myRules.ruleList = self.ruleList
            self.myRules.doModal()

            if self.myRules.wasSaved == True:
                self.ruleList = self.myRules.ruleList
                self.savedRules = True
        elif controlId == 130:      # Playlist-type channel, playlist button
            dlg = xbmcgui.Dialog()
            retval = dlg.browse(1, "Channel " + str(self.channel) + " Playlist", "files", ".xsp", False, False, "special://videoplaylists/")

            if retval != "special://videoplaylists/":
                self.getControl(130).setLabel(self.getSmartPlaylistName(retval), label2=retval)
        elif controlId == 140:      # Network TV channel, left
            self.changeListData(self.networkList, 142, -1)
        elif controlId == 141:      # Network TV channel, right
            self.changeListData(self.networkList, 142, 1)
        elif controlId == 150:      # Movie studio channel, left
            self.changeListData(self.studioList, 152, -1)
        elif controlId == 151:      # Movie studio channel, right
            self.changeListData(self.studioList, 152, 1)
        elif controlId == 160:      # TV Genre channel, left
            self.changeListData(self.showGenreList, 162, -1)
        elif controlId == 161:      # TV Genre channel, right
            self.changeListData(self.showGenreList, 162, 1)
        elif controlId == 170:      # Movie Genre channel, left
            self.changeListData(self.movieGenreList, 172, -1)
        elif controlId == 171:      # Movie Genre channel, right
            self.changeListData(self.movieGenreList, 172, 1)
        elif controlId == 180:      # Mixed Genre channel, left
            self.changeListData(self.mixedGenreList, 182, -1)
        elif controlId == 181:      # Mixed Genre channel, right
            self.changeListData(self.mixedGenreList, 182, 1)
        elif controlId == 190:      # TV Show channel, left
            self.changeListData(self.showList, 192, -1)
        elif controlId == 191:      # TV Show channel, right
            self.changeListData(self.showList, 192, 1)
        elif controlId == 200:      # Directory channel, select
            dlg = xbmcgui.Dialog()
            retval = dlg.browse(0, "Channel " + str(self.channel) + " Directory", "files")

            if len(retval) > 0:
                self.getControl(200).setLabel(retval)

        self.log("onClick return")


    def changeListData(self, thelist, controlid, val):
        self.log("changeListData " + str(controlid) + ", " + str(val))
        curval = self.getControl(controlid).getLabel()
        found = False
        index = 0

        if len(thelist) == 0:
            self.getControl(controlid).setLabel('')
            self.log("changeListData return Empty list")
            return

        for item in thelist:
            if item == curval:
                found = True
                break

            index += 1

        if found == True:
            index += val

        while index < 0:
            index += len(thelist)

        while index >= len(thelist):
            index -= len(thelist)

        self.getControl(controlid).setLabel(thelist[index])
        self.log("changeListData return")


    def getSmartPlaylistName(self, fle):
        self.log("getSmartPlaylistName " + fle)
        fle = xbmc.translatePath(fle)

        try:
            xml = FileAccess.open(fle, "r")
        except:
            self.log('Unable to open smart playlist')
            return ''

        try:
            dom = parse(xml)
        except:
            xml.close()
            self.log("getSmartPlaylistName return unable to parse")
            return ''

        xml.close()

        try:
            plname = dom.getElementsByTagName('name')
            self.log("getSmartPlaylistName return " + plname[0].childNodes[0].nodeValue)
            return plname[0].childNodes[0].nodeValue
        except:
            self.playlisy('Unable to find element name')

        self.log("getSmartPlaylistName return")


    def changeChanType(self, channel, val):
        self.log("changeChanType " + str(channel) + ", " + str(val))
        chantype = 9999

        try:
            chantype = int(ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_type"))
        except:
            self.log("Unable to get channel type")

        if val != 0:
            chantype += val

            if chantype < 0:
                chantype = 9999
            elif chantype == 10000:
                chantype = 0
            elif chantype == 9998:
                chantype = NUMBER_CHANNEL_TYPES - 1
            elif chantype == NUMBER_CHANNEL_TYPES:
                chantype = 9999

            ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_type", str(chantype))
        else:
            self.channel_type = chantype
            self.setting1 = ''
            self.setting2 = ''

            try:
                self.setting1 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_1")
                self.setting2 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_2")
            except:
                pass

        for i in range(NUMBER_CHANNEL_TYPES):
            if i == chantype:
                self.getControl(120 + i).setVisible(True)
                self.getControl(110).controlDown(self.getControl(120 + ((i + 1) * 10)))

                try:
                    self.getControl(111).controlDown(self.getControl(120 + ((i + 1) * 10 + 1)))
                except:
                    self.getControl(111).controlDown(self.getControl(120 + ((i + 1) * 10)))
            else:
                try:
                    self.getControl(120 + i).setVisible(False)
                except:
                    pass

        self.fillInDetails(channel)
        self.log("changeChanType return")


    def fillInDetails(self, channel):
        self.log("fillInDetails " + str(channel))
        self.getControl(104).setLabel("Channel " + str(channel))
        chantype = 9999
        chansetting1 = ''
        chansetting2 = ''

        try:
            chantype = int(ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_type"))
            chansetting1 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_1")
            chansetting2 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_2")
        except:
            self.log("Unable to get some setting")

        self.getControl(109).setLabel(self.getChanTypeLabel(chantype))

        if chantype == 0:
            plname = self.getSmartPlaylistName(chansetting1)

            if len(plname) == 0:
                chansetting1 = ''

            self.getControl(130).setLabel(self.getSmartPlaylistName(chansetting1), label2=chansetting1)
        elif chantype == 1:
            self.getControl(142).setLabel(self.findItemInList(self.networkList, chansetting1))
        elif chantype == 2:
            self.getControl(152).setLabel(self.findItemInList(self.studioList, chansetting1))
        elif chantype == 3:
            self.getControl(162).setLabel(self.findItemInList(self.showGenreList, chansetting1))
        elif chantype == 4:
            self.getControl(172).setLabel(self.findItemInList(self.movieGenreList, chansetting1))
        elif chantype == 5:
            self.getControl(182).setLabel(self.findItemInList(self.mixedGenreList, chansetting1))
        elif chantype == 6:
            self.getControl(192).setLabel(self.findItemInList(self.showList, chansetting1))
            self.getControl(194).setSelected(chansetting2 == str(MODE_ORDERAIRDATE))
        elif chantype == 7:
            self.getControl(200).setLabel(chansetting1)

        self.loadRules(channel)
        self.log("fillInDetails return")


    def loadRules(self, channel):
        self.log("loadRules")
        self.ruleList = []
        self.myRules.allRules

        try:
            rulecount = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rulecount'))

            for i in range(rulecount):
                ruleid = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rule_' + str(i + 1) + '_id'))

                for rule in self.myRules.allRules.ruleList:
                    if rule.getId() == ruleid:
                        self.ruleList.append(rule.copy())

                        for x in range(rule.getOptionCount()):
                            self.ruleList[-1].optionValues[x] = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rule_' + str(i + 1) + '_opt_' + str(x + 1))

                        foundrule = True
                        break
        except:
            self.ruleList = []


    def saveRules(self, channel):
        self.log("saveRules")
        rulecount = len(self.ruleList)
        ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_rulecount', str(rulecount))
        index = 1

        for rule in self.ruleList:
            ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_rule_' + str(index) + '_id', str(rule.getId()))

            for x in range(rule.getOptionCount()):
                ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_rule_' + str(index) + '_opt_' + str(x + 1), rule.getOptionValue(x))

            index += 1


    def findItemInList(self, thelist, item):
        loitem = item.lower()

        for i in thelist:
            if loitem == i.lower():
                return item

        if len(thelist) > 0:
            return thelist[0]

        return ''


    def getChanTypeLabel(self, chantype):
        if chantype == 0:
            return "Custom Playlist"
        elif chantype == 1:
            return "TV Network"
        elif chantype == 2:
            return "Movie Studio"
        elif chantype == 3:
            return "TV Genre"
        elif chantype == 4:
            return "Movie Genre"
        elif chantype == 5:
            return "Mixed Genre"
        elif chantype == 6:
            return "TV Show"
        elif chantype == 7:
            return "Directory"
        elif chantype == 9999:
            return "None"

        return ''

    def prepareConfig(self):
        self.log("prepareConfig")
        self.showList = []
        self.getControl(105).setVisible(False)
        self.getControl(106).setVisible(False)
        self.dlg = xbmcgui.DialogProgress()
        self.dlg.create("PseudoTV", "Preparing Configuration")
        self.dlg.update(1)
        chnlst = ChannelList()
        chnlst.fillTVInfo()
        self.dlg.update(40)
        chnlst.fillMovieInfo()
        self.dlg.update(80)
        self.mixedGenreList = chnlst.makeMixedList(chnlst.showGenreList, chnlst.movieGenreList)
        self.networkList = chnlst.networkList
        self.studioList = chnlst.studioList
        self.showGenreList = chnlst.showGenreList
        self.movieGenreList = chnlst.movieGenreList

        for i in range(len(chnlst.showList)):
            self.showList.append(chnlst.showList[i][0])

        self.mixedGenreList.sort(key=lambda x: x.lower())
        self.listcontrol = self.getControl(102)

        for i in range(200):
            theitem = xbmcgui.ListItem()
            theitem.setLabel(str(i + 1))
            self.listcontrol.addItem(theitem)


        self.dlg.update(90)
        self.updateListing()
        self.dlg.close()
        self.getControl(105).setVisible(True)
        self.getControl(106).setVisible(False)
        self.setFocusId(102)
        self.log("prepareConfig return")


    def updateListing(self, channel = -1):
        self.log("updateListing")
        start = 0
        end = 200

        if channel > -1:
            start = channel - 1
            end = channel

        for i in range(start, end):
            theitem = self.listcontrol.getListItem(i)
            chantype = 9999
            chansetting1 = ''
            chansetting2 = ''
            newlabel = ''

            try:
                chantype = int(ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_type"))
                chansetting1 = ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_1")
                chansetting2 = ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_2")
            except:
                pass

            if chantype == 0:
                newlabel = self.getSmartPlaylistName(chansetting1)
            elif chantype == 1 or chantype == 2 or chantype == 5 or chantype == 6:
                newlabel = chansetting1
            elif chantype == 3:
                newlabel = chansetting1 + " TV"
            elif chantype == 4:
                newlabel = chansetting1 + " Movies"
            elif chantype == 7:
                if chansetting1[-1] == '/' or chansetting1[-1] == '\\':
                    newlabel = os.path.split(chansetting1[:-1])[1]
                else:
                    newlabel = os.path.split(chansetting1)[1]

            theitem.setLabel2(newlabel)

        self.log("updateListing return")



__cwd__ = REAL_SETTINGS.getAddonInfo('path')


mydialog = ConfigWindow("script.pseudotv.ChannelConfig.xml", __cwd__, "default")
del mydialog
