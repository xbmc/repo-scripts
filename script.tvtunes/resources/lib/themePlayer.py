# -*- coding: utf-8 -*-
import time
import traceback
import xbmc
import sys

# Add JSON support for queries
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

# Import the common settings
from settings import Settings
from settings import log
from settings import WindowShowing


###################################
# Custom Player to play the themes
###################################
class ThemePlayer(xbmc.Player):
    def __init__(self, *args):
        # Record if the volume is currently altered
        self.hasChangedVolume = False
        self.hasChangedRepeat = False
        # Save the volume from before any alterations
        self.original_volume = self._getVolume()

        # Record the time that playing was started
        # 0 is not playing
        self.startTime = 0

        # Record the number of items in the playlist
        self.playlistSize = 1

        # Time the track started playing
        self.trackEndTime = -1

        # Record the number of tracks left to play in the playlist
        # (Only used if skipping through tracks)
        self.remainingTracks = -1

        self.playListItems = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)

        # Save off the current repeat state before we started playing anything
        if xbmc.getCondVisibility('Playlist.IsRepeat'):
            self.repeat = "all"
        elif xbmc.getCondVisibility('Playlist.IsRepeatOne'):
            self.repeat = "one"
        else:
            self.repeat = "off"

        xbmc.Player.__init__(self, *args)

    def onPlayBackStopped(self):
        log("ThemePlayer: Received onPlayBackStopped")
        self.restoreSettings()
        xbmc.Player.onPlayBackStopped(self)

    def onPlayBackEnded(self):
        log("ThemePlayer: Received onPlayBackEnded")
        self.restoreSettings()
        xbmc.Player.onPlayBackEnded(self)

    def restoreSettings(self):
        log("ThemePlayer: Restoring player settings")
        # We could be doing a video background rather than audio, but
        # if that is the case, we have no choice but to start resetting
        # as we will not know the difference between the video theme stopping
        # and the video movie/tv show starting
        while self.isPlayingAudio():
            xbmc.sleep(1)
        # Restore repeat state
        if self.hasChangedRepeat:
            xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.SetRepeat", "params": {"playerid": 0, "repeat": "%s" }, "id": 1 }' % self.repeat)
            self.hasChangedRepeat = False
        # Force the volume to the starting volume, but only if we have changed it
        if self.hasChangedVolume:
            # There have been reports of some audio systems like PulseAudio return that they have
            # stopped playing the audio, however they have not quite finished, to accommodate
            # this we add an extra sleep in here
            xbmc.sleep(350)
            self._setVolume(self.original_volume)
            # Record that the volume has been restored
            self.hasChangedVolume = False
            log("ThemePlayer: Restored volume to %d" % self.original_volume)
        # Record the time that playing was started (0 is stopped)
        self.startTime = 0

    def stop(self):
        log("ThemePlayer: stop called")
        # Only stop if playing audio
        if self.isPlaying():
            xbmc.Player.stop(self)
        self.restoreSettings()

    def play(self, item=None, listitem=None, windowed=True, fastFade=False):
        # if something is already playing, then we do not want
        # to replace it with the theme
        if not self.isPlaying():
            self.playListItems = item
            # Perform and lowering of the sound for theme playing
            self._lowerVolume()

            if Settings.isFadeIn():
                # Get the current volume - this is out target volume
                targetVol = self._getVolume()
                cur_vol_perc = 1

                # Calculate how fast to fade the theme, this determines
                # the number of step to drop the volume in
                numSteps = 10
                if fastFade:
                    numSteps = numSteps / 2

                vol_step = targetVol / numSteps
                # Reduce the volume before starting
                # do not mute completely else the mute icon shows up
                self._setVolume(1)
                # Now start playing before we start increasing the volume
                xbmc.Player.play(self, item=item, listitem=listitem, windowed=windowed)

                # Wait until playing has started
                while not self.isPlaying():
                    xbmc.sleep(30)

                for step in range(0, (numSteps - 1)):
                    # If the system is going to be shut down then we need to reset
                    # everything as quickly as possible
                    if WindowShowing.isShutdownMenu() or xbmc.abortRequested:
                        log("ThemePlayer: Shutdown menu detected, cancelling fade in")
                        break
                    vol = cur_vol_perc + vol_step
                    log("ThemePlayer: fadeIn_vol: %s" % str(vol))
                    self._setVolume(vol)
                    cur_vol_perc = vol
                    xbmc.sleep(200)
                # Make sure we end on the correct volume
                self._setVolume(targetVol)
            else:
                xbmc.Player.play(self, item=item, listitem=listitem, windowed=windowed)

            if Settings.isLoop():
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.SetRepeat", "params": {"playerid": 0, "repeat": "all" }, "id": 1 }')
                # If we had a random start and we are looping then we need to make sure
                # when it comes to play the theme for a second time it starts at the beginning
                # and not from the same mid-point
                if Settings.isRandomStart():
                    item[0].setProperty('StartOffset', "0")
            else:
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.SetRepeat", "params": {"playerid": 0, "repeat": "off" }, "id": 1 }')

            self.hasChangedRepeat = True

            # Record the time that playing was started
            self.startTime = int(time.time())

            # Save off the number of items in the playlist
            if item is not None:
                self.playlistSize = item.size()
                log("ThemePlayer: Playlist size = %d" % self.playlistSize)
                # Check if we are limiting each track in the list
                if not Settings.isLoop():
                    # Already started playing the first, so the remaining number of
                    # tracks is one less than the total
                    self.remainingTracks = self.playlistSize - 1
                self._setNextSkipTrackTime(self.startTime)
            else:
                self.playlistSize = 1

    # This will return the volume in a range of 0-100
    def _getVolume(self):
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": { "properties": [ "volume" ] }, "id": 1}')

        json_query = simplejson.loads(result)
        if ("result" in json_query) and ('volume' in json_query['result']):
            # Get the volume value
            volume = json_query['result']['volume']

        log("ThemePlayer: current volume: %s%%" % str(volume))
        return volume

    # Sets the volume in the range 0-100
    def _setVolume(self, newvolume):
        # Can't use the RPC version as that will display the volume dialog
        # '{"jsonrpc": "2.0", "method": "Application.SetVolume", "params": { "volume": %d }, "id": 1}'
        xbmc.executebuiltin('SetVolume(%d)' % newvolume, True)
        self.hasChangedVolume = True

    def _lowerVolume(self):
        try:
            if Settings.getDownVolume() != 0:
                current_volume = self._getVolume()
                vol = current_volume - Settings.getDownVolume()
                # Make sure the volume still has a value
                if vol < 1:
                    vol = 1
                log("ThemePlayer: volume goal: %d%% " % vol)
                self._setVolume(vol)
            else:
                log("ThemePlayer: No reduced volume option set")
        except:
            log("ThemePlayer: %s" % traceback.format_exc(), True, xbmc.LOGERROR)

    # Graceful end of the playing, will fade if set to do so
    def endPlaying(self, fastFade=False, slowFade=False):
        if self.isPlaying() and Settings.isFadeOut():
            cur_vol = self._getVolume()

            # Calculate how fast to fade the theme, this determines
            # the number of step to drop the volume in
            numSteps = 10
            if fastFade:
                numSteps = numSteps / 2
            elif slowFade:
                numSteps = numSteps * 4

            vol_step = cur_vol / numSteps
            # do not mute completely else the mute icon shows up
            for step in range(0, (numSteps - 1)):
                # If the system is going to be shut down then we need to reset
                # everything as quickly as possible
                if WindowShowing.isShutdownMenu() or xbmc.abortRequested:
                    log("ThemePlayer: Shutdown menu detected, cancelling fade out")
                    break
                vol = cur_vol - vol_step
                log("ThemePlayer: fadeOut_vol: %s" % str(vol))
                self._setVolume(vol)
                cur_vol = vol
                xbmc.sleep(200)
            # The final stop and reset of the settings will be done
            # outside of this "if"
        # Need to always stop by the end of this
        self.stop()

    # Checks if the play duration has been exceeded and then stops playing
    def checkEnding(self):
        if self.isPlaying() and (self.startTime > 0):
            # Get the current time
            currTime = int(time.time())

            # Time in minutes to play for
            durationLimit = Settings.getPlayDurationLimit()
            if durationLimit > 0:
                expectedEndTime = self.startTime + (60 * durationLimit)

                if currTime > expectedEndTime:
                    self.endPlaying(slowFade=True)
                    return

            # Check for the case where only a given amount of time of the track will be played
            # Only skip forward if there is a track left to play - otherwise just keep
            # playing the last track
            if (self.playlistSize > 1) and (self.remainingTracks != 0):
                trackLimit = Settings.getTrackLengthLimit()
                if trackLimit > 0:
                    if currTime > self.trackEndTime:
                        log("ThemePlayer: Skipping to next track after %s" % self.getPlayingFile())
                        self.playnext()
                        if self.remainingTracks != -1:
                            self.remainingTracks = self.remainingTracks - 1
                        self._setNextSkipTrackTime(currTime)

    # Calculates the next time that "playnext" on a playlist should be called
    def _setNextSkipTrackTime(self, currentTime):
        trackLimit = Settings.getTrackLengthLimit()
        if trackLimit < 1:
            self.trackEndTime = -1
            return
        self.trackEndTime = currentTime + trackLimit
        trackLength = int(self.getTotalTime())
        log("ThemePlayer: track length = %d" % trackLength)
        if trackLimit > trackLength and (Settings.isLoop() or self.remainingTracks > 0):
            self.remainingTracks = self.remainingTracks - 1
            self.trackEndTime = self.trackEndTime + trackLength

    # Check if tTvTunes is playing a video theme
    def isPlayingTheme(self):
        # All audio is considered a theme
        if self.isPlayingAudio():
            return True

        if not self.isPlayingVideo():
            return False

        try:
            # Get the currently playing file
            filePlaying = self.getPlayingFile()

            i = 0
            while i < self.playlistSize:
                if self.playListItems[i].getfilename() == filePlaying:
                    return True
                i = i + 1
        except:
            log("ThemePlayer: Exception when checking if theme is playing")
        return False
