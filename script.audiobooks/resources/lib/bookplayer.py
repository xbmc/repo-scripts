# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon

__addon__ = xbmcaddon.Addon(id='script.audiobooks')

# Import the common settings
from settings import log

from database import AudioBooksDB


#######################################
# Custom Player to play the audio book
#######################################
class BookPlayer(xbmc.Player):

    # Calls the media player to play the selected item
    @staticmethod
    def playAudioBook(audioBookHandler, startTime=-1, chapter=0):
        log("BookPlayer: Playing audio book = %s" % audioBookHandler.getFile())

        bookPlayer = BookPlayer()

        playlist = audioBookHandler.getPlayList(startTime, chapter)

        bookPlayer.play(playlist)

        # Don't allow this to loop forever
        loopCount = 3000
        while (not bookPlayer.isPlaying()) and (loopCount > 0):
            xbmc.sleep(1)
            loopCount = loopCount - 1

        # Looks like the audiobook never started for some reason, do not go any further
        if loopCount == 0:
            return

        currentTime = 0
        currentFile = ''

        waitingForComplete = 0
        # Wait for the player to stop
        while waitingForComplete < 30:
            # There is a small gap when switching between different items in the same
            # playlist where it records it as not playing, so we need to give it a little
            # bit of time to start playing the next item in the playlist if there is one
            if bookPlayer.isPlaying():
                # Keep track of where the current track is up to
                currentTime = int(bookPlayer.getTime())
                currentFile = bookPlayer.getPlayingFile()
                waitingForComplete = 0
            else:
                waitingForComplete += 1
            xbmc.sleep(10)

        # Record the time that the player actually stopped
        log("BookPlayer: Played to time = %d, file = %s" % (currentTime, currentFile))

        # Get the chapter number that was playing
        chapterPosition = audioBookHandler.getChapterPosition(currentFile)
        log("BookPlayer: Chapter position is %d" % chapterPosition)

        if (currentTime > 0) or (chapterPosition > 1):
            bookComplete = False
            duration = audioBookHandler.getTotalDuration()
            log("BookPlayer: Total book duration is %d" % duration)
            if duration > 1:
                if currentTime > (duration - 60):
                    bookComplete = True

            audiobookDB = AudioBooksDB()
            audiobookDB.setPosition(audioBookHandler.getFile(), currentTime, chapterPosition, bookComplete)
            del audiobookDB
