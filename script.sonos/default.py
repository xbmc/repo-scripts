# -*- coding: utf-8 -*-
import sys
import os
import traceback
import xbmc
import xbmcaddon
import xbmcgui
import threading
import xbmcvfs
import time

__addon__ = xbmcaddon.Addon(id='script.sonos')
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__version__ = __addon__.getAddonInfo('version')
__icon__ = __addon__.getAddonInfo('icon')
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log

from sonos import Sonos

# Import the Event Listener for the Sonos system
from soco.events import event_listener

from lyrics import Lyrics

log('script version %s started' % __version__)

# The base type of the window depends on if we are just having the basic controls
# (In which case it is a dialog, so you can see the rest of the screen)
# If we want to use ArtistSlideshow then it needs to be a Window, as it does
# not work with dialogs (And we want to full the whole screen anyway)
BaseWindow = xbmcgui.WindowXMLDialog
if Settings.displayArtistInfo():
    BaseWindow = xbmcgui.WindowXML


#####################################################
# Main window for the Sonos controller
#####################################################
class SonosControllerWindow(BaseWindow):  # xbmcgui.WindowXMLDialog
    ALBUM_ART = 801
    ARTIST_LABEL = 802
    TITLE_LABEL = 803
    ALBUM_LABEL = 804
    NEXT_LABEL = 805

    TRACK_POSITION_LABEL = 810
    DURATION_LABEL = 812
    SLIDER_SEEK = 811

    # Button IDs
    BUTTON_PREVIOUS = 600
    BUTTON_PLAY = 601
    BUTTON_PAUSE = 602
    BUTTON_STOP = 603
    BUTTON_NEXT = 604

    BUTTON_NOT_MUTED = 620
    BUTTON_MUTED = 621
    SLIDER_VOLUME = 622

    BUTTON_REPEAT = 605
    BUTTON_REPEAT_ENABLED = 606

    BUTTON_RANDOM = 607
    BUTTON_RANDOM_ENABLED = 608

    BUTTON_CROSSFADE = 609
    BUTTON_CROSSFADE_ENABLED = 610

    def __init__(self, *args, **kwargs):
        self.closeRequested = False
        # Copy off the key-word arguments
        # The non keyword arguments will be the ones passed to the main WindowXML
        self.sonosDevice = kwargs.pop('sonosDevice')
        self.currentTrack = None
        self.nextTrack = None

        self.delayedRefresh = 0
        # After startup we can always process the action
        self.nextFilteredAction = 0

        # Record if the playlist is random and the loop state
        self.isRandom = False
        self.isLoop = False

    # Static method to create the Window Dialog class
    @staticmethod
    def createSonosControllerWindow(sonosDevice):
        return SonosControllerWindow("script-sonos-controller.xml", __cwd__, sonosDevice=sonosDevice)

    def isClose(self):
        return self.closeRequested

    # Handle the close action
    def onAction(self, action):
        # actioncodes from https://github.com/xbmc/xbmc/blob/master/xbmc/guilib/Key.h
        ACTION_PREVIOUS_MENU = 10
        ACTION_NAV_BACK = 92

        # For remote control
        ACTION_PAUSE = 12
        ACTION_STOP = 13
        ACTION_NEXT_ITEM = 14
        ACTION_PREV_ITEM = 15
        # The following 4 are active forward and back
        ACTION_FORWARD = 16
        ACTION_REWIND = 17
        ACTION_PLAYER_FORWARD = 77
        ACTION_PLAYER_REWIND = 78

        ACTION_PLAYER_PLAY = 79
        ACTION_VOLUME_UP = 88
        ACTION_VOLUME_DOWN = 89
        ACTION_MUTE = 91

        # Values Used in the custom keymap
        ACTION_FIRST_PAGE = 159  # Next Track
        ACTION_LAST_PAGE = 160  # Previous Track
        ACTION_PAGE_UP = 5  # Increase Volume
        ACTION_PAGE_DOWN = 6  # Decrease Volume
        ACTION_TOGGLE_WATCHED = 200  # Mute volume

        if (action == ACTION_PREVIOUS_MENU) or (action == ACTION_NAV_BACK):
            log("SonosControllerWindow: Close Action received: %s" % str(action.getId()))
            self.close()
        else:
            # Handle remote control commands
            if((action == ACTION_PLAYER_PLAY) or (action == ACTION_PAUSE)):
                # Get the initial state of the device
                playStatus = self.sonosDevice.get_current_transport_info()

                # Play/pause is a toggle, so pause if playing
                if playStatus is not None:
                    if playStatus['current_transport_state'] == 'PLAYING':
                        self.onClick(SonosControllerWindow.BUTTON_PAUSE)
                    else:
                        self.onClick(SonosControllerWindow.BUTTON_PLAY)
            elif (action == ACTION_STOP):
                self.onClick(SonosControllerWindow.BUTTON_STOP)
            elif (action == ACTION_NEXT_ITEM) or (action == ACTION_FIRST_PAGE):
                self.onClick(SonosControllerWindow.BUTTON_NEXT)
            elif (action == ACTION_PREV_ITEM) or (action == ACTION_LAST_PAGE):
                self.onClick(SonosControllerWindow.BUTTON_PREVIOUS)
            elif (action == ACTION_MUTE) or (action == ACTION_TOGGLE_WATCHED):
                # Check if currently muted
                if self.sonosDevice.mute is False:
                    self.onClick(SonosControllerWindow.BUTTON_NOT_MUTED)
                else:
                    self.onClick(SonosControllerWindow.BUTTON_MUTED)
            elif (action == ACTION_VOLUME_UP) or (action == ACTION_PAGE_UP):
                # Get the current slider position
                volumeSlider = self.getControl(SonosControllerWindow.SLIDER_VOLUME)
                currentSliderPosition = int(volumeSlider.getPercent())
                if currentSliderPosition < 100:
                    # Bump the volume by double the wait time (otherwise we can't skip forward accurately)
                    volumeSlider.setPercent(currentSliderPosition + Settings.getVolumeChangeIncrements())
                    self.onClick(SonosControllerWindow.SLIDER_VOLUME)
            elif (action == ACTION_VOLUME_DOWN) or (action == ACTION_PAGE_DOWN):
                # Get the current slider position
                volumeSlider = self.getControl(SonosControllerWindow.SLIDER_VOLUME)
                currentSliderPosition = int(volumeSlider.getPercent())
                if currentSliderPosition > 0:
                    # Bump the volume down by double the wait time (otherwise we can't skip forward accurately)
                    volumeSlider.setPercent(currentSliderPosition - Settings.getVolumeChangeIncrements())
                    self.onClick(SonosControllerWindow.SLIDER_VOLUME)
            elif((action == ACTION_FORWARD) or (action == ACTION_PLAYER_FORWARD)):
                # Get the current slider position
                seekSlider = self.getControl(SonosControllerWindow.SLIDER_SEEK)
                currentSliderPosition = int(seekSlider.getPercent())
                if currentSliderPosition < 99:
                    # Bump the slider by double the wait time (otherwise we can't skip forward accurately)
                    seekSlider.setPercent(currentSliderPosition + (int(Settings.getAvoidDuplicateCommands()) * 2))
                    self.onClick(SonosControllerWindow.SLIDER_SEEK)
            elif((action == ACTION_REWIND) or (action == ACTION_PLAYER_REWIND)):
                # Get the current slider position
                seekSlider = self.getControl(SonosControllerWindow.SLIDER_SEEK)
                currentSliderPosition = int(seekSlider.getPercent())
                if currentSliderPosition > 0:
                    # Bump the slider down by double the wait time (otherwise we can't skip forward accurately)
                    seekSlider.setPercent(currentSliderPosition - (int(Settings.getAvoidDuplicateCommands()) * 2))
                    self.onClick(SonosControllerWindow.SLIDER_SEEK)

    # Handle the close event - make sure we set the flag so we know it's been closed
    def close(self):
        self.closeRequested = True
        BaseWindow.close(self)

    # Updates the controller display
    def updateDisplay(self, eventDetails=None):
        # Get the current track information
        track = self.sonosDevice.get_current_track_info()
        # Now merge the track and event information
        track = self.sonosDevice.mergeTrackInfoAndEvent(track, eventDetails, self.currentTrack)

        # Only update if the track has changed
        if self.sonosDevice.hasTrackChanged(self.currentTrack, track):
            log("SonosControllerWindow: Track changed, updating screen")
            # Get the album art if it is set (Default to the Sonos icon)
            albumArtImage = __icon__
            if track['album_art'] != "":
                albumArtImage = track['album_art']

            # Need to populate the popup with the artist details
            albumArt = self.getControl(SonosControllerWindow.ALBUM_ART)
            albumArt.setImage(albumArtImage)

            artistLabel = self.getControl(SonosControllerWindow.ARTIST_LABEL)
            artistLabel.reset()
            artistLabel.addLabel(track['artist'])

            titleLabel = self.getControl(SonosControllerWindow.TITLE_LABEL)
            titleLabel.reset()
            titleLabel.addLabel(track['title'])

            albumLabel = self.getControl(SonosControllerWindow.ALBUM_LABEL)
            albumLabel.reset()
            albumLabel.addLabel(track['album'])

            # Display the track duration
            durationLabel = self.getControl(SonosControllerWindow.DURATION_LABEL)
            durationLabel.setLabel(self._stripHoursFromTime(track['duration']))

            # If the duration is 00:00:00 then this normally means that something like radio
            # is steaming so we shouldn't show any timing details
            if track['duration'] == '0:00:00':
                durationLabel.setVisible(False)
            else:
                durationLabel.setVisible(True)

        # Store the duration in seconds - it is used a few times later on
        track['duration_seconds'] = self._getSecondsInTimeString(track['duration'])

        # Set the current position of where the track is playing in the seconds format
        # this makes it easier to use later, instead of always parsing the string format
        track['position_seconds'] = self._getSecondsInTimeString(track['position'])

        # Get the control that currently has focus
        focusControl = -1
        try:
            focusControl = self.getFocusId()
        except:
            pass

        # Get the playing mode, so see if random or repeat has changes
        self.isRandom, self.isLoop = self.sonosDevice.getPlayMode()

        randomButton = self.getControl(SonosControllerWindow.BUTTON_RANDOM)
        # We can not calculate the next track if it is random
        if self.isRandom:
            log("SonosControllerWindow: Random enabled - Disabling button")
            randomButton.setVisible(False)
            # Set the correct highlighted button
            if focusControl == SonosControllerWindow.BUTTON_RANDOM:
                self.setFocusId(SonosControllerWindow.BUTTON_RANDOM_ENABLED)
        else:
            log("SonosControllerWindow: Random disabled - Enabling Button")
            randomButton.setVisible(True)
            # Set the correct highlighted button
            if focusControl == SonosControllerWindow.BUTTON_RANDOM_ENABLED:
                self.setFocusId(SonosControllerWindow.BUTTON_RANDOM)

        # Set the next track info, needs to be done after we know if
        # random play is enabled
        self._updateNextTrackInfo(track)

        # Set the repeat button status
        repeatButton = self.getControl(SonosControllerWindow.BUTTON_REPEAT)
        if self.isLoop:
            repeatButton.setVisible(False)
            # Set the correct highlighted button
            if focusControl == SonosControllerWindow.BUTTON_REPEAT:
                self.setFocusId(SonosControllerWindow.BUTTON_REPEAT_ENABLED)
        else:
            repeatButton.setVisible(True)
            # Set the correct highlighted button
            if focusControl == SonosControllerWindow.BUTTON_REPEAT_ENABLED:
                self.setFocusId(SonosControllerWindow.BUTTON_REPEAT)

        # Get the current Cross-Fade setting
        crossFade = self.sonosDevice.cross_fade
        crossFadeButton = self.getControl(SonosControllerWindow.BUTTON_CROSSFADE)
        if crossFade:
            crossFadeButton.setVisible(False)
            # Set the correct highlighted button
            if focusControl == SonosControllerWindow.BUTTON_CROSSFADE:
                self.setFocusId(SonosControllerWindow.BUTTON_CROSSFADE_ENABLED)
        else:
            crossFadeButton.setVisible(True)
            # Set the correct highlighted button
            if focusControl == SonosControllerWindow.BUTTON_CROSSFADE_ENABLED:
                self.setFocusId(SonosControllerWindow.BUTTON_CROSSFADE)

        self.currentTrack = track

        # Display the track position
        trackPositionLabel = self.getControl(SonosControllerWindow.TRACK_POSITION_LABEL)
        trackPositionLabel.setLabel(self._stripHoursFromTime(track['position']))

        # Get the initial state of the device
        playStatus = self.sonosDevice.get_current_transport_info()

        # Set the play/pause button to the correct value
        playButton = self.getControl(SonosControllerWindow.BUTTON_PLAY)
        if (playStatus is not None) and (playStatus['current_transport_state'] == 'PLAYING'):
            playButton.setVisible(False)
            # Set the correct highlighted button
            if focusControl == SonosControllerWindow.BUTTON_PLAY:
                self.setFocusId(SonosControllerWindow.BUTTON_PAUSE)
        else:
            playButton.setVisible(True)
            # Set the correct highlighted button
            if focusControl == SonosControllerWindow.BUTTON_PAUSE:
                self.setFocusId(SonosControllerWindow.BUTTON_PLAY)

        # Check to see what the current state of the mute button is
        muteButton = self.getControl(SonosControllerWindow.BUTTON_NOT_MUTED)
        if self.sonosDevice.mute is False:
            muteButton.setVisible(True)
            # Set the correct highlighted button
            if focusControl == SonosControllerWindow.BUTTON_MUTED:
                self.setFocusId(SonosControllerWindow.BUTTON_NOT_MUTED)
        else:
            muteButton.setVisible(False)
            # Set the correct highlighted button
            if focusControl == SonosControllerWindow.BUTTON_NOT_MUTED:
                self.setFocusId(SonosControllerWindow.BUTTON_MUTED)

        # The following controls need a delayed refresh, this is because they
        # are controls like sliders, so we do not want to update them until
        # the slider operation is complete
        if self.delayedRefresh < 1:
            # Get the current volume and set the slider
            # Will return a value between 0 and 100
            currentVolume = self.sonosDevice.volume
            # Get the slider control
            volumeSlider = self.getControl(SonosControllerWindow.SLIDER_VOLUME)
            # Don't move slider is already in correct position
            currentSliderPosition = int(volumeSlider.getPercent())
            if currentSliderPosition != currentVolume:
                volumeSlider.setPercent(currentVolume)

            # Set the seek slider
            self._setSeekSlider(track['position_seconds'], track['duration_seconds'])
        else:
            self.delayedRefresh = self.delayedRefresh - 1

    # Do the initial setup of the dialog
    def onInit(self):
        self.updateDisplay()

    # work out if a given action is OK to run
    def _canProcessFilteredAction(self):
        currentTime = time.time()

        # Make sure we are not in a blackout zone
        if currentTime > self.nextFilteredAction:
            # Reset the time, and make sure we do not process any others
            # for another 2 seconds (This will prevent a large build up
            # as we hope that the sonos system can process this within
            # 2 seconds, otherwise there will be a delay)
            self.nextFilteredAction = currentTime + Settings.getAvoidDuplicateCommands()
            return True
        elif self.nextFilteredAction > 0:
            log("SonosControllerWindow: Ignoring commands until %s" % time.strftime("%H:%M:%S", time.gmtime(self.nextFilteredAction)))

        return False

    # Handle the operations where the user clicks on a button
    def onClick(self, controlID):
        # Play button has been clicked
        if controlID == SonosControllerWindow.BUTTON_PLAY:
            log("SonosControllerWindow: Play Requested")
            # Send the play message to Sonos
            self.sonosDevice.play()

        elif controlID == SonosControllerWindow.BUTTON_PAUSE:
            log("SonosControllerWindow: Pause Requested")
            # Send the pause message to Sonos
            self.sonosDevice.pause()

        elif controlID == SonosControllerWindow.BUTTON_NEXT:
            log("SonosControllerWindow: Next Track Requested")
            self.sonosDevice.next()

        elif controlID == SonosControllerWindow.BUTTON_PREVIOUS:
            log("SonosControllerWindow: Previous Track Requested")
            self.sonosDevice.previous()

        elif controlID == SonosControllerWindow.BUTTON_STOP:
            log("SonosControllerWindow: Stop Requested")
            self.sonosDevice.stop()

        elif controlID == SonosControllerWindow.BUTTON_REPEAT:
            log("SonosControllerWindow: Repeat On Requested")
            self.isLoop = True
            self.sonosDevice.setPlayMode(self.isRandom, self.isLoop)

        elif controlID == SonosControllerWindow.BUTTON_REPEAT_ENABLED:
            log("SonosControllerWindow: Repeat Off Requested")
            self.isLoop = False
            self.sonosDevice.setPlayMode(self.isRandom, self.isLoop)

        elif controlID == SonosControllerWindow.BUTTON_RANDOM:
            log("SonosControllerWindow: Randon On Requested")
            self.isRandom = True
            self.sonosDevice.setPlayMode(self.isRandom, self.isLoop)

        elif controlID == SonosControllerWindow.BUTTON_RANDOM_ENABLED:
            log("SonosControllerWindow: Randon On Requested")
            self.isRandom = False
            self.sonosDevice.setPlayMode(self.isRandom, self.isLoop)

        elif controlID == SonosControllerWindow.BUTTON_CROSSFADE:
            log("SonosControllerWindow: Crossfade On Requested")
            self.sonosDevice.cross_fade = True

        elif controlID == SonosControllerWindow.BUTTON_CROSSFADE_ENABLED:
            log("SonosControllerWindow: Crossfade Off Requested")
            self.sonosDevice.cross_fade = False

        elif controlID == SonosControllerWindow.BUTTON_NOT_MUTED:
            log("SonosControllerWindow: Mute Requested")
            self.sonosDevice.mute = True

        elif controlID == SonosControllerWindow.BUTTON_MUTED:
            log("SonosControllerWindow: Mute Requested")
            self.sonosDevice.mute = False

        elif controlID == SonosControllerWindow.SLIDER_VOLUME:
            # Only process the operation if we are allowed
            # this is to prevent a buildup of actions
            if self._canProcessFilteredAction():
                # Get the position of the slider
                volumeSlider = self.getControl(SonosControllerWindow.SLIDER_VOLUME)
                currentSliderPosition = int(volumeSlider.getPercent())

                log("SonosControllerWindow: Volume Request to value: %d" % currentSliderPosition)

                # Before we send the volume change request we want to delay any refresh
                # on the gui so we have time to perform the slide operation without
                # the slider being reset
                self._setDelayedRefresh()

                # Now set the volume
                self.sonosDevice.volume = currentSliderPosition

        elif controlID == SonosControllerWindow.SLIDER_SEEK:
            # Only process the operation if we are allowed
            # this is to prevent a buildup of actions
            if self._canProcessFilteredAction():
                # Get the position of the slider
                seekSlider = self.getControl(SonosControllerWindow.SLIDER_SEEK)
                currentSliderPosition = int(seekSlider.getPercent())

                log("SonosControllerWindow: Seek Request to value: %d" % currentSliderPosition)

                # Before we send the seek change request we want to delay any refresh
                # on the gui so we have time to perform the slide operation without
                # the slider being reset
                self._setDelayedRefresh()

                # Now set the seek location
                self._setSeekPosition(currentSliderPosition)

#        else:
#            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), "Control clicked is " + str(controlID))

        # Refresh the screen to show the current state
        self.updateDisplay()

    # Set a delay time so that the screen does not automatically update
    # and leaves time for a given operation
    def _setDelayedRefresh(self):
        # Convert the refresh interval into seconds
        refreshInterval = Settings.getRefreshInterval() / 1000
        if refreshInterval == 0:
            # Make sure we do not divide by zero
            refreshInterval = 1
        self.delayedRefresh = int(4 / float(refreshInterval))
        if self.delayedRefresh == 0:
            self.delayedRefresh = 1

    # Takes a time string (00:00:00) and removes the hour section if it is 0
    def _stripHoursFromTime(self, fullTimeString):
        # Some services do not support duration
        if fullTimeString == 'NOT_IMPLEMENTED':
            return ""

        if (fullTimeString is None) or (fullTimeString == ""):
            return "00:00"
        if fullTimeString.count(':') == 2:
            # Check if the hours section should be stripped
            hours = 0
            try:
                hours = int(fullTimeString.split(':', 1)[0])
            except:
                # Hours section is not numbers
                log("SonosControllerWindow: Exception Details: %s" % traceback.format_exc())
                hours = 0

            # Only strip the hours if there are no hours
            if hours < 1:
                return fullTimeString.split(':', 1)[-1]
        return fullTimeString

    # Set the seek slider to the current position of the track
    def _setSeekSlider(self, currentPositionSeconds, trackDurationSeconds):
        # work out the percentage we are through the track
        currentPercentage = 0
        if trackDurationSeconds > 0:
            currentPercentage = int((float(currentPositionSeconds) / float(trackDurationSeconds)) * 100)

        log("SonosControllerWindow: Setting seek slider to %d" % currentPercentage)

        # Get the slider control
        seekSlider = self.getControl(SonosControllerWindow.SLIDER_SEEK)
        seekSlider.setPercent(currentPercentage)

    # Converts a time string 0:00:00 to the total number of seconds
    def _getSecondsInTimeString(self, fullTimeString):
        # Some services do not support duration
        if fullTimeString == 'NOT_IMPLEMENTED':
            return -1

        # Start by splitting the time into sections
        hours = 0
        minutes = 0
        seconds = 0

        try:
            hours = int(fullTimeString.split(':', 1)[0])
            minutes = int(fullTimeString.split(':')[1])
            seconds = int(fullTimeString.split(':')[2])
        except:
            # time sections are not numbers
            log("SonosControllerWindow: Exception Details: %s" % traceback.format_exc())
            hours = 0
            minutes = 0
            seconds = 0

        totalInSeconds = (((hours * 60) + minutes) * 60) + seconds
        log("SonosControllerWindow: Time %s, splits into hours=%d, minutes=%d, seconds=%d, total=%d" % (fullTimeString, hours, minutes, seconds, totalInSeconds))

        # Return the total time in seconds
        return totalInSeconds

    # Sets the current seek time, sending it to the sonos speaker
    def _setSeekPosition(self, percentage):
        trackDurationSeconds = self.currentTrack['duration_seconds']

        if trackDurationSeconds > 0:
            # Get the current number of seconds into the track
            newPositionSeconds = int((float(percentage) * float(trackDurationSeconds)) / 100)

            # Convert the seconds into a timestamp
            newPosition = "0:00:00"

            # Convert the duration into a viewable format
            if newPositionSeconds > 0:
                seconds = newPositionSeconds % 60
                minutes = 0
                hours = 0

                if newPositionSeconds > 60:
                    minutes = ((newPositionSeconds - seconds) % 3600) / 60

                if newPositionSeconds > 3600:
                    hours = (newPositionSeconds - (minutes * 60) - seconds) / 3600

                # Build the string up
                newPosition = "%d:%02d:%02d" % (hours, minutes, seconds)

            # Now send the seek message to the sonos speaker
            self.sonosDevice.seek(newPosition)

    # Populates the details of the next track that will be played
    def _updateNextTrackInfo(self, track=None):
        nextTrackLabel = self.getControl(SonosControllerWindow.NEXT_LABEL)
        nextTrackCreator = None
        nextTrackTitle = None

        # Make sure there is a track present, also want to make sure that we
        # are not streaming something - as we do not want to display a next
        # track when we are streaming, this is normally the case if the
        # track duration is zero
        if (track is not None) and (track['title'] != '') and (track['duration'] != '0:00:00'):
            # The code below gives the next track in the playlist
            # Check if there is a next track
            playlistPos = track['playlist_position']
            log("SonosControllerWindow: Current track playlist position is %s" % str(playlistPos))
            if track['playlist_position'] != "" and int(track['playlist_position']) > -1:
                # Also get the "Next Track" Information
                # 0 would be the current track
                nextTrackList = self.sonosDevice.get_queue(int(track['playlist_position']), 1)

                if (nextTrackList is not None) and (len(nextTrackList) > 0):
                    nextTrackItem = nextTrackList[0]
                    nextTrackCreator = nextTrackItem.creator
                    nextTrackTitle = nextTrackItem.title
            # If we have random play enabled, then we can not just read the next
            # track in the playlist, for this case we will need to see if there
            # is an event that tells us what the next track is
            elif track['lastEventDetails'] is not None:
                # Get the track and creator if they both exist, if only one
                # exists, then it's most probably a radio station and Next track
                # title just contains a URI
                if (track['next_artist'] is not None) and (track['next_title'] is not None):
                    nextTrackCreator = track['next_artist']
                    nextTrackTitle = track['next_title']

        # Check to see if both the title and creator of the next track is set
        if (nextTrackCreator is not None) and (nextTrackTitle is not None):
            nextTrackText = "[COLOR=FF0084ff]%s:[/COLOR] %s - %s" % (__addon__.getLocalizedString(32062), nextTrackTitle, nextTrackCreator)
            # If the next track has changed, then set the new value
            # Otherwise we just leave it as it was
            if self.nextTrack != nextTrackText:
                self.nextTrack = nextTrackText
                nextTrackLabel.reset()
                nextTrackLabel.addLabel(nextTrackText)
        else:
            # If there is no next track, then clear the screen
            log("SonosControllerWindow: Clearing next track label")
            nextTrackLabel.reset()
            nextTrackLabel.addLabel("")


#####################################################
# Main window for the Sonos Artist Slide show
#####################################################
class SonosArtistSlideshow(SonosControllerWindow):
    LYRICS = 1345

    SONOS_ICON_ID = 800

    def __init__(self, *args, **kwargs):
        # Store the ID of this Window
        self.windowId = -1
        self.lyricListLinesCount = 0
        SonosControllerWindow.__init__(self, *args, **kwargs)

    # Static method to create the Window Dialog class
    @staticmethod
    def createSonosArtistSlideshow(sonosDevice):
        # Check the ArtistSlideshow setting to see if the biography field is set
        try:
            artistslideshow = xbmcaddon.Addon(id='script.artistslideshow')
            if artistslideshow.getSetting('artistinfo') != 'true':
                # Biography is not set, prompt the use to see if we should set it
                if xbmcgui.Dialog().yesno(__addon__.getLocalizedString(32001),
                                          __addon__.getLocalizedString(32060),
                                          "  \"%s\"" % artistslideshow.getLocalizedString(32005),
                                          __addon__.getLocalizedString(32061)):
                    artistslideshow.setSetting('artistinfo', 'true')
            if artistslideshow.getSetting('transparent') != 'true':
                # Transparent image is not set, prompt the use to see if we should set it
                if xbmcgui.Dialog().yesno(__addon__.getLocalizedString(32001),
                                          __addon__.getLocalizedString(32060),
                                          "  \"%s\"" % artistslideshow.getLocalizedString(32107),
                                          __addon__.getLocalizedString(32061)):
                    artistslideshow.setSetting('transparent', 'true')
        except:
            log("SonosArtistSlideshow: Exception Details: %s" % traceback.format_exc(), xbmc.LOGERROR)

        return SonosArtistSlideshow(Settings.getArtistInfoLayout(), __cwd__, sonosDevice=sonosDevice)

    # Launch ArtistSlideshow
    def runArtistSlideshow(self):
        log("SonosArtistSlideshow: runArtistSlideshow")
        # startup artistslideshow
        xbmcgui.Window(self.windowId).setProperty("ArtistSlideshow.ExternalCall", "True")
        # assumes addon is using suggested infolabel name of CURRENTARTIST and CURRENTTITLE
        artistslideshow = "RunScript(script.artistslideshow,windowid=%s&artistfield=%s&titlefield=%s&albumfield=%s&mbidfield=%s)" % (xbmcgui.getCurrentWindowId(), "CURRENTARTIST", "CURRENTTITLE", "CURRENTALBUM", "CURRENTMBID")
        xbmc.executebuiltin(artistslideshow)

    # Display the window
    def show(self):
        log("SonosArtistSlideshow: About to show window")
        # First show the window
        SonosControllerWindow.show(self)

        # Work out how many lines there are on the screen to show lyrics
        if Settings.isLyricsInfoLayout():
            lyricControl = self.getControl(SonosArtistSlideshow.LYRICS)
            if lyricControl is not None:
                listitem = xbmcgui.ListItem()
                while xbmc.getInfoLabel('Container(%s).NumPages' % SonosArtistSlideshow.LYRICS) != '2':
                    lyricControl.addItem(listitem)
                    xbmc.sleep(10)
                self.lyricListLinesCount = lyricControl.size() - 1
                lyricControl.reset()

        self.windowId = xbmcgui.getCurrentWindowId()

        log("SonosArtistSlideshow: After show window %s" % self.windowId)

        # Set the sonos icon
        if not Settings.hideSonosLogo():
            xbmcgui.Window(self.windowId).setProperty('SonosAddonIcon', __icon__)

        # Set option to make the artist slideshow full screen
        if Settings.fullScreenArtistSlideshow():
            xbmcgui.Window(self.windowId).setProperty('SonosAddonSlideshowFullscreen', "true")

        # Now make sure that Artist Slideshow is running
        self.athread = threading.Thread(target=self.runArtistSlideshow)
        self.athread.setDaemon(True)
        self.athread.start()
        log("SonosArtistSlideshow: ArtistSlideShow thread started")

    def close(self):
        log("SonosArtistSlideshow: Closing windows - stop ArtistSlideShow")
        xbmc.executebuiltin("ActivateWindow(busydialog)")

        # Tell ArtistSlideshow to exit
        xbmcgui.Window(self.windowId).clearProperty("ArtistSlideshow.ExternalCall")
        # Wait until ArtistSlideshow exits
        # Do not loop forever
        loops = 40
        while (not xbmcgui.Window(self.windowId).getProperty("ArtistSlideshow.CleanupComplete") == "True") and (loops > 0):
            xbmc.sleep(100)
            loops = loops - 1

        if loops > -1:
            log("SonosArtistSlideshow: ArtistSlideShow Stopped")
        else:
            log("SonosArtistSlideshow: ArtistSlideShow did not stop")

        # Make sure the thread is dead at this point
        try:
            self.athread.join(3)
        except:
            log("Thread join error: %s" % traceback.format_exc(), xbmc.LOGERROR)

        # Now close the window (needs to be last as ArtistSlideshow is reading from it)
        SonosControllerWindow.close(self)
        xbmc.executebuiltin("Dialog.Close(busydialog)")

    def updateDisplay(self, eventDetails=None):
        SonosControllerWindow.updateDisplay(self, eventDetails)

        # Now we have updated the track currently playing read the details out and
        # set the windows properties for ArtistSlideshow
        # Only update if the track has changed
        if self.currentTrack not in [None, '']:
            # Check if we want to show lyrics for the track, although not part of the
            # artist slideshow feature (it is part of script.cu.lrclyrics) we treat
            # this in a similar manner, first set the values
            lyrics = None
            if Settings.isLyricsInfoLayout():
                lyrics = Lyrics(self.currentTrack, self.getControl(SonosArtistSlideshow.LYRICS), self.lyricListLinesCount)
                lyrics.setLyricRequest()

            # Artist Slideshow will set these properties for us
            xbmcgui.Window(self.windowId).setProperty('CURRENTARTIST', self.currentTrack['artist'])
            xbmcgui.Window(self.windowId).setProperty('CURRENTTITLE', self.currentTrack['title'])
            xbmcgui.Window(self.windowId).setProperty('CURRENTALBUM', self.currentTrack['album'])

            # Check if lyrics are enabled, and set the test if they are
            if lyrics is not None:
                self.currentTrack = lyrics.populateLyrics()
                lyrics.refresh()
                del lyrics

    def isClose(self):
        # Check if the base class has detected a need to close
        needToClose = SonosControllerWindow.isClose(self)

        # There are cases where the user could have changed the screen being
        # displayed, for example, if they have the following in their keymap:
        #   <keymap>
        #     <global>
        #       <keyboard>
        #         <f5>ActivateWindow(0)</f5>
        #       </keyboard>
        #     </global>
        #   </keymap>
        # This could cause a change in window, such as loading the home screen
        # however we do not get a call to close - as the Sonos window will be
        # still running in the back-ground - just not showing on the screen
        # If the user then exits, the keymap file will be left, so we will
        # automatically close the window in this case
        # Note: This is not an issue with the normal controller - as it is a
        # dialog window, so will always remain in view
        if (not needToClose) and (self.windowId != -1):
            # Get the current window
            showingWindowId = xbmcgui.getCurrentWindowId()
            # Check if the window is no longer showing
            if showingWindowId != self.windowId:
                log("SonosArtistSlideshow: Detected change in window, sonos window = %d, new window = %d" % (self.windowId, showingWindowId))
                return True

        return needToClose


# Load the Sonos keymap to make sure that volume/skip track keys do not get
# passed to Kodi to handle. This is needed because Kodi addons can not swallow
# events and so Kodi will perform the same operation
# Each run we copy our keymap over, force Kodi to relaoad the keymaps, then at the end
# we do the reverse - delete the custom one and reload the original setup
class KeyMaps():
    def __init__(self):
        self.KEYMAP_PATH = xbmc.translatePath(os.path.join(__resource__, "keymaps"))
        self.KEYMAPSOURCEFILE = os.path.join(self.KEYMAP_PATH, "sonos_keymap.xml")
        self.KEYMAPDESTFILE = os.path.join(xbmc.translatePath('special://userdata/keymaps'), "sonos_keymap.xml")
        self.keymapCopied = False

    # Copies the Sonos keymap to the correct location and loads it
    def enable(self):
        try:
            xbmcvfs.copy(self.KEYMAPSOURCEFILE, self.KEYMAPDESTFILE)
            self.keymapCopied = True
            xbmc.executebuiltin('Action(reloadkeymaps)')
            log("KeyMaps: Installed custom keymap")
        except:
            log("KeyMaps: Failed to copy & load custom keymap: %s" % traceback.format_exc(), xbmc.LOGERROR)

    # Removes the Sonos keymap
    def cleanup(self):
        if self.keymapCopied is True:
            try:
                xbmcvfs.delete(self.KEYMAPDESTFILE)
                log("KeyMaps: Removed custom keymap")
            except:
                log("KeyMaps: Failed to remove & load custom keymap: %s" % traceback.format_exc(), xbmc.LOGERROR)

            # Force a re-load
            xbmc.executebuiltin('Action(reloadkeymaps)')


if __name__ == '__main__':

    sonosDevice = Sonos.createSonosDevice()

    # Make sure a Sonos speaker was found
    if sonosDevice is not None:
        # Setup the keymap for the controller
        keyMapCtrl = KeyMaps()
        keyMapCtrl.enable()

        try:
            if Settings.displayArtistInfo():
                sonosCtrl = SonosArtistSlideshow.createSonosArtistSlideshow(sonosDevice)
            else:
                sonosCtrl = SonosControllerWindow.createSonosControllerWindow(sonosDevice)

            # Record the fact that the Sonos controller window is displayed
            xbmcgui.Window(10000).setProperty("SonosControllerShowing", "true")

            # Start with the subscription service unset
            sub = None

            try:
                # Display the window
                sonosCtrl.show()

                # Subscribe to receive notifications of changes
                sub = sonosDevice.avTransport.subscribe()

                # Make sure that we stop the screensaver coming in, the minimum value
                # for the screensaver is 1 minute - so set at 40 seconds to keep active
                stopScreensaver = 40000

                while (not sonosCtrl.isClose()) and (not xbmc.abortRequested):
                    # Now get the details of an event if there is one there
                    lastChangeDetails = sonosDevice.getLastEventDetails(sub)

                    # Update the displayed information
                    sonosCtrl.updateDisplay(eventDetails=lastChangeDetails)

                    # Wait a second or so before updating
                    xbmc.sleep(Settings.getRefreshInterval())

                    stopScreensaver = stopScreensaver - Settings.getRefreshInterval()
                    if stopScreensaver < 0:
                        # A bit of a hack, but we need Kodi to think a user is "doing things" so
                        # that it does not start the screensaver, so we just send the message
                        # to open the Context menu - which in our case will do nothing
                        # but it does make Kodi think the user has done something
                        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.ContextMenu", "id": 1}')
                        stopScreensaver = 40000

            except:
                # Failed to connect to the Sonos Speaker
                log("Sonos: Exception Details: %s" % traceback.format_exc(), xbmc.LOGERROR)
                xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), (__addon__.getLocalizedString(32066) % Settings.getIPAddress()))

            # Need to check to see if we can stop any subscriptsions
            if sub is not None:
                try:
                    sub.unsubscribe()
                except:
                    log("Sonos: Failed to unsubscribe: %s" % traceback.format_exc(), xbmc.LOGERROR)
                try:
                    # Make sure the thread is stopped even if unsubscribe failed
                    event_listener.stop()
                except:
                    log("Sonos: Failed to stop event listener: %s" % traceback.format_exc(), xbmc.LOGERROR)
                del sub

            sonosCtrl.close()
            # Record the fact that the Sonos controller is no longer displayed
            xbmcgui.Window(10000).clearProperty("SonosControllerShowing")
            del sonosCtrl
        except:
            log("Sonos: Exception Details: %s" % traceback.format_exc(), xbmc.LOGERROR)

        # Make sure we always tidy up the keymap
        keyMapCtrl.cleanup()
        del keyMapCtrl
        del sonosDevice
    else:
        xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), __addon__.getLocalizedString(32067))
