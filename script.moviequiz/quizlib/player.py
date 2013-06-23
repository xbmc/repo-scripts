#
#      Copyright (C) 2013 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

import random
import threading
import os
import re

import xbmc
import xbmcvfs
import xbmcgui


class TenSecondPlayer(xbmc.Player):
    """TenSecondPlayer is a subclass of xbmc.Player that stops playback after about ten seconds."""

    def __init__(self):
        """
        Creates and instance of TenSecondPlayer.
        """
        xbmc.Player.__init__(self)
        xbmc.log(">> TenSecondPlayer.__init__()")
        self.tenSecondTimer = None

        self.startingPlayback = False

        self.lastItem = None
        self.lastStartPercentage = None

        self.playBackEventReceived = False
        self.isAudioFile = False

    def replay(self):
        xbmc.log(">> TenSecondPlayer.replay()")
        if self.lastItem is not None:
            self.playWindowed(self.lastItem, replay=True)

    def stopPlayback(self, force=False):
        """
        Cancels the Timer in case it's active and stars a new Timer for a delayed stop.
        This method doesn't actually stop playback, this is handled by _delayedStop().
        """
        xbmc.log(">> TenSecondPlayer.stop()")
        if force:
            self.startingPlayback = False
            # call xbmc.Player.stop() in a seperate thread to attempt to avoid xbmc lockups/crashes
        #threading.Timer(0.5, self._delayedStop).start()

        if not self.startingPlayback and self.isPlaying():
            xbmc.Player.stop(self)
        if self.tenSecondTimer is not None:
            self.tenSecondTimer.cancel()
        xbmc.log(">> TenSecondPlayer.stop() - end")

    def _delayedStop(self):
        """
        Stops playback by calling xbmc.Player.stop()

        This is done in a seperate thread to attempt to avoid xbmc lockups/crashes
        """
        xbmc.log(">> TenSecondPlayer.delayedStop()")

        if not self.startingPlayback and self.isPlaying():
            xbmc.Player.stop(self)
        xbmc.log(">> TenSecondPlayer.delayedStop() - end")

    def playWindowed(self, item, replay=False):
        """
        Starts playback by calling xbmc.Player.play(windowed = True).
        """
        xbmc.log(">> TenSecondPlayer.playWindowed()")
        self.startingPlayback = True

        if not xbmcvfs.exists(item):
            xbmc.log(">> TenSecondPlayer - file not found")  #: %s" % file.encode('utf-8', 'ignore'))
            return False

        self.lastItem = item

        if not replay:
            self.lastStartPercentage = None

        if self.tenSecondTimer is not None:
            #self.stop()
            self.tenSecondTimer.cancel()

        if item[-4:].lower() == '.ifo':
            item = self._getRandomDvdVob(item)
        elif item[-4:].lower() == '.iso':
            pass
            #todo file = self._getRandomDvdVob(file)

        #xbmc.log(">> TenSecondPlayer.playWindowed() - about to play file %s" % file.encode('utf-8', 'ignore'))

        self.isAudioFile = False
        self.playBackEventReceived = False

        if self.lastStartPercentage is None:
            self.lastStartPercentage = random.randint(10, 80)

        xbmc.log(">> Playback from %d%% for 10 seconds" % self.lastStartPercentage)

        listItem = xbmcgui.ListItem(path=item)
        listItem.setProperty("StartPercent", str(self.lastStartPercentage))
        # (Ab)use the original_listitem_url to avoid saving/overwriting a bookmark in the file
        listItem.setProperty("original_listitem_url", "plugin://script.moviequiz/dummy-savestate")
        self.play(item=item, listitem=listItem, windowed=True)

        retries = 0
        while not self.playBackEventReceived and retries < 20:
            xbmc.sleep(250)  # keep sleeping to get onPlayBackStarted() event
            retries += 1

        xbmc.log(">> TenSecondPlayer.playWindowed() - end")
        return True

    def playAudio(self, item):
        xbmc.log(">> TenSecondPlayer.playWindowed()")
        self.startingPlayback = True

        if not xbmcvfs.exists(item):
            xbmc.log(">> TenSecondPlayer - file not found")
            return False

        #xbmc.log(">> TenSecondPlayer.playWindowed() - about to play file %s" % file)

        self.bookmark = None
        self.isAudioFile = True
        self.playBackEventReceived = False
        self.play(item=item, windowed=True)

        retries = 0
        while not self.playBackEventReceived and retries < 20:
            xbmc.sleep(250)  # keep sleeping to get onPlayBackStarted() event
            retries += 1

    def _getRandomDvdVob(self, ifoFile):
        #xbmc.log(">> TenSecondPlayer._getRandomDvdVob() - ifoFile = %s" % ifoFile)

        if not os.path.exists(ifoFile):
            return ifoFile

        files = []
        path = os.path.dirname(ifoFile)
        for item in os.listdir(path):
            if re.search('vts_[0-9]{2}_[1-9].vob', item.lower()):
                files.append(item)

        random.shuffle(files)
        file = os.path.join(path, files[0])
        #xbmc.log(">> TenSecondPlayer._getRandomDvdVob() - file = %s" % file)
        return file

    def onTenSecondsPassed(self):
        """
        Invoked when the player has played for about ten seconds.
        
        The playback is stopped by calling xbmc.Player.stop()
        """
        xbmc.log(">> TenSecondPlayer.onTenSecondsPassed()")
        if self.startingPlayback:
            return

        if self.isPlaying():
            self.stopPlayback()

        retries = 0
        while self.isPlaying() and retries < 20 and not self.startingPlayback:
            xbmc.sleep(250)  # keep sleeping to get onPlayBackStopped() event
            retries += 1

    def onPlayBackStarted(self):
        xbmc.log(">> TenSecondPlayer.onPlayBackStarted()")
        self.playBackEventReceived = True

        if self.isAudioFile:
            self.startingPlayback = False
            return

        self.tenSecondTimer = threading.Timer(10.0, self.onTenSecondsPassed)
        self.tenSecondTimer.start()

        self.startingPlayback = False
        xbmc.log(">> TenSecondPlayer.onPlayBackStarted() - end")

    def onPlayBackStopped(self):
        xbmc.log(">> TenSecondPlayer.onPlayBackStopped()")
        self.playBackEventReceived = True

        if self.tenSecondTimer is not None:
            self.tenSecondTimer.cancel()
