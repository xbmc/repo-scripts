# -*- coding: utf-8 -*-
import sys
import os
import traceback
import xbmc
import xbmcaddon
import xbmcgui

__addon__     = xbmcaddon.Addon(id='script.sonos')
__addonid__   = __addon__.getAddonInfo('id')
__cwd__       = __addon__.getAddonInfo('path').decode("utf-8")
__version__   = __addon__.getAddonInfo('version')
__icon__      = __addon__.getAddonInfo('icon')
__resource__  = xbmc.translatePath( os.path.join( __cwd__, 'resources' ).encode("utf-8") ).decode("utf-8")
__lib__  = xbmc.translatePath( os.path.join( __resource__, 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

from soco import SoCo
from soco import SonosDiscovery
from soco import SoCoException


def log(txt):
    if __addon__.getSetting( "logEnabled" ) == "true":
        if isinstance (txt,str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

##############################
# Stores Addon Settings
##############################
class Settings():

    @staticmethod
    def getIPAddress():
        return __addon__.getSetting("ipAddress")

    @staticmethod
    def isNotificationEnabled():
        return __addon__.getSetting("notifEnabled") == 'true'

    @staticmethod
    def getNotificationDisplayDuration():
        # Convert to milliseconds before returning
        return int(float(__addon__.getSetting("notifDisplayDuration"))) * 1000

    @staticmethod
    def getNotificationCheckFrequency():
        # Value set in seconds
        return int(float(__addon__.getSetting("notifCheckFrequency")))

    @staticmethod
    def stopNotifIfVideoPlaying():
        return __addon__.getSetting("notifNotIfVideoPlaying") == 'true'

    @staticmethod
    def useXbmcNotifDialog():
        return __addon__.getSetting("xbmcNotifDialog") == 'true'


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


################################
# Main of the Sonos Service
################################
if __name__ == '__main__':
    log("SonosService: Starting service (version %s)" % __version__)
    
    if not Settings.isNotificationEnabled():
        log("SonosService: Notifications are disabled, exiting service")
    else:
        timeUntilNextCheck = Settings.getNotificationCheckFrequency()
        
        log("SonosService: Notification Check Frequency = %d" % timeUntilNextCheck)
        
        lastDisplayedTrack = None
        
        # Loop until XBMC exits
        while (not xbmc.abortRequested):
            if timeUntilNextCheck < 1:
                if Settings.stopNotifIfVideoPlaying() and xbmc.Player().isPlayingVideo():
                    log("SonosService: Video Playing, Skipping Notification Display")
                else:
                    log("SonosService: Notification wait time expired")
                    ipAddress = Settings.getIPAddress()
                    
                    log("SonosService: IP Address = %s" % ipAddress)
        
                    # Make sure the IP Address has been set
                    if ipAddress != "0.0.0.0":
                        sonosDevice = SoCo(ipAddress)
                      
                        # Should now have a single speaker set to "device"
                        if sonosDevice != None:
                            try:
                                # Get the current track that is being played at the moment
                                track = sonosDevice.get_current_track_info()
                                
                                # Check to see if a new track is playing before displaying the popup
                                if (track['uri'] == '') and (track['title'] == ''):
                                    track = None
                                    # Also make the last track value None as we don't want
                                    # this seen as a change
                                    lastDisplayedTrack = None
            
                                # Check to see if the playing track has changed
                                if (track != None) and ((lastDisplayedTrack == None) or (track['uri'] != lastDisplayedTrack['uri'])):
                                    # Update the last displayed track to the current one
                                    lastDisplayedTrack = track
                                    if Settings.useXbmcNotifDialog():
                                        log("SonosService: Currently playing artist = %s, album = %s, track = %s" % (track['artist'], track['album'], track['title']))
                             
                                        # Get the album art if it is set (Default to the Sonos icon)
                                        albumArt = __icon__
                                        if track['album_art'] != "":
                                            albumArt = track['album_art']
                            
                                        xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (track['artist'], track['title'], Settings.getNotificationDisplayDuration(), albumArt))
                                    else:
                                        sonosPopup = SonosPlayingPopup.createSonosPlayingPopup(track)
                                        sonosPopup.showPopup()
                                        del sonosPopup
                            except:
                                # Connection failure - may just be a network glitch - so don't exit
                                log("SonosService: Error from speaker %s" % ipAddress)
                                log("SonosService: %s" % traceback.format_exc())
    
                # Reset the timer for the next check
                timeUntilNextCheck = Settings.getNotificationCheckFrequency()
    
            # Increment the timer and sleep for a second before the next check
            xbmc.sleep(1000)
            timeUntilNextCheck = timeUntilNextCheck - 1

    log("Sonos: Stopping service")

    # Test code to test the dialog without a Sonos Speaker connected
#     track = {'title': 'Title value', 'artist': 'Artist Value', 'album': 'AlbumValue', 'album_art': '',
#             'position': ''}
# 
#     sonosPopup = SonosPlayingPopup.createSonosPlayingPopup(track)
#     sonosPopup.showPopup()
#     del sonosPopup
