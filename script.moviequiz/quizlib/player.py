import random
import threading
import db
import xbmc
import os
import re

class TenSecondPlayer(xbmc.Player):
    """TenSecondPlayer is a subclass of xbmc.Player that stops playback after about ten seconds."""

    def __init__(self, database = None):
        """
        Creates and instance of TenSecondPlayer.
        
        Keyword arguments;
        database - db.Database instance for loading and saving XBMC bookmark information
        """
        xbmc.Player.__init__(self)
        xbmc.log(">> TenSecondPlayer.__init__()")
        self.tenSecondTimer = None
        self.startTime = None

        self.database = database
        self.bookmark = None
        self.startingPlayback = False

    def stop(self):
        """
        Cancels the Timer in case it's active and stars a new Timer for a delayed stop.
        This method doesn't actually stop playback, this is handled by delayedStop().
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
        Starts playback bby calling xbmc.Player.play(windowed = True).

        It also loads bookmark information and keeps track on the Timer
        for stopping playback.
        """
        xbmc.log(">> TenSecondPlayer.playWindowed()")
        self.startingPlayback = True
        if self.tenSecondTimer is not None:
            #self.stop()
            self.tenSecondTimer.cancel()

        if file[-4:].lower() == '.ifo':
            file = self._getRandomDvdVob(file)
        elif file[-4:].lower() == '.iso':
            pass
            #todo file = self._getRandomDvdVob(file)

        # Get bookmark details, so we can restore after playback
        try:
            self.bookmark = self.database.fetchone("""
                SELECT idBookmark, timeInSeconds FROM bookmark WHERE idFile = ?
            """, idFile)
        except db.DbException:
            self.bookmark = {'idFile' : idFile}

        self.play(item = file, windowed = True)

        retries = 0
        while not self.isPlaying() and retries < 20:
            xbmc.sleep(250) # keep sleeping to get onPlayBackStarted() event
            retries += 1
        xbmc.log(">> TenSecondPlayer.playWindowed() - end")

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

        totalTime = self.getTotalTime()
        # find start time, ignore first 10% and last 20% of movie
        self.startTime = random.randint(int(totalTime * 0.1), int(totalTime * 0.8))

        xbmc.log(">> Playback from %d secs. to %d secs." % (self.startTime, self.startTime + 10))
        self.seekTime(self.startTime)

        self.tenSecondTimer = threading.Timer(10.0, self.onTenSecondsPassed)
        self.tenSecondTimer.start()

        self.startingPlayback = False
        xbmc.log(">> TenSecondPlayer.onPlayBackStarted() - end")

    def onPlayBackStopped(self):
        xbmc.log(">> TenSecondPlayer.onPlayBackStopped()")
        if self.tenSecondTimer is not None:
            self.tenSecondTimer.cancel()

        # Restore bookmark details
        if self.bookmark is not None:
            xbmc.sleep(1000) # Delay to allow XBMC to store the bookmark before we reset it
            if self.bookmark.has_key('idFile'):
                try:
                    self.database.execute("""
                        DELETE FROM bookmark WHERE idFile = ?
                    """, self.bookmark['idFile'])
                except db.DbException:
                    pass
            else:
                try:
                    self.database.execute("""
                        UPDATE bookmark SET timeInSeconds = ? WHERE idBookmark = ?
                    """, (self.bookmark['timeInSeconds'], self.bookmark['idBookmark']))
                except db.DbException:
                    pass

