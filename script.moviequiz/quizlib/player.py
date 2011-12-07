import random
import threading
import db
import os
import re

import xbmc
import xbmcvfs

class TenSecondPlayer(xbmc.Player):
    """TenSecondPlayer is a subclass of xbmc.Player that stops playback after about ten seconds."""

    def __init__(self):
        """
        Creates and instance of TenSecondPlayer.
        """
        xbmc.Player.__init__(self)
        xbmc.log(">> TenSecondPlayer.__init__()")
        self.tenSecondTimer = None

        self.database = db.Database.connect()
        self.bookmark = None
        self.startingPlayback = False

        self.replaying = False
        self.lastFile = None
        self.lastIdFile = None
        self.lastStartTime = None

        self.playBackEventReceived = False
        self.isAudioFile = False

    def close(self):
        if hasattr(self, 'database') and self.database:
            self.database.close()
            print "TenSecondPlayer closed"

    def replay(self):
        xbmc.log(">> TenSecondPlayer.replay()")
        if self.lastFile is not None:
            self.replaying = True
            self.playWindowed(self.lastFile, self.lastIdFile)
            self.replaying = False

    def stop(self):
        """
        Cancels the Timer in case it's active and stars a new Timer for a delayed stop.
        This method doesn't actually stop playback, this is handled by _delayedStop().
        """
        xbmc.log(">> TenSecondPlayer.stop()")
        # call xbmc.Player.stop() in a seperate thread to attempt to avoid xbmc lockups/crashes
        threading.Timer(0.5, self._delayedStop).start()
        if self.tenSecondTimer is not None:
            self.tenSecondTimer.cancel()

    def _delayedStop(self):
        """
        Stops playback by calling xbmc.Player.stop()

        This is done in a seperate thread to attempt to avoid xbmc lockups/crashes
        """
        xbmc.log(">> TenSecondPlayer.delayedStop()")
        if not self.startingPlayback and self.isPlaying():
            xbmc.Player.stop(self)
        xbmc.log(">> TenSecondPlayer.delayedStop() - end")


    def playWindowed(self, file, idFile):
        """
        Starts playback by calling xbmc.Player.play(windowed = True).

        It also loads bookmark information and keeps track on the Timer
        for stopping playback.
        """
        xbmc.log(">> TenSecondPlayer.playWindowed()")
        self.startingPlayback = True

        if not xbmcvfs.exists(file):
            xbmc.log(">> TenSecondPlayer - file not found: %s" % file)
            return False

        self.lastFile = file
        self.lastIdFile= idFile

        if not self.replaying:
            self.lastStartTime = None

        if self.tenSecondTimer is not None:
            #self.stop()
            self.tenSecondTimer.cancel()

        if file[-4:].lower() == '.ifo':
            file = self._getRandomDvdVob(file)
        elif file[-4:].lower() == '.iso':
            pass
            #todo file = self._getRandomDvdVob(file)

        # Get bookmark details, so we can restore after playback
        self.bookmark = self.database.getVideoBookmark(idFile)

        xbmc.log(">> TenSecondPlayer.playWindowed() - about to play file %s" % file)

        self.isAudioFile = False
        self.playBackEventReceived = False
        self.play(item = file, windowed = True)

        retries = 0
        while not self.playBackEventReceived and retries < 20:
            xbmc.sleep(250) # keep sleeping to get onPlayBackStarted() event
            retries += 1

        xbmc.log(">> TenSecondPlayer.playWindowed() - end")
        return True

    def playAudio(self, file):
        xbmc.log(">> TenSecondPlayer.playWindowed()")
        self.startingPlayback = True

        if not xbmcvfs.exists(file):
            xbmc.log(">> TenSecondPlayer - file not found: %s" % file)
            return False

        xbmc.log(">> TenSecondPlayer.playWindowed() - about to play file %s" % file)

        self.bookmark = None
        self.isAudioFile = True
        self.playBackEventReceived = False
        self.play(item = file, windowed = True)

        retries = 0
        while not self.playBackEventReceived and retries < 20:
            xbmc.sleep(250) # keep sleeping to get onPlayBackStarted() event
            retries += 1

    def _getRandomDvdVob(self, ifoFile):
        xbmc.log(">> TenSecondPlayer._getRandomDvdVob() - ifoFile = %s" % ifoFile)

        files = []
        path = os.path.dirname(ifoFile)
        for item in os.listdir(path):
            if re.search('vts_[0-9]{2}_[1-9].vob', item.lower()):
                files.append(item)

        random.shuffle(files)
        file = os.path.join(path, files[0])
        xbmc.log(">> TenSecondPlayer._getRandomDvdVob() - file = %s" % file)
        return file

    def onTenSecondsPassed(self):
        """
        Invoked when the player has played for about ten seconds.
        
        The playback is stopped by calling xbmc.Player.stop()
        """
        xbmc.log(">> TenSecondPlayer.onTenSecondsPassed()")
        if self.startingPlayback:
            return

        xbmc.sleep(250)
        if self.isPlaying():
            xbmc.Player.stop(self)

        retries = 0
        while self.isPlaying() and retries < 20 and not self.startingPlayback:
            xbmc.sleep(250) # keep sleeping to get onPlayBackStopped() event
            retries += 1


    def onPlayBackStarted(self):
        xbmc.log(">> TenSecondPlayer.onPlayBackStarted()")
        self.playBackEventReceived = True

        if self.isAudioFile:
            self.startingPlayback = False
            return

        if self.lastStartTime is not None:
            startTime = self.lastStartTime
        else:
            totalTime = self.getTotalTime()
            # find start time, ignore first 10% and last 20% of movie
            startTime = random.randint(int(totalTime * 0.1), int(totalTime * 0.8))
            self.lastStartTime = startTime

        xbmc.log(">> Playback from %d secs. to %d secs." % (startTime, startTime + 10))
        self.seekTime(startTime)

        self.tenSecondTimer = threading.Timer(10.0, self.onTenSecondsPassed)
        self.tenSecondTimer.start()

        self.startingPlayback = False
        xbmc.log(">> TenSecondPlayer.onPlayBackStarted() - end")

    def onPlayBackStopped(self):
        xbmc.log(">> TenSecondPlayer.onPlayBackStopped()")
        self.playBackEventReceived = True

        if self.tenSecondTimer is not None:
            self.tenSecondTimer.cancel()

        # Restore bookmark details
        if self.bookmark is not None:
            xbmc.sleep(1000) # Delay to allow XBMC to store the bookmark before we reset it
            self.database.resetVideoBookmark(self.bookmark)
