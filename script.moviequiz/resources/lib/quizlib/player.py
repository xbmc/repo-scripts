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

import os, random, re, threading

import xbmc, xbmcgui, xbmcvfs

from resources.lib.util import logger


class TimeLimitedPlayer(xbmc.Player):
    """TimeLimitedPlayer is a subclass of xbmc.Player that stops playback after a limited amount of time"""

    def __init__(self, minPercent, maxPercent, duration):
        super().__init__()
        logger.debug("TimeLimitedPlayer.__init__()")
        self.setBounds(minPercent, maxPercent, duration)
        self.eventTimer = None
        self.startingPlayback = False
        self.lastItem = None
        self.lastStartPercentage = None
        self.playBackEventReceived = False

    def setBounds(self, minPercent, maxPercent, duration):
        self.minPercent = minPercent
        self.maxPercent = maxPercent
        self.duration = duration

    def replay(self):
        logger.debug("TimeLimitedPlayer.replay()")
        if self.lastItem is not None:
            self.playWindowed(self.lastItem, replay=True)

    def stopPlayback(self, force=False):
        """
        Cancels the Timer in case it's active and starts a new Timer for a delayed stop.
        """
        logger.debug("TimeLimitedPlayer.stop()")
        if force:
            self.startingPlayback = False

        if not self.startingPlayback and self.isPlaying():
            xbmc.Player.stop(self)
        if self.eventTimer is not None:
            self.eventTimer.cancel()
        logger.debug("TimeLimitedPlayer.stop() - end")

    def playWindowed(self, item, replay=False):
        """
        Starts playback by calling xbmc.Player.play(windowed=True).
        """
        logger.debug("TimeLimitedPlayer.playWindowed()")
        self.startingPlayback = True

        if not xbmcvfs.exists(item):
            logger.debug("TimeLimitedPlayer - file not found")
            return False

        self.lastItem = item

        if not replay:
            self.lastStartPercentage = None

        if self.eventTimer is not None:
            self.eventTimer.cancel()

        if item[-4:].lower() == '.ifo':
            item = self._getRandomDvdVob(item)
        elif item[-4:].lower() == '.iso':
            pass

        if self.lastStartPercentage is None:
            self.lastStartPercentage = random.randint(self.minPercent, self.maxPercent)

        logger.debug(f"Playback from {self.lastStartPercentage}% for {self.duration} seconds")

        listItem = xbmcgui.ListItem(path=item)
        listItem.setProperty("StartPercent", str(self.lastStartPercentage))
        # (Ab)use the original_listitem_url to avoid saving/overwriting a bookmark in the file
        listItem.setProperty("original_listitem_url", "plugin://script.moviequiz/dummy-savestate")

        self.playBackEventReceived = False
        self.play(item=item, listitem=listItem, windowed=True)

        retries = 0
        while not self.playBackEventReceived and retries < 20:
            xbmc.sleep(250)  # keep sleeping to get onAVStarted() event
            retries += 1

        logger.debug("TimeLimitedPlayer.playWindowed() - end")
        return True

    def _getRandomDvdVob(self, ifoFile):
        if not os.path.exists(ifoFile):
            return ifoFile

        files = []
        path = os.path.dirname(ifoFile)
        for item in os.listdir(path):
            if re.search('vts_[0-9]{2}_[1-9].vob', item.lower()):
                files.append(item)

        random.shuffle(files)
        file = os.path.join(path, files[0])
        return file

    def onTimerComplete(self):
        """
        Invoked when the player has played for the set amount of time.
        The playback is stopped by calling xbmc.Player.stop()
        """
        logger.debug("TimeLimitedPlayer.onTimerComplete()")
        if self.startingPlayback:
            return
        if self.isPlaying():
            self.stopPlayback()
        retries = 0
        self.playBackEventReceived = False
        while self.isPlaying() and retries < 20 and not self.playBackEventReceived:
            xbmc.sleep(250)  # keep sleeping to get onPlayBackStopped() event
            retries += 1

    def onAVStarted(self):
        logger.debug("TimeLimitedPlayer.onAVStarted()")
        self.playBackEventReceived = True

        if self.eventTimer is not None:
            self.eventTimer.cancel()
        logger.debug(f"TimeLimitedPlayer.onAVStarted() - setting timer for {self.duration} seconds")
        self.eventTimer = threading.Timer(self.duration, self.onTimerComplete)
        self.eventTimer.start()

        self.startingPlayback = False
        logger.debug("TimeLimitedPlayer.onAVStarted() - end")

    def onPlayBackStopped(self):
        logger.debug("TimeLimitedPlayer.onPlayBackStopped()")
        self.playBackEventReceived = True
        if self.eventTimer is not None:
            self.eventTimer.cancel()
