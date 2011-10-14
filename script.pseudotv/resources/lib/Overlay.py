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

from Playlist import Playlist
from Globals import *
from Channel import Channel
from EPGWindow import EPGWindow
from ChannelList import ChannelList
from ChannelListThread import ChannelListThread
from FileAccess import FileLock, FileAccess
from Migrate import Migrate



class MyPlayer(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self, xbmc.PLAYER_CORE_AUTO)
        self.stopped = False


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('Player: ' + msg, level)


    def onPlayBackStopped(self):
        if self.stopped == False:
            self.log('Playback stopped')

            if self.overlay.sleepTimeValue == 0:
                self.overlay.sleepTimer = threading.Timer(1, self.overlay.sleepAction)

            self.overlay.background.setVisible(True)
            self.overlay.sleepTimeValue = 1
            self.overlay.startSleepTimer()
            self.stopped = True



# overlay window to catch events and change channels
class TVOverlay(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.log('__init__')
        # initialize all variables
        self.channels = []
        self.Player = MyPlayer()
        self.Player.overlay = self
        self.inputChannel = -1
        self.channelLabel = []
        self.lastActionTime = 0
        self.actionSemaphore = threading.BoundedSemaphore()
        self.channelThread = ChannelListThread()
        self.channelThread.myOverlay = self
        self.setCoordinateResolution(1)
        self.timeStarted = 0
        self.infoOnChange = True
        self.infoOffset = 0
        self.invalidatedChannelCount = 0
        self.showingInfo = False
        self.showChannelBug = False
        self.notificationLastChannel = 0
        self.notificationLastShow = 0
        self.notificationShowedNotif = False
        self.isExiting = False
        self.maxChannels = 0
        self.notPlayingCount = 0
        self.ignoreInfoAction = False

        for i in range(3):
            self.channelLabel.append(xbmcgui.ControlImage(50 + (50 * i), 50, 50, 50, IMAGES_LOC + 'solid.png', colorDiffuse='0xAA00ff00'))
            self.addControl(self.channelLabel[i])
            self.channelLabel[i].setVisible(False)

        self.doModal()
        self.log('__init__ return')


    def resetChannelTimes(self):
        for i in range(self.maxChannels):
            self.channels[i].setAccessTime(self.timeStarted - self.channels[i].totalTimePlayed)


    def onFocus(self, controlId):
        pass


    # override the doModal function so we can setup everything first
    def onInit(self):
        self.log('onInit')

        if FileAccess.exists(GEN_CHAN_LOC) == False:
            try:
                FileAccess.makedirs(GEN_CHAN_LOC)
            except:
                self.Error('Unable to create the cache directory')
                return

        if FileAccess.exists(MADE_CHAN_LOC) == False:
            try:
                FileAccess.makedirs(MADE_CHAN_LOC)
            except:
                self.Error('Unable to create the storage directory')
                return

        self.background = self.getControl(101)
        self.getControl(102).setVisible(False)
        self.background.setVisible(True)
        updateDialog = xbmcgui.DialogProgress()
        updateDialog.create("PseudoTV", "Initializing")
        updateDialog.update(5, "Initializing", "Grabbing Lock File")
        ADDON_SETTINGS.loadSettings()
        updateDialog.update(70, "Initializing", "Checking Other Instances")
        self.isMaster = GlobalFileLock.lockFile("MasterLock", False)
        updateDialog.update(95, "Initializing", "Migrating")

        if self.isMaster:
            migratemaster = Migrate()
            migratemaster.migrate()

        self.channelLabelTimer = threading.Timer(5.0, self.hideChannelLabel)
        self.playerTimer = threading.Timer(2.0, self.playerTimerAction)
        self.playerTimer.name = "PlayerTimer"
        self.infoTimer = threading.Timer(5.0, self.hideInfo)
        self.masterTimer = threading.Timer(5.0, self.becomeMaster)
        self.myEPG = EPGWindow("script.pseudotv.EPG.xml", ADDON_INFO, "default")
        self.myEPG.MyOverlayWindow = self
        # Don't allow any actions during initialization
        self.actionSemaphore.acquire()
        updateDialog.close()
        self.timeStarted = time.time()

        if self.readConfig() == False:
            return

        self.myEPG.channelLogos = self.channelLogos
        self.maxChannels = len(self.channels)

        if self.maxChannels == 0:
            self.Error('Unable to find any channels. Please configure the addon.')
            return

        found = False

        for i in range(self.maxChannels):
            if self.channels[i].isValid:
                found = True
                break

        if found == False:
            self.Error("Unable to populate channels. Please verify that you", "have scraped media in your library and that you have", "properly configured channels.")
            return

        if self.sleepTimeValue > 0:
            self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)

        self.notificationTimer = threading.Timer(NOTIFICATION_CHECK_TIME, self.notificationAction)

        try:
            if self.forceReset == False:
                self.currentChannel = self.fixChannel(int(REAL_SETTINGS.getSetting("CurrentChannel")))
            else:
                self.currentChannel = self.fixChannel(1)
        except:
            self.currentChannel = self.fixChannel(1)

        self.resetChannelTimes()
        self.setChannel(self.currentChannel)
        self.background.setVisible(False)
        self.startSleepTimer()
        self.startNotificationTimer()
        self.playerTimer.start()

        if self.backgroundUpdating < 2 or self.isMaster == False:
            self.channelThread.name = "ChannelThread"
            self.channelThread.start()

        if self.isMaster == False:
            self.masterTimer.name = "MasterTimer"
            self.masterTimer.start()

        self.actionSemaphore.release()
        self.log('onInit return')


    def becomeMaster(self):
        self.isMaster = GlobalFileLock.lockFile("MasterLock", False)
        self.masterTimer = threading.Timer(5.0, self.becomeMaster)

        if self.isMaster == False and self.isExiting == False:
            self.masterTimer.name = "MasterTimer"
            self.masterTimer.start()

            # Perform this after start so that there isn't an issue with evaluation before it is
            # set.
            if self.isExiting:
                self.masterTimer.cancel()
        elif self.isMaster:
            self.log("Became master")


    # setup all basic configuration parameters, including creating the playlists that
    # will be used to actually run this thing
    def readConfig(self):
        self.log('readConfig')
        # Sleep setting is in 30 minute incriments...so multiply by 30, and then 60 (min to sec)
        self.sleepTimeValue = int(REAL_SETTINGS.getSetting('AutoOff')) * 1800
        self.log('Auto off is ' + str(self.sleepTimeValue))
        self.infoOnChange = REAL_SETTINGS.getSetting("InfoOnChange") == "true"
        self.log('Show info label on channel change is ' + str(self.infoOnChange))
        self.showChannelBug = REAL_SETTINGS.getSetting("ShowChannelBug") == "true"
        self.log('Show channel bug - ' + str(self.showChannelBug))
        self.forceReset = REAL_SETTINGS.getSetting('ForceChannelReset') == "true"
        self.channelResetSetting = REAL_SETTINGS.getSetting('ChannelResetSetting')
        self.log("Channel reset setting - " + str(self.channelResetSetting))
        self.channelLogos = xbmc.translatePath(REAL_SETTINGS.getSetting('ChannelLogoFolder'))
        self.backgroundUpdating = int(REAL_SETTINGS.getSetting("ThreadMode"))
        self.log("Background updating - " + str(self.backgroundUpdating))
        self.showNextItem = REAL_SETTINGS.getSetting("EnableComingUp") == "true"
        self.log("Show Next Item - " + str(self.showNextItem))
        self.hideShortItems = REAL_SETTINGS.getSetting("HideClips") == "true"
        self.log("Hide Short Items - " + str(self.hideShortItems))

        if FileAccess.exists(self.channelLogos) == False:
            self.channelLogos = IMAGES_LOC

        self.log('Channel logo folder - ' + self.channelLogos)
        chn = ChannelList()
        chn.myOverlay = self
        self.channels = chn.setupList()

        if self.channels is None:
            self.log('readConfig No channel list returned')
            self.end()
            return False

        self.Player.stop()
        self.log('readConfig return')
        return True


    # handle fatal errors: log it, show the dialog, and exit
    def Error(self, line1, line2 = '', line3 = ''):
        self.log('FATAL ERROR: ' + line1 + " " + line2 + " " + line3, xbmc.LOGFATAL)
        dlg = xbmcgui.Dialog()
        dlg.ok('Error', line1, line2, line3)
        del dlg
        self.end()


    def channelDown(self):
        self.log('channelDown')

        if self.maxChannels == 1:
            return

        self.background.setVisible(True)
        channel = self.fixChannel(self.currentChannel - 1, False)
        self.setChannel(channel)
        self.background.setVisible(False)
        self.log('channelDown return')


    def channelUp(self):
        self.log('channelUp')

        if self.maxChannels == 1:
            return

        self.background.setVisible(True)
        channel = self.fixChannel(self.currentChannel + 1)
        self.setChannel(channel)
        self.background.setVisible(False)
        self.log('channelUp return')


    def message(self, data):
        self.log('Dialog message: ' + data)
        dlg = xbmcgui.Dialog()
        dlg.ok('Info', data)
        del dlg


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('TVOverlay: ' + msg, level)


    # set the channel, the proper show offset, and time offset
    def setChannel(self, channel):
        self.log('setChannel ' + str(channel))
        
        if self.Player.stopped:
            return

        if channel < 1 or channel > self.maxChannels:
            self.log('setChannel invalid channel ' + str(channel), xbmc.LOGERROR)
            return

        if self.channels[channel - 1].isValid == False:
            self.log('setChannel channel not valid ' + str(channel), xbmc.LOGERROR)
            return

        self.lastActionTime = 0
        timedif = 0
        self.getControl(102).setVisible(False)
        self.showingInfo = False

        # first of all, save playing state, time, and playlist offset for
        # the currently playing channel
        if self.Player.isPlaying():
            if channel != self.currentChannel:
                self.channels[self.currentChannel - 1].setPaused(xbmc.getCondVisibility('Player.Paused'))

                # Automatically pause in serial mode
                if self.channels[self.currentChannel - 1].mode & MODE_ALWAYSPAUSE > 0:
                    self.channels[self.currentChannel - 1].setPaused(True)

                self.channels[self.currentChannel - 1].setShowTime(self.Player.getTime())
                self.channels[self.currentChannel - 1].setShowPosition(xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition())
                self.channels[self.currentChannel - 1].setAccessTime(time.time())

        self.currentChannel = channel
        # now load the proper channel playlist
        xbmc.PlayList(xbmc.PLAYLIST_MUSIC).clear()

        if xbmc.PlayList(xbmc.PLAYLIST_MUSIC).load(self.channels[channel - 1].fileName) == False:
            self.log("Error loading playlist")
            self.InvalidateChannel(channel)
            return

        # Disable auto playlist shuffling if it's on
        if xbmc.getInfoLabel('Playlist.Random').lower() == 'random':
            self.log('Random on.  Disabling.')
            xbmc.PlayList(xbmc.PLAYLIST_MUSIC).unshuffle()

        xbmc.executebuiltin("PlayerControl(repeatall)")
        curtime = time.time()
        timedif = (curtime - self.channels[self.currentChannel - 1].lastAccessTime)

        if self.channels[self.currentChannel - 1].isPaused == False:
            # adjust the show and time offsets to properly position inside the playlist
            while self.channels[self.currentChannel - 1].showTimeOffset + timedif > self.channels[self.currentChannel - 1].getCurrentDuration():
                timedif -= self.channels[self.currentChannel - 1].getCurrentDuration() - self.channels[self.currentChannel - 1].showTimeOffset
                self.channels[self.currentChannel - 1].addShowPosition(1)
                self.channels[self.currentChannel - 1].setShowTime(0)

        # set the show offset
        self.Player.playselected(self.channels[self.currentChannel - 1].playlistPosition)
        # set the time offset
        self.channels[self.currentChannel - 1].setAccessTime(curtime)

        if self.channels[self.currentChannel - 1].isPaused:
            self.channels[self.currentChannel - 1].setPaused(False)

            try:
                self.Player.seekTime(self.channels[self.currentChannel - 1].showTimeOffset)

                if self.channels[self.currentChannel - 1].mode & MODE_ALWAYSPAUSE == 0:
                    self.Player.pause()

                    if self.waitForVideoPaused() == False:
                        return
            except:
                self.log('Exception during seek on paused channel', xbmc.LOGERROR)
        else:
            seektime = self.channels[self.currentChannel - 1].showTimeOffset + timedif + int((time.time() - curtime))

            try:
                self.Player.seekTime(seektime)
            except:
                self.log("Unable to set proper seek time, trying different value")

                try:
                    seektime = self.channels[self.currentChannel - 1].showTimeOffset + timedif
                    self.Player.seekTime(seektime)
                except:
                    self.log('Exception during seek', xbmc.LOGERROR)

        self.showChannelLabel(self.currentChannel)
        self.lastActionTime = time.time()
        self.log('setChannel return')


    def InvalidateChannel(self, channel):
        self.log("InvalidateChannel" + str(channel))

        if channel < 1 or channel > self.maxChannels:
            self.log("InvalidateChannel invalid channel " + str(channel))
            return

        self.channels[channel - 1].isValid = False
        self.invalidatedChannelCount += 1

        if self.invalidatedChannelCount > 3:
            self.Error("Exceeded 3 invalidated channels. Exiting.")
            return

        remaining = 0

        for i in range(self.maxChannels):
            if self.channels[i].isValid:
                remaining += 1

        if remaining == 0:
            self.Error("No channels available. Exiting.")
            return

        self.setChannel(self.fixChannel(channel))


    def waitForVideoPaused(self):
        self.log('waitForVideoPaused')
        sleeptime = 0

        while sleeptime < TIMEOUT:
            xbmc.sleep(100)

            if self.Player.isPlaying():
                if xbmc.getCondVisibility('Player.Paused'):
                    break

            sleeptime += 100
        else:
            self.log('Timeout waiting for pause', xbmc.LOGERROR)
            return False

        self.log('waitForVideoPaused return')
        return True


    def setShowInfo(self):
        self.log('setShowInfo')

        if self.infoOffset > 0:
            self.getControl(502).setLabel('COMING UP:')
        elif self.infoOffset < 0:
            self.getControl(502).setLabel('ALREADY SEEN:')
        elif self.infoOffset == 0:
            self.getControl(502).setLabel('NOW WATCHING:')

        if self.hideShortItems and self.infoOffset != 0:
            position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
            curoffset = 0
            modifier = 1

            if self.infoOffset < 0:
                modifier = -1

            while curoffset != abs(self.infoOffset):
                position = self.channels[self.currentChannel - 1].fixPlaylistIndex(position + modifier)

                if self.channels[self.currentChannel - 1].getItemDuration(position) >= 60:
                    curoffset += 1
        else:
            position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition() + self.infoOffset

        self.getControl(503).setLabel(self.channels[self.currentChannel - 1].getItemTitle(position))
        self.getControl(504).setLabel(self.channels[self.currentChannel - 1].getItemEpisodeTitle(position))
        self.getControl(505).setLabel(self.channels[self.currentChannel - 1].getItemDescription(position))
        self.getControl(506).setImage(self.channelLogos + self.channels[self.currentChannel - 1].name + '.png')
        self.log('setShowInfo return')


    # Display the current channel based on self.currentChannel.
    # Start the timer to hide it.
    def showChannelLabel(self, channel):
        self.log('showChannelLabel ' + str(channel))

        if self.channelLabelTimer.isAlive():
            self.channelLabelTimer.cancel()
            self.channelLabelTimer = threading.Timer(5.0, self.hideChannelLabel)

        tmp = self.inputChannel
        self.hideChannelLabel()
        self.inputChannel = tmp
        curlabel = 0

        if channel > 99:
            self.channelLabel[curlabel].setImage(IMAGES_LOC + 'label_' + str(channel // 100) + '.png')
            self.channelLabel[curlabel].setVisible(True)
            curlabel += 1

        if channel > 9:
            self.channelLabel[curlabel].setImage(IMAGES_LOC + 'label_' + str((channel % 100) // 10) + '.png')
            self.channelLabel[curlabel].setVisible(True)
            curlabel += 1

        self.channelLabel[curlabel].setImage(IMAGES_LOC + 'label_' + str(channel % 10) + '.png')
        self.channelLabel[curlabel].setVisible(True)

        ##ADDED BY SRANSHAFT: USED TO SHOW NEW INFO WINDOW WHEN CHANGING CHANNELS
        if self.inputChannel == -1 and self.infoOnChange == True:
            self.infoOffset = 0
            self.showInfo(5.0)

        if self.showChannelBug == True:
            try:
                self.getControl(103).setImage(self.channelLogos + self.channels[self.currentChannel - 1].name + '.png')
            except:
                pass
        ##

        if xbmc.getCondVisibility('Player.ShowInfo'):
            xbmc.executehttpapi("SendKey(0xF049)")
            self.ignoreInfoAction = True

        self.channelLabelTimer.name = "ChannelLabel"
        self.channelLabelTimer.start()
        self.startNotificationTimer(10.0)
        self.log('showChannelLabel return')


    # Called from the timer to hide the channel label.
    def hideChannelLabel(self):
        self.log('hideChannelLabel')
        self.channelLabelTimer = threading.Timer(5.0, self.hideChannelLabel)

        for i in range(3):
            self.channelLabel[i].setVisible(False)

        self.inputChannel = -1
        self.log('hideChannelLabel return')


    def hideInfo(self):
        self.getControl(102).setVisible(False)
        self.infoOffset = 0
        self.showingInfo = False

        if self.infoTimer.isAlive():
            self.infoTimer.cancel()

        self.infoTimer = threading.Timer(5.0, self.hideInfo)


    def showInfo(self, timer):
        if self.hideShortItems:
            position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition() + self.infoOffset

            if self.channels[self.currentChannel - 1].getItemDuration(xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()) < 60:
                return

        self.getControl(102).setVisible(True)
        self.showingInfo = True
        self.setShowInfo()

        if self.infoTimer.isAlive():
            self.infoTimer.cancel()

        self.infoTimer = threading.Timer(timer, self.hideInfo)
        self.infoTimer.name = "InfoTimer"

        if xbmc.getCondVisibility('Player.ShowInfo'):
            xbmc.executehttpapi("SendKey(0xF049)")
            self.ignoreInfoAction = True

        self.infoTimer.start()


    # return a valid channel in the proper range
    def fixChannel(self, channel, increasing = True):
        while channel < 1 or channel > self.maxChannels:
            if channel < 1: channel = self.maxChannels + channel
            if channel > self.maxChannels: channel -= self.maxChannels

        if increasing:
            direction = 1
        else:
            direction = -1

        if self.channels[channel - 1].isValid == False:
            return self.fixChannel(channel + direction, increasing)

        return channel


    # Handle all input while videos are playing
    def onAction(self, act):
        action = act.getId()
        self.log('onAction ' + str(action))

        if self.Player.stopped:
            return

        # Since onAction isnt always called from the same thread (weird),
        # ignore all actions if we're in the middle of processing one
        if self.actionSemaphore.acquire(False) == False:
            self.log('Unable to get semaphore')
            return

        lastaction = time.time() - self.lastActionTime

        # during certain times we just want to discard all input
        if lastaction < 2:
            self.log('Not allowing actions')
            action = ACTION_INVALID

        self.startSleepTimer()

        if action == ACTION_SELECT_ITEM:
            # If we're manually typing the channel, set it now
            if self.inputChannel > 0:
                if self.inputChannel != self.currentChannel:
                    self.setChannel(self.inputChannel)

                self.inputChannel = -1
            else:
                # Otherwise, show the EPG
                if self.channelThread.isAlive():
                    self.channelThread.pause()

                if self.notificationTimer.isAlive():
                    self.notificationTimer.cancel()
                    self.notificationTimer = threading.Timer(NOTIFICATION_CHECK_TIME, self.notificationAction)

                if self.sleepTimeValue > 0:
                    if self.sleepTimer.isAlive():
                        self.sleepTimer.cancel()
                        self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)

                self.hideInfo()
                self.newChannel = 0
                self.myEPG.doModal()

                if self.channelThread.isAlive():
                    self.channelThread.unpause()

                self.startNotificationTimer()

                if self.newChannel != 0:
                    self.background.setVisible(True)
                    self.setChannel(self.newChannel)
                    self.background.setVisible(False)
        elif action == ACTION_MOVE_UP or action == ACTION_PAGEUP:
            self.channelUp()
        elif action == ACTION_MOVE_DOWN or action == ACTION_PAGEDOWN:
            self.channelDown()
        elif action == ACTION_MOVE_LEFT:
            if self.showingInfo:
                self.infoOffset -= 1
                self.showInfo(10.0)
            else:
                xbmc.executebuiltin("PlayerControl(SmallSkipBackward)")
        elif action == ACTION_MOVE_RIGHT:
            if self.showingInfo:
                self.infoOffset += 1
                self.showInfo(10.0)
            else:
                xbmc.executebuiltin("PlayerControl(SmallSkipForward)")
        elif action == ACTION_PREVIOUS_MENU:
            if self.showingInfo:
                self.hideInfo()
            else:
                dlg = xbmcgui.Dialog()

                if self.sleepTimeValue > 0:
                    if self.sleepTimer.isAlive():
                        self.sleepTimer.cancel()
                        self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)

                if dlg.yesno("Exit?", "Are you sure you want to exit PseudoTV?"):
                    self.end()
                    return  # Don't release the semaphore
                else:
                    self.startSleepTimer()

                del dlg
        elif action == ACTION_SHOW_INFO:
            if self.ignoreInfoAction:
                self.ignoreInfoAction = False
            else:
                if self.showingInfo:
                    self.hideInfo()

                    if xbmc.getCondVisibility('Player.ShowInfo'):
                        xbmc.executehttpapi("SendKey(0xF049)")
                        self.ignoreInfoAction = True
                else:
                    self.showInfo(10.0)
        elif action >= ACTION_NUMBER_0 and action <= ACTION_NUMBER_9:
            if self.inputChannel < 0:
                self.inputChannel = action - ACTION_NUMBER_0
            else:
                if self.inputChannel < 100:
                    self.inputChannel = self.inputChannel * 10 + action - ACTION_NUMBER_0

            self.showChannelLabel(self.inputChannel)
        elif action == ACTION_OSD:
            xbmc.executebuiltin("ActivateWindow(12901)")

        self.actionSemaphore.release()
        self.log('onAction return')


    # Reset the sleep timer
    def startSleepTimer(self):
        if self.sleepTimeValue == 0:
            return

        # Cancel the timer if it is still running
        if self.sleepTimer.isAlive():
            self.sleepTimer.cancel()
            self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)

        if self.Player.stopped == False:
            self.sleepTimer.name = "SleepTimer"
            self.sleepTimer.start()


    def startNotificationTimer(self, timertime = NOTIFICATION_CHECK_TIME):
        self.log("startNotificationTimer")

        if self.notificationTimer.isAlive():
            self.notificationTimer.cancel()
            self.notificationTimer = threading.Timer(timertime, self.notificationAction)

        if self.Player.stopped == False:
            self.notificationTimer.name = "NotificationTimer"
            self.notificationTimer.start()


    # This is called when the sleep timer expires
    def sleepAction(self):
        self.log("sleepAction")
        self.actionSemaphore.acquire()
#        self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)
        # TODO: show some dialog, allow the user to cancel the sleep
        # perhaps modify the sleep time based on the current show
        self.end()


    def notificationAction(self):
        self.log("notificationAction")
        docheck = False

        if self.showNextItem == False:
            return

        if self.Player.isPlaying():
            if self.notificationLastChannel != self.currentChannel:
                docheck = True
            else:
                if self.notificationLastShow != xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition():
                    docheck = True
                else:
                    if self.notificationShowedNotif == False:
                        docheck = True

            if docheck == True:
                self.notificationLastChannel = self.currentChannel
                self.notificationLastShow = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
                self.notificationShowedNotif = False

                if self.hideShortItems:
                    # Don't show any notification if the current show is < 60 seconds
                    if self.channels[self.currentChannel - 1].getItemDuration(self.notificationLastShow) < 60:
                        self.notificationShowedNotif = True

                timedif = self.channels[self.currentChannel - 1].getItemDuration(self.notificationLastShow) - self.Player.getTime()

                if self.notificationShowedNotif == False and timedif < NOTIFICATION_TIME_BEFORE_END and timedif > NOTIFICATION_DISPLAY_TIME:
                    nextshow = self.channels[self.currentChannel - 1].fixPlaylistIndex(self.notificationLastShow + 1)

                    if self.hideShortItems:
                        # Find the next show that is >= 60 seconds long
                        while nextshow != self.notificationLastShow:
                            if self.channels[self.currentChannel - 1].getItemDuration(nextshow) >= 60:
                                break

                            nextshow = self.channels[self.currentChannel - 1].fixPlaylistIndex(nextshow + 1)

                    xbmc.executebuiltin("Notification(Coming Up Next, " + self.channels[self.currentChannel - 1].getItemTitle(nextshow).replace(',', '') + ", " + str(NOTIFICATION_DISPLAY_TIME * 1000) + ")")
                    self.notificationShowedNotif = True

        self.startNotificationTimer()


    def playerTimerAction(self):
        self.playerTimer = threading.Timer(2.0, self.playerTimerAction)

        if self.Player.isPlaying():
            self.lastPlayTime = int(self.Player.getTime())
            self.lastPlaylistPosition = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
            self.notPlayingCount = 0
        else:
            self.notPlayingCount += 1
            self.log("Adding to notPlayingCount")

            if self.notPlayingCount == 3:
                self.end()
                return

        if self.Player.stopped == False:
            self.playerTimer.name = "PlayerTimer"
            self.playerTimer.start()


    # cleanup and end
    def end(self):
        self.log('end')
        # Prevent the player from setting the sleep timer
        self.Player.stopped = True
        self.background.setVisible(True)
        curtime = time.time()
        xbmc.executebuiltin("PlayerControl(repeatoff)")
        self.isExiting = True
        updateDialog = xbmcgui.DialogProgress()
        updateDialog.create("PseudoTV", "Exiting")
        updateDialog.update(0, "Exiting", "Removing File Locks")
        GlobalFileLock.close()

        if self.playerTimer.isAlive():
            self.playerTimer.cancel()
            self.playerTimer.join()

        if self.Player.isPlaying():
            self.lastPlayTime = self.Player.getTime()
            self.lastPlaylistPosition = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
            self.Player.stop()

        updateDialog.update(1, "Exiting", "Stopping Threads")

        try:
            if self.channelLabelTimer.isAlive():
                self.channelLabelTimer.cancel()
                self.channelLabelTimer.join()
        except:
            pass

        updateDialog.update(2)

        try:
            if self.notificationTimer.isAlive():
                self.notificationTimer.cancel()
                self.notificationTimer.join()
        except:
            pass

        updateDialog.update(3)

        try:
            if self.infoTimer.isAlive():
                self.infoTimer.cancel()
                self.infoTimer.join()
        except:
            pass

        updateDialog.update(4)

        try:
            if self.sleepTimeValue > 0:
                if self.sleepTimer.isAlive():
                    self.sleepTimer.cancel()
        except:
            pass

        updateDialog.update(5)

        try:
            if self.masterTimer.isAlive():
                self.masterTimer.cancel()
                self.masterTimer.join()
        except:
            pass

        if self.channelThread.isAlive():
            for i in range(30):
                try:
                    self.channelThread.join(1.0)
                except:
                    pass

                if self.channelThread.isAlive() == False:
                    break

                updateDialog.update(6 + i, "Exiting", "Stopping Threads")

            if self.channelThread.isAlive():
                self.log("Problem joining channel thread", xbmc.ERROR_LOG)

        if self.timeStarted > 0 and self.isMaster:
            updateDialog.update(35, "Exiting", "Saving Settings")
            validcount = 0

            for i in range(self.maxChannels):
                if self.channels[i].isValid:
                    validcount += 1

            if validcount > 0:
                incval = 65.0 / float(validcount)

                for i in range(self.maxChannels):
                    updateDialog.update(35 + int((incval * i)))

                    if self.channels[i].isValid:
                        if self.channels[i].mode & MODE_RESUME == 0:
                            ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', str(int(curtime - self.timeStarted + self.channels[i].totalTimePlayed)))
                        else:
                            if i == self.currentChannel - 1:
                                # Determine pltime...the time it at the current playlist position
                                pltime = 0
                                self.log("position for current playlist is " + str(self.lastPlaylistPosition))

                                for pos in range(self.lastPlaylistPosition):
                                    pltime += self.channels[i].getItemDuration(pos)

                                ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', str(pltime + self.lastPlayTime))
                            else:
                                tottime = 0

                                for j in range(self.channels[i].playlistPosition):
                                    tottime += self.channels[i].getItemDuration(j)

                                tottime += self.channels[i].showTimeOffset
                                ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', str(int(tottime)))

        if self.isMaster:
            try:
                REAL_SETTINGS.setSetting('CurrentChannel', str(self.currentChannel))
            except:
                pass

            ADDON_SETTINGS.setSetting('LastExitTime', str(int(curtime)))

        updateDialog.close()
        self.background.setVisible(False)
        self.close()
