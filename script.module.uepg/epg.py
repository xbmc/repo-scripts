#   Copyright (C) 2019 Lunatixz
#
#
# This file is part of uEPG.
#
# uEPG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# uEPG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with uEPG.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import os, sys, time, datetime, re, traceback, urllib
import json, collections, utils, itertools, threading
import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon

class Player(xbmc.Player):
    def onPlayBackStarted(self):
        utils.log('onPlayBackStarted')
        self.uEPG.currentChannel = self.uEPG.newChannel
        
        
    def onPlayBackEnded(self):
        utils.log('onPlayBackEnded')
        self.uEPG.currentChannel = -1
        
        
    def onPlayBackStopped(self):
        utils.log('onPlayBackStopped')
        self.uEPG.currentChannel = -1
    
class Splash(xbmcgui.WindowXML):
    def onAction(self, act):
        pass
        
    def onClick(self, act):
        pass

class BackgroundWindow(xbmcgui.WindowXML):
    #todo channel surfing, channel input
    def onAction(self, act):
        action = act.getId()
        utils.log('BackgroundWindow, onAction ' + str(action))
        self.uEPG.playSFX(action) 
        lastaction = time.time() - self.uEPG.lastActTime
        if action in utils.ACTION_PREVIOUS_MENU: self.uEPG.toggleFullscreen()
        else:
            if action in utils.ACTION_MOVE_DOWN: self.uEPG.GoDown()
            elif action in utils.ACTION_MOVE_UP: self.uEPG.GoUp()

                
class uEPG(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.mediaPath      = ''
        self.toRemove       = []
        self.infoOffset     = 0
        self.infoOffsetV    = 0
        self.shownTime      = 0
        self.centerPosition = 0
        self.centerChannel  = 0
        self.currentChannel = 1
        self.newChannel     = -1
        self.focusRow       = 0
        self.defaultRows    = 9
        self.focusIndex     = -1
        self.onInitReturn   = False
        self.player         = Player()
        self.player.uEPG    = self
        self.rowCount       = (int(utils.getProperty("uEPG.rowCount") or self.defaultRows))
        self.overlay        = BackgroundWindow('%s.overlay.xml'%utils.ADDON_ID,utils.ADDON_PATH,"default")
        self.overlay.uEPG   = self

        
    def onInit(self):
        utils.log('onInit')
        utils.setProperty('uEPGRunning','True')
        self.closeCount   = 0
        curtime           = time.time()
        self.lastActTime  = time.time()
        self.windowID     = self.getWindowID()
        self.windowIDS    = ["ActivateWindow(fullscreenvideo)","ActivateWindow(%s)"%self.windowID]
        self.windowToggle = itertools.cycle(self.windowIDS).next

        if self.onInitReturn == False:
            utils.log('onInit, onInitReturn = False')
            self.guideLimit     = 14400
            self.rowCount       = self.chkRows(self.rowCount)
            self.epgButtonwidth = float((utils.getProperty("uEPG.buttonWidth"))         or "5400.0")
            self.timeCount      = int((utils.getProperty("uEPG.timeCount"))             or "3")
            self.textColor      = hex(int((utils.getProperty("uEPG.textColor")          or "0xFFFFFFFF"),16))[2:]
            self.disabledColor  = hex(int((utils.getProperty("uEPG.disabledColor")      or "0xFFFFFFFF"),16))[2:]
            self.focusedColor   = hex(int((utils.getProperty("uEPG.focusedColor")       or "0xFFFFFFFF"),16))[2:]
            self.shadowColor    = hex(int((utils.getProperty("uEPG.shadowColor")        or "0xFF000000"),16))[2:]
            self.pastColor      = hex(int((utils.getProperty("uEPG.pastColor")          or "0xFF0f85a5"),16))[2:]
            self.timeColor      = hex(int((utils.getProperty("uEPG.timeColor")          or "0xFF0f85a5"),16))[2:]
            self.futureColor    = hex(int((utils.getProperty("uEPG.futureColor")        or "0xFF0f85a5"),16))[2:]
            self.favColor       = hex(int((utils.getProperty("uEPG.favColor")           or "0xFFFFD700"),16))[2:]
            self.favDefault     = hex(int((utils.getProperty("uEPG.favDefault")         or "0x00000000"),16))[2:]
            self.singleLineFade = (utils.getProperty("uEPG.singleLineFade")             or "false") == "true"
            self.textFont       = (utils.getProperty("uEPG.timeCount")                  or "font12")
            self.timeFormat     = (urllib.unquote(utils.getProperty("uEPG.timeFormat")) or "%A, %B %d")
            self.clockMode      = int(utils.REAL_SETTINGS.getSetting("ClockMode"))
        
            self.channelButtons = [None] * self.rowCount
            for i in range(self.rowCount): self.channelButtons[i] = []
            try:
                self.removeControl(self.fadePast)
                self.removeControl(self.currentTimeBar)
            except: pass
                
            self.focusChannel   = self.getControl(33009)
            self.currentHighLT  = self.getControl(33010)
            self.currentTime    = self.getControl(33007)
            timetx, timety      = self.currentTime.getPosition()
            timetw              = self.currentTime.getWidth()
            timeth              = self.currentTime.getHeight()
            
            self.currentLine    = self.getControl(33013)
            timex, timey        = self.currentLine.getPosition()
            timew               = self.currentLine.getWidth()
            timeh               = self.currentLine.getHeight()
            self.timeButtonBar  = os.path.join(self.channelLST.mediaFolder,utils.TIME_BAR)
            self.currentTimeBar = xbmcgui.ControlImage(timex, timey, timew, timeh, self.timeButtonBar, colorDiffuse=self.timeColor) 
            self.addControl(self.currentTimeBar)
            
            self.pastLine       = self.getControl(33011)
            timex, timey        = self.pastLine.getPosition()
            timew               = self.pastLine.getWidth()
            timeh               = self.pastLine.getHeight()
            self.pastTime       = os.path.join(self.channelLST.mediaFolder,utils.PAST_FADE)
            self.fadePast       = xbmcgui.ControlImage(timex, timey, timew, timeh, self.pastTime, colorDiffuse=self.pastColor)
            self.addControl(self.fadePast)
            
            self.futureLine     = self.getControl(33012)
            timex, timey        = self.futureLine.getPosition()
            timew               = self.futureLine.getWidth()
            timeh               = self.futureLine.getHeight()
            self.futureTime     = os.path.join(self.channelLST.mediaFolder,utils.FUTURE_FADE)
            self.fadeFuture     = xbmcgui.ControlImage(timex, timey, timew, timeh, self.futureTime, colorDiffuse=self.futureColor)
            self.addControl(self.fadeFuture)

            self.TimeXYW = {}
            for i in range(self.timeCount):
                self.TimeXYW['Time%dX'%(i + 1)] = self.getControl(33101 + i).getPosition()[0]
                self.TimeXYW['Time%dY'%(i + 1)] = self.getControl(33101 + i).getPosition()[1]
                self.TimeXYW['Time%dW'%(i + 1)] = int(round(self.getControl(33101 + i).getWidth()//2))
        
            self.TimeRange = {}
            for i in range(self.timeCount):
                self.TimeRange['Time%dRange'%(i + 1)] = range(self.TimeXYW['Time%dX'%(i + 1)] - self.TimeXYW['Time%dW'%(i + 1)],self.TimeXYW['Time%dX'%(i + 1)] + self.TimeXYW['Time%dW'%(i + 1)])

        if self.setChannelButtons(curtime, self.fixChannel(self.currentChannel)) == False:
            utils.log('Unable to add channel buttons')
            utils.notificationDialog("%s Error, Contact %s for support"%(self.channelLST.pluginName, self.channelLST.pluginAuthor))
            self.closeUEPG()
 
        self.setChannelButtons(curtime, self.fixChannel(self.currentChannel))
        basex, basey = self.getControl(33611 + self.focusRow).getPosition()
        basew = self.getControl(33611 + self.focusRow).getWidth()
        
        for i in range(len(self.channelButtons[self.focusRow])):
            left, top = self.channelButtons[self.focusRow][i].getPosition()
            width = self.channelButtons[self.focusRow][i].getWidth()
            left  = left - basex
            starttime = self.shownTime + (left / (basew / self.epgButtonwidth))
            endtime   = starttime + (width / (basew / self.epgButtonwidth))

            if curtime >= starttime and curtime <= endtime:
                utils.log('curtime focusIndex = %s'%i)
                self.focusIndex = i
                self.setFocus(self.channelButtons[self.focusRow][i])
                self.focusTime    = int(curtime)
                self.focusEndTime = endtime
                break
                
        if self.focusIndex == -1:
            self.focusIndex = 0
            self.setFocus(self.channelButtons[self.focusRow][self.focusIndex])
            left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
            width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
            left  = left - basex
            starttime = self.shownTime + (left / (basew / self.epgButtonwidth))
            endtime   = starttime + (width / (basew / self.epgButtonwidth))
            self.focusTime    = int(starttime + 30)
            self.focusEndTime = endtime
        
        self.setProperButton(0)
        self.setShowInfo()
        self.onInitReturn = True
        utils.log('onInit return')
        
        
    def getWindowID(self):
        return xbmcgui.Window(xbmcgui.getCurrentWindowId())

        
    def chkRows(self, rowcount):
        precount = rowcount
        if self.channelLST.maxChannels < rowcount: rowcount = self.channelLST.maxChannels
        elif self.channelLST.maxChannels >= self.defaultRows and self.channelLST.skinPath.startswith(utils.ADDON_PATH): rowcount = self.defaultRows
        
        utils.log("chkRows, rowcount = " + str(rowcount))
        return rowcount
        
        
    def setPlayingTime(self, startTime, duration):
        utils.log("setPlayingTime")
        try:
            endTime = startTime + duration
            if startTime + endTime == 0:
                raise Exception()
            if self.clockMode == 0:
                st = datetime.datetime.fromtimestamp(float(startTime)).strftime("%I:%M %p").upper()
                et = datetime.datetime.fromtimestamp(float(endTime)).strftime("%I:%M %p").upper()
            else:
                st = datetime.datetime.fromtimestamp(float(startTime)).strftime("%H:%M")
                et = datetime.datetime.fromtimestamp(float(endTime)).strftime("%H:%M")
            utils.setProperty("Time",'%s - %s' % (st, et))
        except Exception as e: utils.clearProperty('Time')

            
    def setShowInfo(self):
        utils.log('setShowInfo')
        baseh        = self.getControl(33611 + self.focusRow).getHeight()
        basew        = self.getControl(33611 + self.focusRow).getWidth()
        basex, basey = self.getControl(33611 + self.focusRow).getPosition()

        width     = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
        left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
        left      = left - basex + (width / 2)
        starttime = self.shownTime + (left / (basew / self.epgButtonwidth))
        endtime   = starttime + (width / (basew / self.epgButtonwidth))
        chnoffset = self.focusRow
        newchan   = self.centerChannel
        newchan, chnoffset = self.getFocusChannel(newchan)
        
        plpos, reftime = self.determinePosAtTime(starttime, newchan)
        if plpos == -1:
            utils.log('Unable to find the proper playlist to set from EPG')
            return
            
        self.centerPosition = plpos
        startTime       = self.getItemStartTime(newchan, plpos)
        duration        = self.getItemDuration(newchan, plpos)
        self.mediaPath  = self.getItemMediaPath(newchan, plpos)
        self.listItem   = self.getItemListItem(newchan, plpos)
        self.label      = self.getItemLabel(newchan, plpos)
        self.type       = self.getItemType(newchan, plpos)
        self.contextLST = self.getContextList(newchan, plpos)
        self.newChannel = newchan
        self.setPlayingTime(startTime, duration)
        self.getControl(40000).reset()
        self.getControl(40000).addItem(self.listItem)
        utils.log('setShowInfo, pos = ' + str(plpos))
        
        
    def setTimeLabels(self, thetime):
        now = datetime.datetime.fromtimestamp(thetime)
        self.getControl(33005).setLabel(now.strftime(self.timeFormat))
        delta = datetime.timedelta(minutes=30)
        for i in range(self.timeCount):
            if self.clockMode == 0: self.getControl(33101 + i).setLabel(now.strftime("%I:%M%p").lower())
            else: self.getControl(33101 + i).setLabel(now.strftime("%H:%M"))
            now = now + delta
        utils.log('setTimeLabels return')

        
    def setChannelButtons(self, starttime, curchannel, singlerow = -1):
        starttime  = utils.roundToHalfHour(int(starttime))
        utils.log('setChannelButtons, starttime = ' + str(starttime) + ', curchannel = ' + str(curchannel))
        self.centerChannel = self.fixChannel(curchannel)
        self.shownTime = starttime
        self.setTimeLabels(starttime)
        
        myadds         = []
        basecur        = curchannel
        basew          = self.getControl(33611).getWidth()
        basex, basey   = self.getControl(33611).getPosition()
        timetw         = self.currentTime.getWidth()
        timeth         = self.currentTime.getHeight()
        timetx, timety = self.currentTime.getPosition()
        timew          = self.currentLine.getWidth()
        timeh          = self.currentLine.getHeight()
        timex, timey   = self.currentLine.getPosition()
        utils.log('setChannelButtons, settime')
        self.toRemove.append(self.fadePast)
        self.toRemove.append(self.fadeFuture)
        self.toRemove.append(self.currentTimeBar)
                    
        for i in range(self.rowCount):
            if singlerow == -1 or singlerow == i:
                self.setButtons(starttime, basecur, i)
                myadds.extend(self.channelButtons[i])
            basecur = self.fixChannel(basecur + 1)
        basecur = curchannel
        utils.log('setChannelButtons, row init')  

        for i in range(self.rowCount):
            self.getControl(33511 + i).setLabel(self.channelLST.channels[basecur-1].name)
            basecur = self.fixChannel(basecur + 1)
            
        self.currentHighLT.setVisible(False)
        for i in range(self.rowCount):
            chnumber  = self.channelLST.channels[curchannel - 1].number
            if self.channelLST.channels[curchannel - 1].isHDHR: label = "[COLOR=%s][B]%s[/COLOR] |[/B]"%('green', str(chnumber))
            else: label = '[B]%s |[/B]'%(str(chnumber))
            self.getControl(33111 + i).setLabel(label)
            self.getControl(33411 + i).setImage(self.channelLST.channels[curchannel - 1].logo)
            utils.setProperty('FavColor',{True:self.favColor,False:self.favDefault}[self.channelLST.channels[curchannel - 1].isFavorite])
            
            if curchannel == self.currentChannel:
                utils.log('setChannelButtons, current playing channel row')
                if xbmc.Player().isPlayingVideo(): self.currentHighLT.setVisible(True)
                chx , chy  = self.getControl(33611 + i).getPosition()
                chpx, chpy = self.currentHighLT.getPosition()
                self.currentHighLT.setPosition(chpx, chy)
            curchannel = self.fixChannel(curchannel + 1)

        curtime = time.time()
        if curtime >= starttime and curtime < starttime + self.epgButtonwidth:
            dif = int((starttime + self.epgButtonwidth - curtime)) 
            self.currentTime.setPosition(int((basex + basew - (timew / 2)) - (dif * (basew / self.epgButtonwidth))) - (timetw / 2), timety)
            self.currentTimeBar.setPosition(int((basex + basew - (timew / 2)) - (dif * (basew / self.epgButtonwidth))), timey)
        else:
            if curtime < starttime:
                self.currentTime.setPosition(-1800, timety)
                self.currentTimeBar.setPosition(basex, timey)
            else:
                self.currentTime.setPosition(-1800, timety)
                self.currentTimeBar.setPosition(basex + basew - timew, timey)

        now = datetime.datetime.now()
        if self.clockMode == 0: timeex = now.strftime("%I:%M%p").lower()
        else: timeex = now.strftime("%H:%M")
        self.currentTime.setLabel(timeex)
        
        TimeTX, TimeTY = self.currentTime.getPosition()
        TimeBX, TimeBY = self.currentTimeBar.getPosition()
        PFadeX, PFadeY = self.fadePast.getPosition()
        LTimeX         = (TimeBX + (timew / 2))
        self.fadePast.setWidth(LTimeX - PFadeX)
        FFadeX, FFadeY = self.fadeFuture.getPosition()
        self.fadeFuture.setPosition(LTimeX, PFadeY)
        self.fadeFuture.setWidth(((basew - basex) - (timew / 2)) + TimeBX)
        TimeBW     = int(self.currentTime.getWidth())
        TimeButton = range(LTimeX - int(round(TimeBW//2)),LTimeX + int(round(TimeBW//2)))
        if LTimeX < self.TimeXYW['Time1X']:
            self.fadePast.setVisible(False)
            self.fadeFuture.setVisible(False)
            self.currentTimeBar.setVisible(False)
            self.currentLine.setVisible(False)
        else:
            self.fadePast.setVisible(True)
            self.currentTimeBar.setVisible(True) 
            self.currentLine.setVisible(True)

        if LTimeX > self.TimeXYW['Time%dX'%(self.timeCount)]:
            self.currentTimeBar.setVisible(False)
            self.fadeFuture.setVisible(False)
        else:
            self.currentTimeBar.setVisible(True)
            self.fadeFuture.setVisible(True)
        
        myadds.append(self.fadePast)
        myadds.append(self.fadeFuture)
        myadds.append(self.currentTimeBar)
            
        if TimeTX == -1800:
            for i in range(self.timeCount): self.getControl(33101 + i).setVisible(True)     
        else:
            for i in range(self.timeCount):
                self.getControl(33101 + i).setVisible(True)
                for pos in self.TimeRange['Time%dRange'%(i + 1)]:
                    if pos in TimeButton:
                        self.getControl(33101 + i).setVisible(False)
                        break
        try: self.removeControls(self.toRemove)
        except:
            for cntrl in self.toRemove:
                try: self.removeControl(cntrl)
                except: pass
        try: self.addControls(myadds)
        except: utils.log('setChannelButtons, addControls busy')
        self.toRemove = []
        utils.log('setChannelButtons return')

        
    def getItemListItem(self, channel, position):
        utils.log('getItemListItem, channel = ' + str(channel) + ', position = ' + str(position))
        position = self.fixPlaylistIndex(channel, position)
        return self.channelLST.channels[channel - 1].listItems[position]
        
        
    def getContextList(self, channel, position):
        utils.log('getContextList, channel = ' + str(channel) + ', position = ' + str(position))
        position = self.fixPlaylistIndex(channel, position)
        item = self.channelLST.channels[channel - 1].guidedata[position]
        contextLST = (utils.loadJson(item.get('contextmenu','[]') or '[]'))
        utils.log('getContextList, contextLST = ' + str(contextLST))
        return contextLST
        
        
    def getItemMediaPath(self, channel, position):
        position = self.fixPlaylistIndex(channel, position)
        item = self.channelLST.channels[channel - 1].guidedata[position]
        mediaPath = (item.get('file','') or item.get('url','') or item.get('path',''))
        utils.log('getItemMediaPath, mediaPath = ' + mediaPath)
        return mediaPath
        
        
    def getItemStartTime(self, channel, position):
        position = self.fixPlaylistIndex(channel, position)
        item = self.channelLST.channels[channel - 1].guidedata[position]
        startTime = int(item['starttime'])
        utils.log('getItemStartTime, startTime = ' + str(startTime))
        return startTime
        
        
    def getItemGenre(self, channel, position):
        position = self.fixPlaylistIndex(channel, position)
        item = self.channelLST.channels[channel - 1].guidedata[position]
        genre = item.get('genre','unknown')
        genre = ' / '.join(genre) if isinstance(genre, list) else genre
        utils.log('getItemGenre, genre = ' + str(genre))
        return genre
        
        
    def getItemType(self, channel, position):
        position = self.fixPlaylistIndex(channel, position)
        item = self.channelLST.channels[channel - 1].guidedata[position]
        type = item.get('mediatype','tvshows')
        utils.log('getItemType, type = ' + str(type))
        return type

        
    def getItemDuration(self, channel, position):
        position = self.fixPlaylistIndex(channel, position)
        item = self.channelLST.channels[channel - 1].guidedata[position]
        duration = int((item.get('runtime','') or item.get('duration','')))
        utils.log('getItemDuration, duration = ' + str(duration))
        return duration
        
        
    def getItemLabel(self, channel, position):
        position = self.fixPlaylistIndex(channel, position)
        item = self.channelLST.channels[channel - 1].guidedata[position]
        label = (item.get('label','') or item.get('title',''))
        utils.log('getItemLabel, label = ' + label)
        return label
        
        
    def getItemLabel2(self, channel, position):
        position = self.fixPlaylistIndex(channel, position)
        item = self.channelLST.channels[channel - 1].guidedata[position]
        label2 = (item.get('label2',''))
        utils.log('getItemLabel2, label2 = ' + label2)
        return label2
        

    def fixPlaylistIndex(self, channel, index):
        size = self.channelLST.channels[channel - 1].listSize
        if size == 0: return index
        while index >= size: index -= size
        while index < 0: index += size
        return index

    
    def fixChannel(self, channel, increasing = True):
        while channel < 1 or channel > self.channelLST.maxChannels:
            if channel < 1: channel = self.channelLST.maxChannels + channel
            if channel > self.channelLST.maxChannels: channel -= self.channelLST.maxChannels
        if increasing: direction = 1
        else: direction = -1
        return channel
        
        
    def determinePosAtTime(self, starttime, channel):
        utils.log('determinePosAtTime, channel = ' + str(channel) + ', starttime = ' + str(starttime))
        playlistpos = 0
        curtime     = time.time()
        reftime     = curtime
        channel     = self.fixChannel(channel)
        epochBeginDate = (self.getItemStartTime(channel, playlistpos))
        while epochBeginDate + self.getItemDuration(channel, playlistpos) < curtime:
            utils.log('determinePosAtTime, channel = ' + str(channel) + ', loop epochBeginDate < now, playlistpos = ' + str(playlistpos))
            epochBeginDate += self.getItemDuration(channel, playlistpos)
            playlistpos = self.fixPlaylistIndex(channel, playlistpos + 1)
        
        utils.log('determinePosAtTime, channel = ' + str(channel) + ', live channel position = ' + str(playlistpos))
        videotime = curtime - epochBeginDate
        reftime -= videotime

        while reftime > starttime:
            utils.log('determinePosAtTime, channel = ' + str(channel) + ', loop reftime > starttime, playlistpos = ' + str(playlistpos))
            playlistpos -= 1
            reftime -= self.getItemDuration(channel, playlistpos)

        while reftime + self.getItemDuration(channel, playlistpos) < starttime:
            utils.log('determinePosAtTime, channel = ' + str(channel) + ', loop reftime < starttime, playlistpos = ' + str(playlistpos))
            reftime += self.getItemDuration(channel, playlistpos)
            playlistpos += 1
            
        playlistpos = self.fixPlaylistIndex(channel, playlistpos)
        utils.log('determinePosAtTime, channel = ' + str(channel) + ', return ' + str(playlistpos))
        return playlistpos, reftime

        
    def setButtons(self, starttime, curchannel, row):
        utils.log("setButtons, starttime = " + str(starttime) + ", curchannel = " + str(curchannel) + ", row = " + str(row))
        try:
            curchannel = self.fixChannel(curchannel)
            # if self.channelLST.channels[curchannel-1].isValid == False:
                # return
                
            basex, basey = self.getControl(33611 + row).getPosition()
            baseh = self.getControl(33611 + row).getHeight()
            basew = self.getControl(33611 + row).getWidth()
            buttonFocus   = os.path.join(self.channelLST.mediaFolder,utils.BUTTON_FOCUS)
            buttonNoFocus = os.path.join(self.channelLST.mediaFolder,utils.EPGGENRE_LOC,'COLOR_ButtonNoFocus.png')
            self.toRemove.extend(self.channelButtons[row])
            del self.channelButtons[row][:]
            
            totaltime = 0
            endtime   = starttime + self.epgButtonwidth
            playlistpos, reftime = self.determinePosAtTime(starttime, curchannel)
            
            if int(round(self.channelLST.channels[curchannel - 1].totalTime // self.channelLST.channels[curchannel - 1].listSize)) < 900:
                self.channelButtons[row].append(xbmcgui.ControlButton(basex, basey, basew, baseh, self.channelLST.channels[curchannel-1].name, focusTexture=buttonFocus, noFocusTexture=buttonNoFocus, alignment=4, shadowColor=self.shadowColor, font=self.textFont, textColor=self.textColor, focusedColor=self.focusedColor))
            else:
                while reftime < endtime:
                    xpos       = int(basex + (totaltime * (basew / self.epgButtonwidth)))
                    tmpdur     = self.getItemDuration(curchannel, playlistpos)
                    shouldskip = False
                    if reftime < starttime:
                        tmpdur -= starttime - reftime
                        reftime = starttime
                        if tmpdur < 60 * 3: shouldskip = True

                    if shouldskip == False:
                        nextlen = self.getItemDuration(curchannel, playlistpos + 1)
                        prevlen = self.getItemDuration(curchannel, playlistpos - 1)
                        if nextlen < 60: tmpdur += nextlen / 2
                        if prevlen < 60: tmpdur += prevlen / 2

                    width = int((basew / self.epgButtonwidth) * tmpdur)
                    if width < 30 and shouldskip == False:
                        width = 30
                        tmpdur = int(30.0 / (basew / self.epgButtonwidth))

                    if width + xpos > basex + basew: width = basex + basew - xpos
                    utils.log('setButtons, shouldskip = ' + str(shouldskip))
                    if shouldskip == False and width >= 30:
                        mylabel       = self.getItemLabel(curchannel, playlistpos)
                        mylabel2      = self.getItemLabel2(curchannel, playlistpos)
                        buttonNoFocus = os.path.join(self.channelLST.mediaFolder,utils.EPGGENRE_LOC,'COLOR_%s.png'%utils.getGenreColor(self.getItemGenre(curchannel,playlistpos)))
                        buttonNoFocus = buttonNoFocus if xbmcvfs.exists(buttonNoFocus) == True else os.path.join(self.channelLST.mediaFolder,utils.EPGGENRE_LOC,'COLOR_ButtonNoFocus.png')
                        buttonFocus   = os.path.join(self.channelLST.mediaFolder,utils.BUTTON_FOCUS)
                        tmpButton     = xbmcgui.ControlButton(xpos, basey, width, baseh, mylabel, focusTexture=buttonFocus, noFocusTexture=buttonNoFocus, alignment=4)
                        tmpButton.setLabel(mylabel, self.textFont, self.textColor, self.disabledColor, self.shadowColor, self.focusedColor, mylabel2)
                        self.channelButtons[row].append(tmpButton)

                    totaltime   += tmpdur
                    reftime     += tmpdur
                    playlistpos += 1
                
                    if ((totaltime//60)//60) >= self.guideLimit :
                        utils.log("setButtons, Broken big loop, too many loops, reftime is " + str(reftime) + ", endtime is " + str(endtime))
                        break
            #todo dynamic height for "genre" lineup breaks.
            if len(self.channelButtons[row]) == 0:
                utils.log('setButtons, no buttons')
                self.channelButtons[row].append(xbmcgui.ControlButton(basex, basey, basew, baseh, self.channelLST.channels[curchannel-1].name, focusTexture=buttonFocus, noFocusTexture=buttonNoFocus, alignment=4, shadowColor=self.shadowColor, font=self.textFont, textColor=self.textColor, focusedColor=self.focusedColor))
        except Exception as e: utils.log("setButtons, exception " + str(e), xbmc.LOGERROR)
        utils.log('setButtons return')
        return True

        
    def getFocusChannel(self, newchan):
        utils.log('getFocusChannel')
        chnoffset = self.focusRow
        while chnoffset != 0:
            if chnoffset > 0:
                newchan = self.fixChannel(newchan + 1, True)
                chnoffset -= 1
            else:
                newchan = self.fixChannel(newchan - 1, False)
                chnoffset += 1
        return newchan, chnoffset

        
    def setProperButton(self, newrow, resetfocustime=False):
        utils.log('setProperButton ' + str(newrow))
        self.focusRow = newrow
        baseh         = self.getControl(33611 + newrow).getHeight()
        basew         = self.getControl(33611 + newrow).getWidth()
        basex, basey  = self.getControl(33611 + newrow).getPosition()
        chx, chy = self.focusChannel.getPosition()
        self.focusChannel.setPosition(chx, basey)
        
        # if self.singleLineFade == True:
            # self.fadePast.setPosition(basex-basew, basey)
            # self.fadeFuture.setPosition(basex+basew, basey)
        
        for i in range(len(self.channelButtons[newrow])):
            width     = self.channelButtons[newrow][i].getWidth()
            left, top = self.channelButtons[newrow][i].getPosition()
            left      = left - basex
            starttime = self.shownTime + (left / (basew / self.epgButtonwidth))
            endtime   = starttime + (width / (basew / self.epgButtonwidth))
            if self.focusTime >= starttime and self.focusTime <= endtime:
                self.focusIndex = i
                self.setFocus(self.channelButtons[newrow][i])
                self.setShowInfo()
                self.focusEndTime = endtime
                if resetfocustime: self.focusTime = starttime + 30
                utils.log('setProperButton, found button return')
                return

        self.focusIndex = 0
        self.setFocus(self.channelButtons[newrow][0])
        width     = self.channelButtons[newrow][0].getWidth()
        left, top = self.channelButtons[newrow][0].getPosition()
        left      = left - basex
        starttime = self.shownTime + (left / (basew / self.epgButtonwidth))
        endtime   = starttime + (width / (basew / self.epgButtonwidth))
        self.focusEndTime = endtime
        if resetfocustime: self.focusTime = starttime + 30
        self.setShowInfo()
        utils.log('setProperButton return')

        
    def GoPgDown(self):
        utils.log('GoPgDown')
        try:
            newchannel = self.centerChannel
            for x in range(0, self.rowCount): newchannel = self.fixChannel(newchannel + 1)
            self.setChannelButtons(self.shownTime, self.fixChannel(newchannel))
            self.setProperButton(0)
            self.infoOffsetV = self.infoOffsetV - self.rowCount
            utils.log('GoPgDown return') 
        except Exception as e: utils.log("GoPgDown, failed! " + str(e), xbmc.LOGERROR)

    
    def GoPgUp(self):
        utils.log('GoPgUp')
        try:
            newchannel = self.centerChannel
            for x in range(0, self.rowCount): newchannel = self.fixChannel(newchannel - 1, False)
            self.setChannelButtons(self.shownTime, self.fixChannel(newchannel))
            self.setProperButton(0)
            self.infoOffsetV = self.infoOffsetV + self.rowCount
            utils.log('GoPgUp return')
        except Exception as e: utils.log("GoPgUp, failed! " + str(e), xbmc.LOGERROR)


    def GoDown(self):
        utils.log('goDown')
        try:
            if self.focusRow == ((self.rowCount - 1) or self.getFocusId() == 40001):
                self.setChannelButtons(self.shownTime, self.fixChannel(self.centerChannel + 1))
                self.focusRow = self.rowCount - 2
            self.setProperButton(self.focusRow + 1)
            self.infoOffsetV = self.infoOffsetV - 1
            if self.getWindowID() == 12005: self.selectAction()
            utils.log('goDown return')
        except Exception as e: utils.log("goDown, failed! " + str(e), xbmc.LOGERROR)

        
    def GoUp(self):
        utils.log('goUp')
        try:
            newchan, chnoffset = self.getFocusChannel(self.centerChannel)
            if self.focusRow == 0 and newchan == 1:
                utils.log('goUp, EPG Menu')
                self.focusRow = -1
                xbmc.executebuiltin('Control.SetFocus(%s,1)'%(40001))
                return
            if self.focusRow <= 0:
                utils.log('goUp, default') 
                self.setChannelButtons(self.shownTime, self.fixChannel(self.centerChannel - 1, False))
                self.focusRow = 1
            self.setProperButton(self.focusRow - 1)
            self.infoOffsetV = self.infoOffsetV + 1
            if self.getWindowID() == 12005: self.selectAction()
            utils.log('goUp, return')
        except Exception as e: utils.log("goUp, failed! " + str(e), xbmc.LOGERROR)

    
    def GoLeft(self):
        utils.log('goLeft')
        try:     
            basex, basey = self.getControl(33611 + self.focusRow).getPosition()
            basew = self.getControl(33611 + self.focusRow).getWidth()
            if self.focusIndex == 0:
                left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
                width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
                left = left - basex
                starttime = self.shownTime + (left / (basew / self.epgButtonwidth))  
                self.setChannelButtons(self.shownTime - 1800, self.centerChannel)
                curbutidx = self.findButtonAtTime(self.focusRow, starttime + 30)
                if(curbutidx - 1) >= 0: self.focusIndex = curbutidx - 1
                else: self.focusIndex = 0
            else: self.focusIndex -= 1
            left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
            width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
            left = left - basex
            starttime = self.shownTime + (left / (basew / self.epgButtonwidth))
            endtime = starttime + (width / (basew / self.epgButtonwidth))
            self.setFocus(self.channelButtons[self.focusRow][self.focusIndex])
            self.setShowInfo()
            self.focusEndTime = endtime
            self.focusTime = starttime + 30
            self.infoOffset = self.infoOffset - 1
            utils.log('goLeft return') 
        except Exception as e: utils.log("goLeft, failed! " + str(e), xbmc.LOGERROR)

    
    def GoRight(self):
        utils.log('goRight')
        try:
            basex, basey = self.getControl(33611 + self.focusRow).getPosition()
            basew = self.getControl(33611 + self.focusRow).getWidth()
            if self.focusIndex == len(self.channelButtons[self.focusRow]) - 1:
                left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
                width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
                left = left - basex
                starttime = self.shownTime + (left / (basew / self.epgButtonwidth)) 
                self.setChannelButtons(self.shownTime + 1800, self.centerChannel)
                curbutidx = self.findButtonAtTime(self.focusRow, starttime + 30)
                if(curbutidx + 1) < len(self.channelButtons[self.focusRow]): self.focusIndex = curbutidx + 1
                else: self.focusIndex = len(self.channelButtons[self.focusRow]) - 1
            else: self.focusIndex += 1
            left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
            width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
            left = left - basex
            starttime = self.shownTime + (left / (basew / self.epgButtonwidth))
            endtime = starttime + (width / (basew / self.epgButtonwidth))
            self.setFocus(self.channelButtons[self.focusRow][self.focusIndex])
            self.setShowInfo()
            self.focusEndTime = endtime
            self.focusTime = starttime + 30  
            self.infoOffset = self.infoOffset + 1
            utils.log('goRight return')
        except Exception as e: utils.log("goRight, failed! " + str(e), xbmc.LOGERROR)
                    
        
    def findButtonAtTime(self, row, selectedtime):
        utils.log('findButtonAtTime ' + str(row))
        basex, basey = self.getControl(33611 + row).getPosition()
        baseh = self.getControl(33611 + row).getHeight()
        basew = self.getControl(33611 + row).getWidth()
        for i in range(len(self.channelButtons[row])):
            left, top = self.channelButtons[row][i].getPosition()
            width = self.channelButtons[row][i].getWidth()
            left = left - basex
            starttime = self.shownTime + (left/ (basew / self.epgButtonwidth))
            endtime = starttime + (width / (basew / self.epgButtonwidth))
            if selectedtime >= starttime and selectedtime <= endtime: return i
        return -1
        
        
    def playSFX(self,action):
        utils.log("playSFX")
        if action in ['ACTION_CLICK'] + utils.ACTION_SELECT_ITEM + utils.ACTION_MOVE_DOWN + utils.ACTION_MOVE_UP +utils.ACTION_MOVE_LEFT + utils.ACTION_MOVE_RIGHT: xbmc.playSFX(utils.SELECT_SFX)
        elif action in utils.ACTION_CONTEXT_MENU + utils.ACTION_PAGEDOWN + utils.ACTION_PAGEUP: xbmc.playSFX(utils.CONTEXT_SFX)
        elif action in utils.ACTION_PREVIOUS_MENU: xbmc.playSFX(utils.BACK_SFX)
        elif action in ['ACTION_ALERT']: xbmc.playSFX(utils.ALERT_SFX)
        
        
    def toggleFullscreen(self):
        utils.log('toggleFullscreen')
        if self.player.isPlayingVideo(): xbmc.executebuiltin(self.windowToggle())
        return
        
            
    def buildContextMenu(self):
        utils.log('buildContextMenu')
        tmpLST = ['Information']
        for item in self.contextLST: tmpLST.append(item[0])
        select = xbmcgui.Dialog().contextmenu(tmpLST)
        if select < 0: return
        elif select == 0: return self.showInfo()
        item = (self.contextLST[select-1][1])
        return xbmc.executebuiltin(item)
            
            
    def showInfo(self):
        curListItem = self.listItem
        try: curListItem = utils.buildListItem(utils.getMeta(self.label,self.type))
        except: pass
        xbmcgui.Dialog().info(curListItem)
            
            
    def onAction(self, act): 
        action = act.getId()
        utils.log('onAction ' + str(action))
        self.playSFX(action) 
        lastaction = time.time() - self.lastActTime
        
        if action in utils.ACTION_PREVIOUS_MENU:
            self.closeCount = self.closeCount + 1
            if self.closeCount == 2:
                plug = self.channelLST.pluginName
                head = '%s / %s'%(utils.ADDON_NAME,plug)
                if utils.yesnoDialog(utils.LANGUAGE(30001)%plug,header=head) == True: self.closeUEPG()
                else: self.closeCount = 0
            else: self.toggleFullscreen()
        else:
            self.closeCount = 0
            if action in utils.ACTION_MOVE_DOWN: self.GoDown()
            elif action in utils.ACTION_MOVE_UP: self.GoUp()
            elif action in utils.ACTION_MOVE_LEFT:
                if self.infoOffset <= -2: return
                self.GoLeft()
            elif action in utils.ACTION_MOVE_RIGHT: self.GoRight()
            elif action in utils.ACTION_PAGEDOWN: self.GoPgDown()
            elif action in utils.ACTION_PAGEUP: self.GoPgUp()
            elif action in utils.ACTION_CONTEXT_MENU: self.buildContextMenu()
            elif action in utils.ACTION_SELECT_ITEM and self.getFocusId() <= 40000: self.selectAction()

                
    def onClick(self, controlid):
        utils.log('onClick, controlid = ' + str(controlid))
        
        
    def onFocus(self, controlid):
        utils.log('onFocus, controlid = ' + str(controlid))
        
        
    def selectAction(self):
        utils.log('selectAction, url = ' + self.mediaPath)
        self.player.play(self.mediaPath,self.listItem)
    
    
    def closeUEPG(self):
        del self.player
        self.removeControls(self.toRemove)
        for thread in threading.enumerate():
            if thread.name != "MainThread":
                try:
                    utils.log('canceling threads...')
                    thread.cancel()
                    thread.join()
                except Exception as e: utils.log('closeUEPG, failed to close thread ' + str(e), xbmc.LOGERROR)             
        utils.setProperty('uEPGRunning','False')
        #reopen originating plugin to avoid reloading uEPG on exit.
        xbmc.executebuiltin('XBMC.AlarmClock(%s,ActivateWindow(Videos,plugin://%s),0.5,true)'%('',self.channelLST.pluginPath))
        self.close