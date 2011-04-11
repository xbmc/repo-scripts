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

from Playlist import Playlist
from Globals import *
from Channel import Channel



class EPGWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.focusRow = 0
        self.focusIndex = 0
        self.focusTime = 0
        self.focusEndTime = 0
        self.shownTime = 0
        self.centerChannel = 0
        self.rowCount = 6
        self.channelButtons = [None] * self.rowCount
        self.actionSemaphore = threading.BoundedSemaphore()
        self.lastActionTime = time.time()
        self.channelLogos = ''
        self.textcolor = "FFFFFFFF"
        self.focusedcolor = "FF7d7d7d"

        # Decide whether to use the current skin or the default skin.  If the current skin has the proper
        # image, then it should work.
        if os.path.exists(xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', xbmc.getSkinDir(), 'media'))):
            self.mediaPath = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', xbmc.getSkinDir(), 'media')) + '/'
        elif os.path.exists(xbmc.translatePath('special://skin/media/' + TIME_BAR)):
            self.mediaPath = xbmc.translatePath('special://skin/media/')
        elif xbmc.skinHasImage(TIME_BAR):
            self.mediaPath = ''
        else:
            self.mediaPath = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', 'default', 'media')) + '/'

        self.log('Media Path is ' + self.mediaPath)

        # Use the given focus and non-focus textures if they exist.  Otherwise use the defaults.
        if os.path.exists(self.mediaPath + BUTTON_FOCUS):
            self.textureButtonFocus = self.mediaPath + BUTTON_FOCUS
        else:
            self.textureButtonFocus = 'button-focus.png'

        if os.path.exists(self.mediaPath + BUTTON_NO_FOCUS):
            self.textureButtonNoFocus = self.mediaPath + BUTTON_NO_FOCUS
        else:
            self.textureButtonNoFocus = 'button-nofocus.png'

        for i in range(self.rowCount):
            self.channelButtons[i] = []


    def onFocus(self, controlid):
        pass


    # set the time labels
    def setTimeLabels(self, thetime):
        self.log('setTimeLabels')
        now = datetime.datetime.fromtimestamp(thetime)
        self.getControl(104).setLabel(now.strftime('%A, %b %d'))
        delta = datetime.timedelta(minutes=30)

        for i in range(3):
            self.getControl(101 + i).setLabel(now.strftime("%I:%M"))
            now = now + delta

        self.log('setTimeLabels return')


    def log(self, msg):
        log('EPG: ' + msg)


    def onInit(self):
        self.log('onInit')
        timex, timey = self.getControl(120).getPosition()
        timew = self.getControl(120).getWidth()
        timeh = self.getControl(120).getHeight()
        self.currentTimeBar = xbmcgui.ControlImage(timex, timey, timew, timeh, self.mediaPath + TIME_BAR)
        self.addControl(self.currentTimeBar)

        try:
            textcolor = int(self.getControl(100).getLabel(), 16)
            focusedcolor = int(self.getControl(100).getLabel2(), 16)

            if textcolor > 0:
                self.textcolor = hex(textcolor)[2:-1]

            if focusedcolor > 0:
                self.focusedcolor = hex(focusedcolor)[2:-1]
        except:
            pass

        if self.setChannelButtons(time.time(), self.MyOverlayWindow.currentChannel) == False:
            self.log('Unable to add channel buttons')
            return

        curtime = time.time()
        self.focusIndex = 0
        basex, basey = self.getControl(113).getPosition()
        baseh = self.getControl(113).getHeight()
        basew = self.getControl(113).getWidth()

        # set the button that corresponds to the currently playing show
        for i in range(len(self.channelButtons[2])):
            left, top = self.channelButtons[2][i].getPosition()
            width = self.channelButtons[2][i].getWidth()
            left = left - basex
            starttime = self.shownTime + (left / (basew / 5400.0))
            endtime = starttime + (width / (basew / 5400.0))

            if curtime >= starttime and curtime <= endtime:
                self.focusIndex = i
                self.setFocus(self.channelButtons[2][i])
                self.focusTime = starttime + 30
                self.focusEndTime = endtime
                break

        self.focusRow = 2
        self.setShowInfo()
        self.log('onInit return')


    # setup all channel buttons for a given time
    def setChannelButtons(self, starttime, curchannel):
        self.log('setChannelButtons ' + str(starttime) + ', ' + str(curchannel))
        xbmcgui.lock()
        self.removeControl(self.currentTimeBar)
        self.centerChannel = self.MyOverlayWindow.fixChannel(curchannel)
        # This is done twice to guarantee we go back 2 channels.  If the previous 2 channels
        # aren't valid, then doing a fix on curchannel - 2 may result in going back only
        # a single valid channel.
        curchannel = self.MyOverlayWindow.fixChannel(curchannel - 1, False)
        curchannel = self.MyOverlayWindow.fixChannel(curchannel - 1, False)
        starttime = self.roundToHalfHour(int(starttime))
        self.setTimeLabels(starttime)
        self.shownTime = starttime
        basex, basey = self.getControl(111).getPosition()
        basew = self.getControl(111).getWidth()
        tmpx, tmpy =  self.getControl(110 + self.rowCount).getPosition()
        timex, timey = self.getControl(120).getPosition()
        timew = self.getControl(120).getWidth()
        timeh = self.getControl(120).getHeight()

        for i in range(self.rowCount):
            self.setButtons(starttime, curchannel, i)
            self.getControl(301 + i).setLabel(self.MyOverlayWindow.channels[curchannel - 1].name)

            try:
                self.getControl(311 + i).setLabel(str(curchannel))
            except:
                pass

            try:
                self.getControl(321 + i).setImage(self.channelLogos + self.MyOverlayWindow.channels[curchannel - 1].name + ".png")
            except:
                pass

            curchannel = self.MyOverlayWindow.fixChannel(curchannel + 1)

        if time.time() >= starttime and time.time() < starttime + 5400:
            dif = int((starttime + 5400 - time.time()))
            self.currentTimeBar.setPosition(int((basex + basew - 2) - (dif * (basew / 5400.0))), timey)
        else:
            if time.time() < starttime:
                self.currentTimeBar.setPosition(basex + 2, timey)
            else:
                 self.currentTimeBar.setPosition(basex + basew - 2 - timew, timey)

        self.addControl(self.currentTimeBar)
        xbmcgui.unlock()
        self.log('setChannelButtons return')


    # round the given time down to the nearest half hour
    def roundToHalfHour(self, thetime):
        n = datetime.datetime.fromtimestamp(thetime)
        delta = datetime.timedelta(minutes=30)

        if n.minute > 29:
            n = n.replace(minute=30, second=0, microsecond=0)
        else:
            n = n.replace(minute=0, second=0, microsecond=0)

        return time.mktime(n.timetuple())


    # create the buttons for the specified channel in the given row
    def setButtons(self, starttime, curchannel, row):
        self.log('setButtons ' + str(starttime) + ", " + str(curchannel) + ", " + str(row))
        curchannel = self.MyOverlayWindow.fixChannel(curchannel)
        basex, basey = self.getControl(111 + row).getPosition()
        baseh = self.getControl(111 + row).getHeight()
        basew = self.getControl(111 + row).getWidth()

        if xbmc.Player().isPlaying() == False:
            self.log('No video is playing, not adding buttons')
            self.closeEPG()
            return False

        # go through all of the buttons and remove them
        for button in self.channelButtons[row]:
            self.removeControl(button)

        del self.channelButtons[row][:]

        # if the channel is paused, then only 1 button needed
        if self.MyOverlayWindow.channels[curchannel - 1].isPaused:
            self.channelButtons[row].append(xbmcgui.ControlButton(basex, basey, basew, baseh, self.MyOverlayWindow.channels[curchannel - 1].getCurrentTitle() + " (paused)", focusTexture=self.textureButtonFocus, noFocusTexture=self.textureButtonNoFocus, alignment=4, textColor=self.textcolor, focusedColor=self.focusedcolor))
            self.addControl(self.channelButtons[row][0])
        else:
            # Find the show that was running at the given time
            # Use the current time and show offset to calculate it
            # At timedif time, channelShowPosition was playing at channelTimes
            # The only way this isn't true is if the current channel is curchannel since
            # it could have been fast forwarded or rewinded (rewound)?
            if curchannel == self.MyOverlayWindow.currentChannel:
                playlistpos = int(xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition())
                videotime = xbmc.Player().getTime()
                reftime = time.time()
            else:
                playlistpos = self.MyOverlayWindow.channels[curchannel - 1].playlistPosition
                videotime = self.MyOverlayWindow.channels[curchannel - 1].showTimeOffset
                reftime = self.MyOverlayWindow.channels[curchannel - 1].lastAccessTime

            # normalize reftime to the beginning of the video
            reftime -= videotime

            while reftime > starttime:
                playlistpos -= 1
                # No need to check bounds on the playlistpos, the duration function makes sure it is correct
                reftime -= self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos)

            while reftime + self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos) < starttime:
                reftime += self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos)
                playlistpos += 1

            # create a button for each show that runs in the next hour and a half
            endtime = starttime + 5400
            totaltime = 0

            while reftime < endtime:
                xpos = int(basex + (totaltime * (basew / 5400.0)))
                tmpdur = self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos)
                shouldskip = False


                # this should only happen the first time through this loop
                # it shows the small portion of the show before the current one
                if reftime < starttime:
                    tmpdur -= starttime - reftime
                    reftime = starttime

                    if tmpdur < 60 * 3:
                        shouldskip = True

                width = int((basew / 5400.0) * tmpdur)

                if width + xpos > basex + basew:
                    width = basex + basew - xpos

                if shouldskip == False and width > 30:
                    self.channelButtons[row].append(xbmcgui.ControlButton(xpos, basey, width, baseh, self.MyOverlayWindow.channels[curchannel - 1].getItemTitle(playlistpos), focusTexture=self.textureButtonFocus, noFocusTexture=self.textureButtonNoFocus, alignment=4, textColor=self.textcolor, focusedColor=self.focusedcolor))
                    self.addControl(self.channelButtons[row][-1])

                totaltime += tmpdur
                reftime += tmpdur
                playlistpos += 1

        self.log('setButtons return')
        return True


    def onAction(self, act):
        self.log('onAction ' + str(act.getId()))

        if self.actionSemaphore.acquire(False) == False:
            self.log('Unable to get semaphore')
            return

        action = act.getId()

        if action == ACTION_PREVIOUS_MENU:
            self.closeEPG()
        elif action == ACTION_MOVE_DOWN:
            self.GoDown()
        elif action == ACTION_MOVE_UP:
            self.GoUp()
        elif action == ACTION_MOVE_LEFT:
            self.GoLeft()
        elif action == ACTION_MOVE_RIGHT:
            self.GoRight()
        elif action == ACTION_STOP:
            self.closeEPG()
        elif action == ACTION_SELECT_ITEM:
            lastaction = time.time() - self.lastActionTime

            if lastaction >= 2:
                self.selectShow()
                self.closeEPG()
                self.lastActionTime = time.time()

        self.actionSemaphore.release()
        self.log('onAction return')


    def closeEPG(self):
        self.log('closeEPG')

        try:
            self.removeControl(self.currentTimeBar)
            self.MyOverlayWindow.startSleepTimer()
        except:
            pass

        self.close()


    def onControl(self, control):
        self.log('onControl')


    # Run when a show is selected, so close the epg and run the show
    def onClick(self, controlid):
        self.log('onClick')

        if self.actionSemaphore.acquire(False) == False:
            self.log('Unable to get semaphore')
            return

        lastaction = time.time() - self.lastActionTime

        if lastaction >= 2:
            selectedbutton = self.getControl(controlid)

            for i in range(self.rowCount):
                for x in range(len(self.channelButtons[i])):
                    if selectedbutton == self.channelButtons[i][x]:
                        self.focusRow = i
                        self.focusIndex = x
                        self.selectShow()
                        self.closeEPG()
                        self.lastActionTime = time.time()
                        self.actionSemaphore.release()
                        self.log('onClick found button return')
                        return

            self.lastActionTime = time.time()
            self.closeEPG()

        self.actionSemaphore.release()
        self.log('onClick return')


    def GoDown(self):
        self.log('goDown')

        # change controls to display the proper junks
        if self.focusRow == self.rowCount - 1:
            self.setChannelButtons(self.shownTime, self.MyOverlayWindow.fixChannel(self.centerChannel + 1))
            self.focusRow = self.rowCount - 2

        self.setProperButton(self.focusRow + 1)
        self.log('goDown return')


    def GoUp(self):
        self.log('goUp')

        # same as godown
        # change controls to display the proper junks
        if self.focusRow == 0:
            self.setChannelButtons(self.shownTime, self.MyOverlayWindow.fixChannel(self.centerChannel - 1, False))
            self.focusRow = 1

        self.setProperButton(self.focusRow - 1)
        self.log('goUp return')


    def GoLeft(self):
        self.log('goLeft')

        # change controls to display the proper junks
        if self.focusIndex == 0:
            self.setChannelButtons(self.shownTime - 1800, self.centerChannel)

        self.focusTime -= 60
        self.setProperButton(self.focusRow, True)
        self.log('goLeft return')


    def GoRight(self):
        self.log('goRight')

        # change controls to display the proper junks
        if self.focusIndex == len(self.channelButtons[self.focusRow]) - 1:
            self.setChannelButtons(self.shownTime + 1800, self.centerChannel)

        self.focusTime = self.focusEndTime + 30
        self.setProperButton(self.focusRow, True)
        self.log('goRight return')


    # based on the current focus row and index, find the appropriate button in
    # the new row to set focus to
    def setProperButton(self, newrow, resetfocustime = False):
        self.log('setProperButton ' + str(newrow))
        self.focusRow = newrow
        basex, basey = self.getControl(111 + newrow).getPosition()
        baseh = self.getControl(111 + newrow).getHeight()
        basew = self.getControl(111 + newrow).getWidth()

        for i in range(len(self.channelButtons[newrow])):
            left, top = self.channelButtons[newrow][i].getPosition()
            width = self.channelButtons[newrow][i].getWidth()
            left = left - basex
            starttime = self.shownTime + (left / (basew / 5400.0))
            endtime = starttime + (width / (basew / 5400.0))

            if self.focusTime >= starttime and self.focusTime <= endtime:
                self.focusIndex = i
                self.setFocus(self.channelButtons[newrow][i])
                self.setShowInfo()
                self.focusEndTime = endtime

                if resetfocustime:
                    self.focusTime = starttime + 30

                self.log('setProperButton found button return')
                return

        self.focusIndex = 0
        self.setFocus(self.channelButtons[newrow][0])
        left, top = self.channelButtons[newrow][0].getPosition()
        width = self.channelButtons[newrow][0].getWidth()
        left = left - basex
        starttime = self.shownTime + (left / (basew / 5400.0))
        endtime = starttime + (width / (basew / 5400.0))
        self.focusEndTime = endtime

        if resetfocustime:
            self.focusTime = starttime + 30

        self.setShowInfo()
        self.log('setProperButton return')


    def setShowInfo(self):
        self.log('setShowInfo')
        basex, basey = self.getControl(111 + self.focusRow).getPosition()
        baseh = self.getControl(111 + self.focusRow).getHeight()
        basew = self.getControl(111 + self.focusRow).getWidth()
        # use the selected time to set the video
        left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
        width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
        left = left - basex + (width / 2)
        starttime = self.shownTime + (left / (basew / 5400.0))
        
        chnoffset = self.focusRow - 2
        newchan = self.centerChannel

        while chnoffset != 0:
            if chnoffset > 0:
                newchan = self.MyOverlayWindow.fixChannel(newchan + 1, True)
                chnoffset -= 1
            else:
                newchan = self.MyOverlayWindow.fixChannel(newchan - 1, False)
                chnoffset += 1

        plpos = self.determinePlaylistPosAtTime(starttime, newchan)

        if plpos == -1:
            self.log('Unable to find the proper playlist to set from EPG')
            return

        self.getControl(500).setLabel(self.MyOverlayWindow.channels[newchan - 1].getItemTitle(plpos))
        self.getControl(501).setLabel(self.MyOverlayWindow.channels[newchan - 1].getItemEpisodeTitle(plpos))
        self.getControl(502).setLabel(self.MyOverlayWindow.channels[newchan - 1].getItemDescription(plpos))
        self.getControl(503).setImage(self.channelLogos + self.MyOverlayWindow.channels[newchan - 1].name + '.png')
        self.log('setShowInfo return')


    # using the currently selected button, play the proper shows
    def selectShow(self):
        self.log('selectShow')
        basex, basey = self.getControl(111 + self.focusRow).getPosition()
        baseh = self.getControl(111 + self.focusRow).getHeight()
        basew = self.getControl(111 + self.focusRow).getWidth()
        # use the selected time to set the video
        left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
        width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
        left = left - basex + (width / 2)
        starttime = self.shownTime + (left / (basew / 5400.0))
        chnoffset = self.focusRow - 2
        newchan = self.centerChannel

        while chnoffset != 0:
            if chnoffset > 0:
                newchan = self.MyOverlayWindow.fixChannel(newchan + 1, True)
                chnoffset -= 1
            else:
                newchan = self.MyOverlayWindow.fixChannel(newchan - 1, False)
                chnoffset += 1

        plpos = self.determinePlaylistPosAtTime(starttime, newchan)

        if plpos == -1:
            self.log('Unable to find the proper playlist to set from EPG', xbmc.LOGERROR)
            return

        timedif = (time.time() - self.MyOverlayWindow.channels[newchan - 1].lastAccessTime)
        pos = self.MyOverlayWindow.channels[newchan - 1].playlistPosition
        showoffset = self.MyOverlayWindow.channels[newchan - 1].showTimeOffset

        # adjust the show and time offsets to properly position inside the playlist
        while showoffset + timedif > self.MyOverlayWindow.channels[newchan - 1].getItemDuration(pos):
            timedif -= self.MyOverlayWindow.channels[newchan - 1].getItemDuration(pos) - showoffset
            pos = self.MyOverlayWindow.channels[newchan - 1].fixPlaylistIndex(pos + 1)
            showoffset = 0

        if pos != plpos:
            self.MyOverlayWindow.channels[newchan - 1].setShowPosition(plpos)
            self.MyOverlayWindow.channels[newchan - 1].setShowPosition(plpos)
            self.MyOverlayWindow.channels[newchan - 1].setShowTime(0)
            self.MyOverlayWindow.channels[newchan - 1].setAccessTime(time.time())

        self.MyOverlayWindow.newChannel = newchan
        self.log('selectShow return')


    def determinePlaylistPosAtTime(self, starttime, channel):
        self.log('determinePlaylistPosAtTime ' + str(starttime) + ', ' + str(channel))
        channel = self.MyOverlayWindow.fixChannel(channel)

        # if the channel is paused, then it's just the current item
        if self.MyOverlayWindow.channels[channel - 1].isPaused:
            self.log('determinePlaylistPosAtTime paused return')
            return self.MyOverlayWindow.channels[channel - 1].playlistPosition
        else:
            # Find the show that was running at the given time
            # Use the current time and show offset to calculate it
            # At timedif time, channelShowPosition was playing at channelTimes
            # The only way this isn't true is if the current channel is curchannel since
            # it could have been fast forwarded or rewinded (rewound)?
            if channel == self.MyOverlayWindow.currentChannel:
                playlistpos = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition()
                videotime = xbmc.Player().getTime()
                reftime = time.time()
            else:
                playlistpos = self.MyOverlayWindow.channels[channel - 1].playlistPosition
                videotime = self.MyOverlayWindow.channels[channel - 1].showTimeOffset
                reftime = self.MyOverlayWindow.channels[channel - 1].lastAccessTime

            # normalize reftime to the beginning of the video
            reftime -= videotime

            while reftime > starttime:
                playlistpos -= 1
                reftime -= self.MyOverlayWindow.channels[channel - 1].getItemDuration(playlistpos)

            while reftime + self.MyOverlayWindow.channels[channel - 1].getItemDuration(playlistpos) < starttime:
                reftime += self.MyOverlayWindow.channels[channel - 1].getItemDuration(playlistpos)
                playlistpos += 1

            self.log('determinePlaylistPosAtTime return' + str(self.MyOverlayWindow.channels[channel - 1].fixPlaylistIndex(playlistpos)))
            return self.MyOverlayWindow.channels[channel - 1].fixPlaylistIndex(playlistpos)
