# -*- coding: utf-8 -*-
import sys
import xbmc
import xbmcaddon
import os
import xbmcgui

__addon__     = xbmcaddon.Addon(id='script.videoextras')
__addonid__   = __addon__.getAddonInfo('id')
__cwd__       = __addon__.getAddonInfo('path').decode("utf-8")
__resource__  = xbmc.translatePath( os.path.join( __cwd__, 'resources' ).encode("utf-8") ).decode("utf-8")
__lib__  = xbmc.translatePath( os.path.join( __resource__, 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join

# Load the core Video Extras classes
from core import ExtrasItem
from core import SourceDetails


###################################
# Custom Player to play the extras
###################################
class ExtrasPlayer(xbmc.Player):
    def __init__(self, *args):
        self.completed = False
        xbmc.Player.__init__(self, *args)

    # Play the given Extras File
    def play(self, extrasItem):
        play = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        listitem = self._getListItem(extrasItem)
        play.clear()
        play.add(extrasItem.getMediaFilename(), listitem)
        xbmc.Player.play(self, play)

    # Play a list of extras
    def playAll(self, extrasItems):
        play = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        play.clear()

        for exItem in extrasItems:
            listitem = self._getListItem(exItem)
            play.add(exItem.getMediaFilename(), listitem)

        xbmc.Player.play(self, play)

    # Calls the media player to play the selected item
    @staticmethod
    def performPlayAction(extraItem):
        log("ExtrasPlayer: Playing extra video = %s" % extraItem.getFilename())
        extrasPlayer = ExtrasPlayer()
        extrasPlayer.play( extraItem )
        
        while not extrasPlayer.isPlayingVideo():
            xbmc.sleep(1)
        
        # Get the total duration and round it down to the nearest second
        videoDuration = int(extrasPlayer.getTotalTime())
        log("ExtrasPlayer: TotalTime of video = %d" % videoDuration)
        extraItem.setTotalDuration(videoDuration)

        currentTime = 0
        # Wait for the player to stop
        while extrasPlayer.isPlayingVideo():
            # Keep track of where the current video is up to
            currentTime = int(extrasPlayer.getTime())
            xbmc.sleep(100)

        # Record the time that the player actually stopped
        log("ExtrasPlayer: Played to time = %d" % currentTime)
        extraItem.setResumePoint(currentTime)
        
        # Now update the database with the fact this has now been watched
        extraItem.saveState()


    # Create a list item from an extras item
    def _getListItem(self, extrasItem):
        listitem = xbmcgui.ListItem()
        # Set the display title on the video play overlay
        listitem.setInfo('video', {'studio': __addon__.getLocalizedString(32001) + " - " + SourceDetails.getTitle()})
        listitem.setInfo('video', {'Title': extrasItem.getDisplayName()})
        
        # If both the Icon and Thumbnail is set, the list screen will choose to show
        # the thumbnail
        if extrasItem.getIconImage() != "":
            listitem.setIconImage(extrasItem.getIconImage())
        if extrasItem.getThumbnailImage() != "":
            listitem.setThumbnailImage(extrasItem.getThumbnailImage())
        
        # Record if the video should start playing part-way through
        if extrasItem.isResumable():
            if extrasItem.getResumePoint() > 1:
                listitem.setProperty('StartOffset', str(extrasItem.getResumePoint()))
        return listitem
