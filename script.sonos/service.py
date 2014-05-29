# -*- coding: utf-8 -*-
import sys
import os
import traceback
import xbmc
import xbmcaddon
import xbmcgui

# Add JSON support for queries
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson


__addon__     = xbmcaddon.Addon(id='script.sonos')
__addonid__   = __addon__.getAddonInfo('id')
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

##########################################################
# Class to display a popup of what is currently playing
##########################################################
class SonosPlayingPopup(xbmcgui.WindowXMLDialog):
    ICON = 400
    LABEL1 = 401
    LABEL2 = 402
    LABEL3 = 403

    def __init__( self, *args, **kwargs ):
        # Copy off the key-word arguments
        # The non keyword arguments will be the ones passed to the main WindowXML
        self.artist = kwargs.pop('artist')
        self.album = kwargs.pop('album')
        self.title = kwargs.pop('title')
        self.albumArt = kwargs.pop('albumArt')

    # Static method to create the Window Dialog class
    @staticmethod
    def createSonosPlayingPopup(track):
        # Creating popup for
        log("SonosPlayingPopup: Currently playing artist = %s, album = %s, track = %s" % (track['artist'], track['album'], track['title']))
        
        # Get the album art if it is set (Default to the Sonos icon)
        albumArt = __icon__
        if track['album_art'] != "":
            albumArt = track['album_art']

        return SonosPlayingPopup("script-sonos-notif-popup.xml", __cwd__, artist=track['artist'], album=track['album'], title=track['title'], albumArt=albumArt)

    def onInit(self):
        # Need to populate the popup with the artist details
        label1 = self.getControl(SonosPlayingPopup.LABEL1)
        label1.addLabel(self.artist)

        label2 = self.getControl(SonosPlayingPopup.LABEL2)
        label2.addLabel(self.album)

        label3 = self.getControl(SonosPlayingPopup.LABEL3)
        label3.addLabel(self.title)

        icon = self.getControl(SonosPlayingPopup.ICON)
        icon.setImage(self.albumArt)

        xbmcgui.WindowXMLDialog.onInit(self)

    def showPopup(self):
        self.show()
        xbmc.sleep(Settings.getNotificationDisplayDuration())
        self.close()

#########################################
# Links the Sonos Volume to that of XBMC
#########################################
class SonosVolumeLink():
    def __init__(self, sonosDevice):
        self.sonosDevice = sonosDevice
        self.sonosVolume = 0
        self.sonosMuted = False
        
        # On Startup check to see if we need to switch the SOnos speaker to line-in
        self.switchToLineIn()

    def updateSonosVolume(self):
        # Check to see if the Sonos Volume Link is Enabled
        if not Settings.linkAudioWithSonos():
            return

        # Get the current XBMC Volume
        xbmcVolume, xbmcMuted = self._getXbmcVolume()
        log("*** ROB ***: xbmcVolume = %d, selfvol = %d" % (xbmcVolume, self.sonosVolume))
        # Check to see if it has changed, and if we need to change the sonos value
        if (xbmcVolume != -1) and (xbmcVolume != self.sonosVolume):
            log("*** ROB ***: Setting volume to = %d" % xbmcVolume)
            
            sonosDevice.volume = xbmcVolume
            self.sonosVolume = xbmcVolume

        # Check to see if XBMC has been muted
        if (xbmcMuted != -1) and (xbmcMuted != self.sonosMuted):
            sonosDevice.mute = xbmcMuted
            self.sonosMuted = xbmcMuted

    # This will return the volume in a range of 0-100
    def _getXbmcVolume(self):
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": { "properties": [ "volume", "muted" ] }, "id": 1}')
        json_query = simplejson.loads(result)

        volume = -1
        if "result" in json_query and json_query['result'].has_key('volume'):
            # Get the volume value
            volume = json_query['result']['volume']

        muted = None
        if "result" in json_query and json_query['result'].has_key('muted'):
            # Get the volume value
            muted = json_query['result']['muted']

        log( "Player: current volume: %s%%" % str(volume) )
        return volume, muted

    def switchToLineIn(self):
        # Check if we need to ensure the Sonos system is using the line-in
        if Settings.switchSonosToLineIn():
            try:
                # Not all speakers support line-in - so catch exception
                self.sonosDevice.switch_to_line_in()
            except:
                log("SonosService: Failed to switch to Line-In for speaker %s" % Settings.getIPAddress())
                log("SonosService: %s" % traceback.format_exc())

        

################################
# Main of the Sonos Service
################################
if __name__ == '__main__':
    log("SonosService: Starting service (version %s)" % __version__)

    if (not Settings.isNotificationEnabled()) and (not Settings.linkAudioWithSonos()):
        log("SonosService: Notifications and Volume Link are disabled, exiting service")
    else:
        sonosDevice = Settings.getSonosDevice()

        # Make sure a Sonos speaker was found
        if sonosDevice != None:
            timeUntilNextCheck = Settings.getNotificationCheckFrequency()
            
            log("SonosService: Notification Check Frequency = %d" % timeUntilNextCheck)
            
            lastDisplayedTrack = None
            
            # Need to only display the popup when the service starts if there is
            # currently something playing
            justStartedService = True

            # Class to deal with sync of the volume
            volumeLink = SonosVolumeLink(sonosDevice)

            # Loop until XBMC exits
            while (not xbmc.abortRequested):
                # First make sure the volume matches
                volumeLink.updateSonosVolume()
                
                if (timeUntilNextCheck < 1) and Settings.isNotificationEnabled():
                    if Settings.stopNotifIfVideoPlaying() and xbmc.Player().isPlayingVideo():
                        log("SonosService: Video Playing, Skipping Notification Display")
                    elif xbmcgui.Window(10000).getProperty("SonosControllerShowing") == 'true':
                        log("SonosService: Sonos Controller Showing, Skipping Notification Display")
                        # Reset the "just started" flag to ensure that when we exit it does not
                        # show the notification immediately
                        justStartedService = True
                    else:
                        log("SonosService: Notification wait time expired")        
                        
                        try:
                            # Get the current track that is being played at the moment
                            track = sonosDevice.get_current_track_info()
                            
                            # Record if the sonos is currently playing
                            isActive = True
                            
                            # Check to see if a new track is playing before displaying the popup
                            if (track['uri'] == '') or (track['title'] == ''):
                                track = None
                                # Also make the last track value None as we don't want
                                # this seen as a change
                                lastDisplayedTrack = None
                            elif justStartedService == True:
                                # Check if the sonos is currently playing
                                playStatus = sonosDevice.get_current_transport_info()
                                if (playStatus == None) or (playStatus['current_transport_state'] != 'PLAYING'):
                                    isActive = False
        
                            # Check to see if the playing track has changed
                            if (track != None) and ((lastDisplayedTrack == None) or (track['uri'] != lastDisplayedTrack['uri'])):
                                # Update the last displayed track to the current one
                                lastDisplayedTrack = track
                                # Only display the dialog if it is playing
                                if isActive:
                                    if Settings.useXbmcNotifDialog():
                                        log("SonosService: Currently playing artist = %s, album = %s, track = %s" % (track['artist'], track['album'], track['title']))
                             
                                        # Get the album art if it is set (Default to the Sonos icon)
                                        albumArt = __icon__
                                        if track['album_art'] != "":
                                            albumArt = track['album_art']
    
                                        if Settings.getXbmcMajorVersion() < 13:
                                            xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (track['artist'], track['title'], Settings.getNotificationDisplayDuration(), albumArt))
                                        else:
                                            # Gotham allows you to have a dialog without making a sound
                                            xbmcgui.Dialog().notification(track['artist'], track['title'], albumArt, Settings.getNotificationDisplayDuration(), False)
                                    else:
                                        sonosPopup = SonosPlayingPopup.createSonosPlayingPopup(track)
                                        sonosPopup.showPopup()
                                        del sonosPopup
                        except:
                            # Connection failure - may just be a network glitch - so don't exit
                            log("SonosService: Error from speaker %s" % Settings.getIPAddress())
                            log("SonosService: %s" % traceback.format_exc())
    
                        # No longer the first start
                        justStartedService = False

                    # Reset the timer for the next check
                    timeUntilNextCheck = Settings.getNotificationCheckFrequency()
        
                # Increment the timer and sleep for a second before the next check
                xbmc.sleep(1000)
                timeUntilNextCheck = timeUntilNextCheck - 1

    log("Sonos: Stopping service")
