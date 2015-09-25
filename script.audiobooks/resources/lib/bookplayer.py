# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import xbmcgui

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
    def playAudioBook(audioBookHandler, startTime=-1):
        log("BookPlayer: Playing audio book = %s" % audioBookHandler.getFile())

        bookPlayer = BookPlayer()

        # Create a list item from the book
        listitem = bookPlayer.getListItem(audioBookHandler, startTime)

        # Wrap the audiobook up in a playlist
        playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        playlist.clear()
        playlist.add(audioBookHandler.getFile(), listitem)
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
        # Wait for the player to stop
        while bookPlayer.isPlaying():
            # Keep track of where the current track is up to
            currentTime = int(bookPlayer.getTime())
            xbmc.sleep(10)

        # Record the time that the player actually stopped
        log("BookPlayer: Played to time = %d" % currentTime)

        if currentTime > 0:
            bookComplete = False
            duration = audioBookHandler.getTotalDuration()
            log("BookPlayer: Total book duration is %d" % duration)
            if duration > 1:
                if currentTime > (audioBookHandler.getTotalDuration() - 60):
                    bookComplete = True

            audiobookDB = AudioBooksDB()
            audiobookDB.setPosition(audioBookHandler.getFile(), currentTime, bookComplete)
            del audiobookDB

    # Create a list item from an audiobook details
    def getListItem(self, audioBookHandler, startTime=-1):
        listitem = xbmcgui.ListItem()
        # Set the display title on the music player
        # Have to set this as video otherwise it will not start the audiobook at the correct Offset place
        listitem.setInfo('video', {'Title': audioBookHandler.getTitle()})

        # If both the Icon and Thumbnail is set, the list screen will choose to show
        # the thumbnail
        coverImage = audioBookHandler.getCoverImage()
        if coverImage in [None, ""]:
            coverImage = __addon__.getAddonInfo('icon')

        listitem.setIconImage(coverImage)
        listitem.setThumbnailImage(coverImage)

        # Record if the video should start playing part-way through
        startPoint = startTime
        if startTime < 0:
            startPoint = audioBookHandler.getPosition()
        if startPoint > 0:
            listitem.setProperty('StartOffset', str(startPoint))

        return listitem
