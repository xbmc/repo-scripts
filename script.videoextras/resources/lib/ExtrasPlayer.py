# -*- coding: utf-8 -*-
import traceback
import xbmc
import xbmcaddon
import xbmcgui

# Import the common settings
from settings import log

ADDON = xbmcaddon.Addon(id='script.videoextras')


###################################
# Custom Player to play the extras
###################################
class ExtrasPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        self.isPlayAll = True
        self.currentlyPlaying = None
        # Extract the title of the parent video that owns the extras
        self.parentTitle = kwargs.pop('parentTitle', "")
        xbmc.Player.__init__(self, *args)

    # Play the given Extras File
    def playExtraItem(self, extrasItem):
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        listitem = self._getListItem(extrasItem)
        playlist.clear()
        playlist.add(extrasItem.getMediaFilename(), listitem)
        self.play(playlist)

    # Play a list of extras
    @staticmethod
    def playAll(extrasItems, parentTitle=""):
        log("ExtrasPlayer: playAll")
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()

        extrasPlayer = ExtrasPlayer(parentTitle=parentTitle)

        # store the last file in the list, we will use this later to work out
        # if there are still more to play
        lastFileInList = ""
        for exItem in extrasItems:
            # Get the list item, but not any resume information
            listitem = extrasPlayer._getListItem(exItem, True)
            playlist.add(exItem.getMediaFilename(), listitem)
            lastFileInList = exItem.getMediaFilename()

        extrasPlayer.play(playlist)

        # Now the list of videos is playing we need to keep track of
        # where they are and then save their current status
        currentTime = 0
        currentlyPlayingFile = ""
        currentExtrasItem = None
        while extrasPlayer.isPlayingVideo():
            try:
                # Check if the same file as last time has started playing
                if currentlyPlayingFile != extrasPlayer.getPlayingFile():
                    # If there was previously a playing file, need to save it's state
                    if (currentlyPlayingFile != "") and (currentExtrasItem is not None):
                        # Record the time that the player actually stopped
                        log("ExtrasPlayer: Played %s to time = %d" % (currentlyPlayingFile, currentTime))
                        if currentTime > 5:
                            currentExtrasItem.setResumePoint(currentTime)
                            # Now update the database with the fact this has now been watched
                            currentExtrasItem.saveState()
                        else:
                            log("ExtrasPlayer: Only played to time = %d (Not saving state)" % currentTime)

                    currentlyPlayingFile = ""
                    currentExtrasItem = None
                    currentTime = 0
                    # Last operation may have taken a bit of time as it might have written to
                    # the database, so just make sure we are still playing
                    if extrasPlayer.isPlayingVideo():
                        # Get the name of the currently playing file
                        currentlyPlayingFile = extrasPlayer.getPlayingFile()
                        for exItem in extrasItems:
                            if exItem.getMediaFilename() == currentlyPlayingFile:
                                currentExtrasItem = exItem
                                break

                # Keep track of where the current video is up to
                if extrasPlayer.isPlayingVideo():
                    currentTime = int(extrasPlayer.getTime())
            except:
                log("ExtrasPlayer: Failed to follow progress %s" % currentlyPlayingFile, xbmc.LOGERROR)
                log("ExtrasPlayer: %s" % traceback.format_exc(), xbmc.LOGERROR)

            xbmc.sleep(10)

            # If the user selected the "Play All" option, then we do not want to
            # stop between the two videos, so do an extra wait
            if not extrasPlayer.isPlayingVideo() and (len(extrasItems) > 1) and (currentlyPlayingFile != lastFileInList):
                xbmc.sleep(3000)

        # Need to save the final file state
        if (currentlyPlayingFile is not None) and (currentExtrasItem is not None):
            # Record the time that the player actually stopped
            log("ExtrasPlayer: Played final %s to time = %d" % (currentlyPlayingFile, currentTime))
            if currentTime > 5:
                currentExtrasItem.setResumePoint(currentTime)
                # Now update the database with the fact this has now been watched
                currentExtrasItem.saveState()
            else:
                log("ExtrasPlayer: Only played to time = %d (Not saving state)" % currentTime)

        del extrasPlayer

    # Calls the media player to play the selected item
    @staticmethod
    def performPlayAction(extraItem, parentTitle=""):
        log("ExtrasPlayer: Playing extra video = %s" % extraItem.getFilename())
        extrasPlayer = ExtrasPlayer(parentTitle=parentTitle)
        extrasPlayer.playExtraItem(extraItem)

        # Don't allow this to loop forever
        loopCount = 1000
        while (not extrasPlayer.isPlayingVideo()) and (loopCount > 0):
            xbmc.sleep(1)
            loopCount = loopCount - 1

        # Looks like the video never started for some reason, do not go any further
        if loopCount == 0:
            return

        # Get the total duration and round it down to the nearest second
        videoDuration = int(extrasPlayer.getTotalTime())
        log("ExtrasPlayer: TotalTime of video = %d" % videoDuration)
        extraItem.setTotalDuration(videoDuration)

        currentTime = 0
        # Wait for the player to stop
        while extrasPlayer.isPlayingVideo():
            # Keep track of where the current video is up to
            currentTime = int(extrasPlayer.getTime())
            xbmc.sleep(10)

        # Record the time that the player actually stopped
        log("ExtrasPlayer: Played to time = %d" % currentTime)
        extraItem.setResumePoint(currentTime)

        # Now update the database with the fact this has now been watched
        extraItem.saveState()
        del extrasPlayer

    # Create a list item from an extras item
    def _getListItem(self, extrasItem, ignoreResume=False):
        listitem = xbmcgui.ListItem()
        # Set the display title on the video play overlay
        listitem.setInfo('video', {'studio': ADDON.getLocalizedString(32001) + " - " + self.parentTitle})
        listitem.setInfo('video', {'Title': extrasItem.getDisplayName()})

        # If both the Icon and Thumbnail is set, the list screen will choose to show
        # the thumbnail
        if extrasItem.getIconImage() != "":
            listitem.setIconImage(extrasItem.getIconImage())
        # For the player OSD if there is no thumbnail, then show the VideoExtras icon
        if extrasItem.getThumbnailImage() != "":
            listitem.setThumbnailImage(extrasItem.getThumbnailImage())
        else:
            listitem.setThumbnailImage(ADDON.getAddonInfo('icon'))

        # Check if the plot is set, if so we want to set it on the player
        plotDetails = extrasItem.getPlot()
        if (plotDetails is not None) and (plotDetails != ""):
            listitem.setInfo('video', {'plot': plotDetails})

        # Record if the video should start playing part-way through
        if extrasItem.isResumable() and not ignoreResume:
            if extrasItem.getResumePoint() > 1:
                listitem.setProperty('StartOffset', str(extrasItem.getResumePoint()))
        return listitem
