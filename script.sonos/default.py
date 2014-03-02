# -*- coding: utf-8 -*-
import sys
import os
import traceback
import xbmc
import xbmcaddon
import xbmcgui

__addon__     = xbmcaddon.Addon(id='script.sonos')
__addonid__   = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__cwd__       = __addon__.getAddonInfo('path').decode("utf-8")
__version__   = __addon__.getAddonInfo('version')
__icon__      = __addon__.getAddonInfo('icon')
__resource__  = xbmc.translatePath( os.path.join( __cwd__, 'resources' ).encode("utf-8") ).decode("utf-8")
__lib__  = xbmc.translatePath( os.path.join( __resource__, 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)


# Import the common settings
from settings import Settings
from settings import log

# Import the Mock Sonos class for testing where there is no live Sonos system
#from mocksonos import TestMockSonos

log('script version %s started' % __version__)


#####################################################
# Main window for the Sonos controller
#####################################################
class SonosControllerWindow(xbmcgui.WindowXMLDialog):
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
    

    def __init__( self, *args, **kwargs ):
        self.closeRequested = False
        # Copy off the key-word arguments
        # The non keyword arguments will be the ones passed to the main WindowXML
        self.sonosDevice = kwargs.pop('sonosDevice')
        self.currentTrack = None
        
        self.delayedRefresh = 0

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
        ACTION_NAV_BACK      = 92
        
        # For remote control
        ACTION_PAUSE          = 12
        ACTION_STOP           = 13
        ACTION_NEXT_ITEM      = 14
        ACTION_PREV_ITEM      = 15
        # The following 4 are active forward and back
        ACTION_FORWARD        = 16
        ACTION_REWIND         = 17
        ACTION_PLAYER_FORWARD = 77
        ACTION_PLAYER_REWIND  = 78

        ACTION_PLAYER_PLAY    = 79
        ACTION_VOLUME_UP      = 88
        ACTION_VOLUME_DOWN    = 89
        ACTION_MUTE           = 91


        if (action == ACTION_PREVIOUS_MENU) or (action == ACTION_NAV_BACK):
            log("SonosControllerWindow: Close Action received: %s" % str(action))
            self.close()
        else:
            # Handle remote control commands
            if( (action == ACTION_PLAYER_PLAY) or (action == ACTION_PAUSE) ):
                # Get the initial state of the device
                playStatus = sonosDevice.get_current_transport_info()
                
                # Play/pause is a toggle, so pause if playing
                if playStatus != None:
                    if playStatus['current_transport_state'] == 'PLAYING':
                        self.onAction(SonosControllerWindow.BUTTON_PAUSE)
                    else:
                        self.onAction(SonosControllerWindow.BUTTON_PLAY)
            elif( action == ACTION_STOP ):
                self.onAction(SonosControllerWindow.BUTTON_STOP)
            elif( action == ACTION_NEXT_ITEM ):
                self.onAction(SonosControllerWindow.BUTTON_NEXT)
            elif( action == ACTION_PREV_ITEM ):
                self.onAction(SonosControllerWindow.BUTTON_PREVIOUS)
            elif( action == ACTION_MUTE ):
                # Check if currently muted
                if sonosDevice.mute() == 0:
                    self.onAction(SonosControllerWindow.BUTTON_MUTED)
                else:
                    self.onAction(SonosControllerWindow.BUTTON_NOT_MUTED)
            elif( action == ACTION_VOLUME_UP ):
                # Get the current slider position
                volumeSlider = self.getControl(SonosControllerWindow.SLIDER_VOLUME)
                currentSliderPosition = int(volumeSlider.getPercent())
                if currentSliderPosition < 100:
                    # Bump the volume by one
                    volumeSlider.setPercent(currentSliderPosition + 1)
                    self.onAction(SonosControllerWindow.SLIDER_VOLUME)
            elif( action == ACTION_VOLUME_DOWN ):
                # Get the current slider position
                volumeSlider = self.getControl(SonosControllerWindow.SLIDER_VOLUME)
                currentSliderPosition = int(volumeSlider.getPercent())
                if currentSliderPosition > 0:
                    # Bump the volume down by one
                    volumeSlider.setPercent(currentSliderPosition - 1)
                    self.onAction(SonosControllerWindow.SLIDER_VOLUME)
            elif( (action == ACTION_FORWARD) or (action == ACTION_PLAYER_FORWARD) ):
                # Get the current slider position
                seekSlider = self.getControl(SonosControllerWindow.SLIDER_SEEK)
                currentSliderPosition = int(seekSlider.getPercent())
                if currentSliderPosition < 99:
                    # Bump the slider by one
                    seekSlider.setPercent(currentSliderPosition + 1)
                    self.onAction(SonosControllerWindow.SLIDER_SEEK)
            elif( (action == ACTION_REWIND) or (action == ACTION_PLAYER_REWIND) ):
                # Get the current slider position
                seekSlider = self.getControl(SonosControllerWindow.SLIDER_SEEK)
                currentSliderPosition = int(seekSlider.getPercent())
                if currentSliderPosition > 0:
                    # Bump the slider down by one
                    seekSlider.setPercent(currentSliderPosition - 1)
                    self.onAction(SonosControllerWindow.SLIDER_SEEK)

            


    # Handle the close event - make sure we set the flag so we know it's been closed
    def close(self):
        self.closeRequested = True
        xbmcgui.WindowXMLDialog.close(self)

    def updateDisplay(self):
        # Get the current track information
        track = sonosDevice.get_current_track_info()

        # Only update if the track has changed
        if (track != None) and ((self.currentTrack == None) or (track['uri'] != self.currentTrack['uri'])):
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

            nextTrackLabel = self.getControl(SonosControllerWindow.NEXT_LABEL)
            # Clear the current text
            nextTrackLabel.reset()                

            # Display the track duration
            durationLabel = self.getControl(SonosControllerWindow.DURATION_LABEL)
            durationLabel.setLabel(self._stripHoursFromTime(track['duration']))

            # If the duration is 00:00:00 then this normally means that something like radio
            # is steaming so we shouldn't show any timing details
            if track['duration'] == '0:00:00':
                durationLabel.setVisible(False)
            else:
                durationLabel.setVisible(True)

            #################################################################
            # Note: the code below gives the next track in the playlist
            # not the next track to be played (which is the case if random)
            # No way to do that at the moment
            #################################################################

            # Check if there is a next track            
#             if track['playlist_position'] != "" and int(track['playlist_position']) > -1:
#                 # Also get the "Next Track" Information
#                 # 0 would be the current track
#                 nextTrackList = sonosDevice.get_queue(int(track['playlist_position']), 1)
#      
#                 if (nextTrackList != None) and (len(nextTrackList) > 0):
#                     nextTrackItem = nextTrackList[0]
#                     nextTrackText = "[COLOR=FF0084ff]%s:[/COLOR] %s - %s" % ("Next", nextTrackItem['title'], nextTrackItem['artist'])
#                     nextTrackLabel.addLabel(nextTrackText)

        self.currentTrack = track

        # Display the track position
        trackPositionLabel = self.getControl(SonosControllerWindow.TRACK_POSITION_LABEL)
        trackPositionLabel.setLabel(self._stripHoursFromTime(track['position']))

        # Get the initial state of the device
        playStatus = sonosDevice.get_current_transport_info()
        
        # Set the play/pause button to the correct value
        playButton = self.getControl(SonosControllerWindow.BUTTON_PLAY)
        if (playStatus != None) and (playStatus['current_transport_state'] == 'PLAYING'):
            playButton.setVisible(False)
        else:
            playButton.setVisible(True)
        
        # Check to see what the current state of the mute button is
        muteButton = self.getControl(SonosControllerWindow.BUTTON_NOT_MUTED)
        if sonosDevice.mute() == 0:
            muteButton.setVisible(True)
        else:
            muteButton.setVisible(False)

        # The following controls need a delayed refresh, this is because they
        # are controls like sliders, so we do not want to update them until
        # the slider operation is complete
        if self.delayedRefresh < 1:
    
            # Get the current volume and set the slider
            # Will return a value between 0 and 100
            currentVolume = sonosDevice.volume()
            # Get the slider control
            volumeSlider = self.getControl(SonosControllerWindow.SLIDER_VOLUME)
            # Don't move slider is already in correct position
            currentSliderPosition = int(volumeSlider.getPercent())
            if currentSliderPosition != currentVolume:
                volumeSlider.setPercent(currentVolume)

            # Set the seek slider
            self._setSeekSlider(track['position'],track['duration'])

        else:
            self.delayedRefresh = self.delayedRefresh - 1


    # Do the initial setup of the dialog
    def onInit(self):
        self.updateDisplay()

    # Handle the operations where the user clicks on a button
    def onClick(self, controlID):
        # Play button has been clicked
        if controlID == SonosControllerWindow.BUTTON_PLAY:
            log("SonosControllerWindow: Play Requested")

            # Send the play message to Sonos
            sonosDevice.play()
            self.setFocusId(SonosControllerWindow.BUTTON_PAUSE)

        elif controlID == SonosControllerWindow.BUTTON_PAUSE:
            log("SonosControllerWindow: Pause Requested")

            # Send the pause message to Sonos
            sonosDevice.pause()
            self.setFocusId(SonosControllerWindow.BUTTON_PLAY)

        elif controlID == SonosControllerWindow.BUTTON_NEXT:
            log("SonosControllerWindow: Next Track Requested")
            sonosDevice.next()

        elif controlID == SonosControllerWindow.BUTTON_PREVIOUS:
            log("SonosControllerWindow: Previous Track Requested")
            sonosDevice.previous()

        elif controlID == SonosControllerWindow.BUTTON_STOP:
            log("SonosControllerWindow: Stop Requested")
            sonosDevice.stop()

        elif controlID == SonosControllerWindow.BUTTON_NOT_MUTED:
            log("SonosControllerWindow: Mute Requested")
            sonosDevice.mute(True)
            self.setFocusId(SonosControllerWindow.BUTTON_MUTED)

        elif controlID == SonosControllerWindow.BUTTON_MUTED:
            log("SonosControllerWindow: Mute Requested")
            sonosDevice.mute(False)
            self.setFocusId(SonosControllerWindow.BUTTON_NOT_MUTED)

        elif controlID == SonosControllerWindow.SLIDER_VOLUME:
            # Get the position of the slider
            volumeSlider = self.getControl(SonosControllerWindow.SLIDER_VOLUME)
            currentSliderPosition = int(volumeSlider.getPercent())

            log("SonosControllerWindow: Volume Request to value: %d" % currentSliderPosition)

            # Before we send the volume change request we want to delay any refresh
            # on the gui so we have time to perform the slide operation without
            # the slider being reset
            self._setDelayedRefresh()

            # Now set the volume
            sonosDevice.volume(currentSliderPosition)

        elif controlID == SonosControllerWindow.SLIDER_SEEK:
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
        self.delayedRefresh = int( 4 / float(refreshInterval) )
        if self.delayedRefresh == 0:
            self.delayedRefresh = 1

    # Takes a time string (00:00:00) and removes the hour section if it is 0
    def _stripHoursFromTime(self, fullTimeString):
        if (fullTimeString == None) or (fullTimeString == ""):
            return "00:00"
        if fullTimeString.count(':') == 2:
            # Check if the hours section should be stripped
            hours = 0
            try:
                hours = int(fullTimeString.split(':',1)[0])
            except:
                # Hours section is not numbers
                log("SonosControllerWindow: Exception Details: %s" % traceback.format_exc())
                hours = 0

            # Only strip the hours if there are no hours
            if hours < 1:
                return fullTimeString.split(':',1)[-1]
        return fullTimeString

    # Set the seek slider to the current position of the track
    def _setSeekSlider(self, currentPosition, trackDuration):
        currentPositionSeconds = self._getSecondsInTimeString(currentPosition)
        trackDurationSeconds = self._getSecondsInTimeString(trackDuration)
        
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
        # Start by splitting the time into sections
        hours = 0
        minutes = 0
        seconds = 0
        
        try:
            hours = int(fullTimeString.split(':',1)[0])
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
        trackDurationSeconds = self._getSecondsInTimeString(self.currentTrack['duration'])

        if trackDurationSeconds > 0:
            # Get the current number of seconds into the track
            newPositionSeconds = int((float(percentage) * float(trackDurationSeconds))/100)
            
            # Convert the seconds into a timestamp
            newPosition = "0:00:00"

            # Convert the duration into a viewable format
            if newPositionSeconds > 0:
                seconds = newPositionSeconds % 60
                minutes = 0
                hours = 0
     
                if newPositionSeconds > 60:
                    minutes = ((newPositionSeconds - seconds) % 3600)/60

                if newPositionSeconds > 3600:
                    hours = (newPositionSeconds - (minutes*60) - seconds)/3600

                # Build the string up    
                newPosition = "%d:%02d:%02d" % (hours, minutes, seconds)

            # Now send the seek message to the sonos speaker
            sonosDevice.seek(newPosition)
        


if __name__ == '__main__':    
    
    sonosDevice = Settings.getSonosDevice()
    
    # Make sure a Sonos speaker was found
    if sonosDevice != None:

        sonosCtrl = SonosControllerWindow.createSonosControllerWindow(sonosDevice)
        
        # Record the fact that the Sonos controller window is displayed
        xbmcgui.Window(10000).setProperty( "SonosControllerShowing", "true" )

        try:
            sonosCtrl.show()

            while (not sonosCtrl.isClose()) and (not xbmc.abortRequested):
                sonosCtrl.updateDisplay()
                # Wait a second or so before updating
                xbmc.sleep(Settings.getRefreshInterval())
        except:
            # Failed to connect to the Sonos Speaker
            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), ("Error from speaker %s" % Settings.getIPAddress()))
            log("Sonos: Exception Details: %s" % traceback.format_exc())

        sonosCtrl.close()
        # Record the fact that the Sonos controller is no longer displayed
        xbmcgui.Window(10000).clearProperty("SonosControllerShowing")
        del sonosCtrl

    else:
        xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), "IP Address Not Set")
        
