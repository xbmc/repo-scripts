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


__addon__ = xbmcaddon.Addon(id='script.sonos')
__addonid__ = __addon__.getAddonInfo('id')
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
from settings import SocoLogging

from sonos import Sonos

import soco


##########################################################
# Class to display a popup of what is currently playing
##########################################################
class SonosPlayingPopup(xbmcgui.WindowXMLDialog):
    ICON = 400
    LABEL1 = 401
    LABEL2 = 402
    LABEL3 = 403

    def __init__(self, *args, **kwargs):
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
# Links the Sonos Volume to that of Kodi
#########################################
class SonosVolumeLink():
    def __init__(self, sonosDevice):
        self.sonosDevice = sonosDevice
        self.sonosVolume = 0
        self.sonosMuted = False
        self.xbmcPlayingProcessed = False

        # On Startup check to see if we need to switch the Sonos speaker to line-in
        if Settings.switchSonosToLineIn():
            self._switchToLineIn()

    def updateSonosVolume(self):
        # Check to see if the Sonos Volume Link is Enabled
        if not Settings.linkAudioWithSonos():
            return

        # Get the current Kodi Volume
        xbmcVolume, xbmcMuted = self._getXbmcVolume()
        log("SonosVolumeLink: xbmcVolume = %d, selfvol = %d" % (xbmcVolume, self.sonosVolume))
        # Check to see if it has changed, and if we need to change the sonos value
        if (xbmcVolume != -1) and (xbmcVolume != self.sonosVolume):
            log("SonosVolumeLink: Setting volume to = %d" % xbmcVolume)
            sonosDevice.volume = xbmcVolume
            self.sonosVolume = xbmcVolume

        # Check to see if Kodi has been muted
        if (xbmcMuted != -1) and (xbmcMuted != self.sonosMuted):
            sonosDevice.mute = xbmcMuted
            self.sonosMuted = xbmcMuted

    # This will return the volume in a range of 0-100
    def _getXbmcVolume(self):
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": { "properties": [ "volume", "muted" ] }, "id": 1}')
        json_query = simplejson.loads(result)

        volume = -1
        if ("result" in json_query) and ('volume' in json_query['result']):
            # Get the volume value
            volume = json_query['result']['volume']

        muted = None
        if ("result" in json_query) and ('muted' in json_query['result']):
            # Get the volume value
            muted = json_query['result']['muted']

        log("SonosVolumeLink: current volume: %s%%" % str(volume))
        return volume, muted

    def _switchToLineIn(self):
        # Check if we need to ensure the Sonos system is using the line-in
        try:
            # Not all speakers support line-in - so catch exception
            self.sonosDevice.switch_to_line_in()
            # Once switch to line in, some systems require that a play command is sent
            self.sonosDevice.play()
        except:
            log("SonosService: Failed to switch to Line-In for speaker %s" % Settings.getIPAddress())
            log("SonosService: %s" % traceback.format_exc())

    def switchToLineInIfXmbcPlaying(self):
        # Check if we need to switch to line in every time media starts playing
        if Settings.switchSonosToLineInOnMediaStart():
            # Check to see if something has started playing
            if xbmc.Player().isPlaying():
                # Check if we have already processed that something is playing
                if self.xbmcPlayingProcessed is False:
                    self.xbmcPlayingProcessed = True
                    log("SonosService: Switching to line-in because media started")
                    # Switch to line-in
                    self._switchToLineIn()
            else:
                # No longer playing, so need to process the next change
                self.xbmcPlayingProcessed = False


##############################################################
# Automatically Pauses Sonos if Kodi starts playing something
##############################################################
class SonosAutoPause():
    def __init__(self, sonosDevice):
        self.sonosDevice = sonosDevice
        self.xbmcPlayState = False
        self.autoStopped = False
        self.resumeCountdown = Settings.autoResumeSonos()

    # Check if the Sonos system should be paused or resumed
    def check(self):
        if Settings.autoPauseSonos() and not Settings.linkAudioWithSonos():
            try:
                # Check to see if something has started playing
                if xbmc.Player().isPlaying():
                    # If this is a change in play state since the last time we checked
                    if self.xbmcPlayState is False:
                        log("SonosAutoPause: Automatically pausing Sonos")
                        self.xbmcPlayState = True
                        # Pause the sonos if it is playing
                        if self._isSonosPlaying():
                            self.sonosDevice.pause()
                            self.autoStopped = True
                            self.resumeCountdown = Settings.autoResumeSonos()
                else:
                    self.xbmcPlayState = False
                    if Settings.autoResumeSonos() > 0 and self.autoStopped:
                        if self.resumeCountdown > 0:
                            self.resumeCountdown = self.resumeCountdown - 1
                        else:
                            log("SonosAutoPause: Automatically resuming Sonos")
                            self.sonosDevice.play()
                            self.autoStopped = False
                            self.resumeCountdown = Settings.autoResumeSonos()
            except:
                # If we fail to stop the speaker playing, it may be because
                # there is a network problem or the speaker is powered down
                # So we just continue after logging the error
                log("SonosAutoPause: Error from speaker %s" % Settings.getIPAddress())
                log("SonosAutoPause: %s" % traceback.format_exc())

    # Works out if the Sonos system is playing
    def _isSonosPlaying(self):
        playStatus = self.sonosDevice.get_current_transport_info()
        sonosPlaying = False
        if (playStatus is not None) and (playStatus['current_transport_state'] == 'PLAYING'):
            sonosPlaying = True
        return sonosPlaying


#################################################
# Sets the IP Address based off of the Zone Name
#################################################
class AutoUpdateIPAddress():
    def __init__(self):
        # Check if the auto update IP is enabled
        if not Settings.isAutoIpUpdateEnabled():
            return

        # Get the existing zone we are trying to set the IP Address for
        existingZone = Settings.getZoneName()

        # Nothing to do if there is no Zone name set
        if (existingZone is None) or (existingZone == ""):
            return

        # Set up the logging before using the Sonos Device
        SocoLogging.enable()

        try:
            sonos_devices = soco.discover()
        except:
            log("AutoUpdateIPAddress: Exception when getting devices")
            log("AutoUpdateIPAddress: %s" % traceback.format_exc())
            sonos_devices = []

        ipaddresses = []

        # Check each of the devices found
        for device in sonos_devices:
            ip = device.ip_address
            log("AutoUpdateIPAddress: Getting info for IP address %s" % ip)

            playerInfo = None

            # Try and get the player info, if it fails then it is not a valid
            # player and we should continue to the next
            try:
                playerInfo = device.get_speaker_info()
            except:
                log("AutoUpdateIPAddress: IP address %s is not a valid player" % ip)
                log("AutoUpdateIPAddress: %s" % traceback.format_exc())
                continue

            # If player  info was found, then print it out
            if playerInfo is not None:
                # What is the name of the zone that this speaker is in?
                zone_name = playerInfo['zone_name']

                # Check the zone against the ones we are looking for
                if zone_name == existingZone:
                    # There could be multiple IP addressing in the same group
                    # so save them all
                    log("AutoUpdateIPAddress: IP address %s in zone %s" % (ip, existingZone))
                    ipaddresses.append(ip)

        # Check if there is an IP Address to set
        if len(ipaddresses) > 0:
            oldIp = Settings.getIPAddress()
            # Check if we already have a match to the existing IP Address
            matchesExisting = False
            for newIp in ipaddresses:
                if newIp == oldIp:
                    matchesExisting = True
                    break
            # If no match found - then set to the first IP Address
            if not matchesExisting:
                log("AutoUpdateIPAddress: Setting IP address to %s" % ipaddresses[0])
                Settings.setIPAddress(ipaddresses[0])


################################
# Main of the Sonos Service
################################
if __name__ == '__main__':
    log("SonosService: Starting service (version %s)" % __version__)

    # Start by doing any auto-setting of the IP Address
    autoIpAdd = AutoUpdateIPAddress()
    del autoIpAdd

    # Check for the list of things that impact audio
    audioChanges = Settings.linkAudioWithSonos() or Settings.switchSonosToLineIn() or Settings.switchSonosToLineInOnMediaStart()

    # Check to see if we need to launch the Sonos Controller as soon as Kodi starts
    if Settings.autoLaunchControllerOnStartup():
        # Launch the Sonos controller, but do not block as we have more to do as a service
        log("SonosService: Launching controller on startup")
        xbmc.executebuiltin('RunScript(%s)' % (os.path.join(__cwd__, "default.py")), False)

    if (not Settings.isNotificationEnabled()) and (not audioChanges) and (not Settings.autoPauseSonos()):
        log("SonosService: Notifications, Volume Link and Auto Pause are disabled, exiting service")
    else:
        sonosDevice = Sonos.createSonosDevice()

        # Make sure a Sonos speaker was found
        if sonosDevice is not None:
            timeUntilNextCheck = Settings.getNotificationCheckFrequency()

            log("SonosService: Notification Check Frequency = %d" % timeUntilNextCheck)

            lastDisplayedTrack = None

            # Need to only display the popup when the service starts if there is
            # currently something playing
            justStartedService = True

            # Class to deal with sync of the volume
            volumeLink = SonosVolumeLink(sonosDevice)

            # Class that handles the automatic pausing of the Sonos system
            autoPause = SonosAutoPause(sonosDevice)

            # Loop until Kodi exits
            while (not xbmc.abortRequested):
                # Fist check to see if the Sonos needs to be switched
                # to line-in because media has started playing
                volumeLink.switchToLineInIfXmbcPlaying()

                # Make sure the volume matches
                volumeLink.updateSonosVolume()

                # Now check to see if the Sonos system needs pausing
                autoPause.check()

                if (timeUntilNextCheck < 1) and Settings.isNotificationEnabled():
                    if Settings.stopNotifIfVideoPlaying() and xbmc.Player().isPlayingVideo():
                        log("SonosService: Video Playing, Skipping Notification Display")
                    elif Settings.stopNotifIfControllerShowing() and (xbmcgui.Window(10000).getProperty("SonosControllerShowing") == 'true'):
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
                            elif justStartedService is True:
                                # Check if the sonos is currently playing
                                playStatus = sonosDevice.get_current_transport_info()
                                if (playStatus is None) or (playStatus['current_transport_state'] != 'PLAYING'):
                                    isActive = False

                            # Check to see if the playing track has changed
                            if (track is not None) and ((lastDisplayedTrack is None) or (track['uri'] != lastDisplayedTrack['uri'])):
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

            del volumeLink
            del autoPause
    log("Sonos: Stopping service")
