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
from Globals import *
from ChannelList import ChannelList



NUMBER_CHANNEL_TYPES = 7



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
        self.doModal()
        self.log("__init__ return")


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('ChannelConfig: ' + msg, level)


    def onInit(self):
        self.log("onInit")

        for i in range(NUMBER_CHANNEL_TYPES):
            self.getControl(120 + i).setVisible(False)

        migrate()
        self.prepareConfig()
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
                ADDON_SETTINGS.setSetting(setting2, str(MODE_SERIAL))
        elif chantype == 9999:
            ADDON_SETTINGS.setSetting(setting1, '')
            ADDON_SETTINGS.setSetting(setting2, '')

        # Check to see if the user changed anything
        set1 = ''
        set2 = ''

        try:
            set1 = ADDON_SETTINGS.getSetting(setting1)
            set2 = ADDON_SETTINGS.getSetting(setting2)
        except:
            pass

        if chantype != self.channel_type or set1 != self.setting1 or set2 != self.setting2:
            ADDON_SETTINGS.setSetting('Channel_' + chan + '_changed', 'True')

        self.log("saveSettings return")


    def cancelChan(self):
        ADDON_SETTINGS.setSetting("Channel_" + str(self.channel) + "_type", str(self.channel_type))
        ADDON_SETTINGS.setSetting("Channel_" + str(self.channel) + "_1", self.setting1)
        ADDON_SETTINGS.setSetting("Channel_" + str(self.channel) + "_2", self.setting2)


    def hideChanDetails(self):
        self.getControl(106).setVisible(False)

        for i in range(NUMBER_CHANNEL_TYPES):
            self.getControl(120 + i).setVisible(False)

        self.setFocusId(102)
        self.getControl(105).setVisible(True)
        self.showingList = True
        self.updateListing(self.channel)
        self.listcontrol.selectItem(self.channel - 1)


    def onClick(self, controlId):
        self.log("onClick " + str(controlId))

        if controlId == 102:
            self.getControl(105).setVisible(False)
            self.getControl(106).setVisible(True)
            self.channel = self.listcontrol.getSelectedPosition() + 1
            self.changeChanType(self.channel, 0)
            self.setFocusId(110)
            self.showingList = False
        elif controlId == 110:
            self.changeChanType(self.channel, -1)
        elif controlId == 111:
            self.changeChanType(self.channel, 1)
        elif controlId == 112:
            self.saveSettings()
            self.hideChanDetails()
        elif controlId == 113:
            self.cancelChan()
            self.hideChanDetails()
        elif controlId == 130:
            dlg = xbmcgui.Dialog()
            retval = dlg.browse(1, "Channel " + str(self.channel) + " Playlist", "files", ".xsp", False, False, "special://videoplaylists/")

            if retval != "special://videoplaylists/":
                self.getControl(130).setLabel(self.getSmartPlaylistName(retval), label2=retval)
        elif controlId == 140:
            self.changeListData(self.networkList, 142, -1)
        elif controlId == 141:
            self.changeListData(self.networkList, 142, 1)
        elif controlId == 150:
            self.changeListData(self.studioList, 152, -1)
        elif controlId == 151:
            self.changeListData(self.studioList, 152, 1)
        elif controlId == 160:
            self.changeListData(self.showGenreList, 162, -1)
        elif controlId == 161:
            self.changeListData(self.showGenreList, 162, 1)
        elif controlId == 170:
            self.changeListData(self.movieGenreList, 172, -1)
        elif controlId == 171:
            self.changeListData(self.movieGenreList, 172, 1)
        elif controlId == 180:
            self.changeListData(self.mixedGenreList, 182, -1)
        elif controlId == 181:
            self.changeListData(self.mixedGenreList, 182, 1)
        elif controlId == 190:
            self.changeListData(self.showList, 192, -1)
        elif controlId == 191:
            self.changeListData(self.showList, 192, 1)

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
            xml = open(fle, "r")
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
                self.getControl(120 + i).setVisible(False)

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
            self.getControl(194).setSelected(chansetting2 == str(MODE_SERIAL))

        self.log("fillInDetails return")


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

            theitem.setLabel2(newlabel)

        self.log("updateListing return")




__cwd__ = REAL_SETTINGS.getAddonInfo('path')


mydialog = ConfigWindow("script.pseudotv.ChannelConfig.xml", __cwd__, "default")
del mydialog
