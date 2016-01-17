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
        # Save the volume from before any alterations
        self.original_volume = -1

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

        self.playListItems = []

        self.repeatOneSet = False

        self.tvtunesPlayerStarted = False

        # Mark the initial refresh rate as unset
        self.original_refreshrate = 0

        xbmc.Player.__init__(self, *args)

    def onPlayBackStopped(self):
        # The Notifications for a player will be picked up even if it was not
        # this instance of the player that started the theme, so check to ensure
        # TvTunes is actually the responsible for starting the player
        if self.tvtunesPlayerStarted:
            log("ThemePlayer: Received onPlayBackStopped")
            self.restoreSettings()
        xbmc.Player.onPlayBackStopped(self)

    def onPlayBackStarted(self):
        # The Notifications for a player will be picked up even if it was not
        # this instance of the player that started the theme, so check to ensure
        # TvTunes is actually the responsible for starting the player
        if self.tvtunesPlayerStarted:
            # Check if the item that has just been started is one of our themes
            # if it isn't then the user has manually started a new media file, so we
            # need to stop the current one
            if not self.isPlayingTheme():
                self.restoreSettings()
        xbmc.Player.onPlayBackStarted(self)

    def restoreSettings(self):
        log("ThemePlayer: Restoring player settings")
        self.tvtunesPlayerStarted = False

        # Check if the refresh rate need to be restored
        if self.original_refreshrate != 0:
            # Disable the refresh rate setting
            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Settings.SetSettingValue",  "params": { "setting": "videoplayer.adjustrefreshrate", "value": %d }, "id": 1}' % self.original_refreshrate)
            log("ThemePlayer: Restored refresh rate to %d" % self.original_refreshrate)
            self.original_refreshrate = 0

        # Restore repeat state
        log("ThemePlayer: Restoring setting repeat to RepeatOff")
        # Need to use the player control as the json one did not seem to work with
        # videos, but we also call the JSON version as that catches more cases where
        # the video has stopped - it's strange - but it works
        xbmc.executebuiltin("PlayerControl(RepeatOff)")
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.SetRepeat", "params": {"playerid": 0, "repeat": "off" }, "id": 1 }')
        self.repeatOneSet = False

        # Give the theme a chance to finish if it is still playing
        maxLoop = 3000
        while self.isPlayingTheme() and (maxLoop > 0):
            maxLoop = maxLoop - 1
            xbmc.sleep(1)

        # Force the volume to the starting volume, but only if we have changed it
        if self.hasChangedVolume:
            # There have been reports of some audio systems like PulseAudio return that they have
            # stopped playing the audio, however they have not quite finished, to accommodate
            # this we add an extra sleep in here
            xbmc.sleep(350)
            if self.original_volume > -1:
                self._setVolume(self.original_volume)
            # Record that the volume has been restored
            self.hasChangedVolume = False
            log("ThemePlayer: Restored volume to %d" % self.original_volume)

        # Record the time that playing was started (0 is stopped)
        self.startTime = 0

    def stop(self):
        log("ThemePlayer: stop called")
        self.tvtunesPlayerStarted = False

        log("ThemePlayer: Restoring setting repeat to RepeatOff")
        # Need to use the player control as the json one did not seem to work with
        # videos, but we also call the JSON version as that catches more cases where
        # the video has stopped - it's strange - but it works
        xbmc.executebuiltin("PlayerControl(RepeatOff)")
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.SetRepeat", "params": {"playerid": 0, "repeat": "off" }, "id": 1 }')
        self.repeatOneSet = False

        # Only stop if playing audio
        if self.isPlaying():
            xbmc.Player.stop(self)
        self.restoreSettings()

    def play(self, item=None, listitem=None, windowed=True, fastFade=False):
        self.tvtunesPlayerStarted = True

        # if something is already playing, then we do not want
        # to replace it with the theme
        if not self.isPlaying():
            self.updateVideoRefreshRate(item)
            # Save the volume from before any alterations
            self.original_volume = self._getVolume()
            # Perform and lowering of the sound for theme playing
            self._lowerVolume()

            if Settings.isFadeIn():
                # Get the current volume - this is our target volume
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
                maxLoop = 100
                while (not self.isPlaying()) and (not xbmc.abortRequested) and (maxLoop > 0):
                    maxLoop = maxLoop - 1
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
                xbmc.executebuiltin("PlayerControl(RepeatAll)")
                # We no longer use the JSON method to repeat as it does not work with videos
                # xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.SetRepeat", "params": {"playerid": 0, "repeat": "all" }, "id": 1 }')

                # If we had a random start and we are looping then we need to make sure
                # when it comes to play the theme for a second time it starts at the beginning
                # and not from the same mid-point
                if Settings.isRandomStart():
                    item[0].setProperty('StartOffset', "0")
            else:
                xbmc.executebuiltin("PlayerControl(RepeatOff)")
                # We no longer use the JSON method to repeat as it does not work with videos
                # xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.SetRepeat", "params": {"playerid": 0, "repeat": "off" }, "id": 1 }')

            # Record the time that playing was started
            self.startTime = int(time.time())

            # Clear the current playlist, as we will re-populate it
            self.playListItems = []

            # Save off the number of items in the playlist
            if item is not None:
                self.playlistSize = item.size()
                log("ThemePlayer: Playlist size = %d" % self.playlistSize)

                # Store a list of all the tracks in the playlist
                try:
                    i = 0
                    while i < self.playlistSize:
                        self.playListItems.append(item[i].getfilename())
                        i = i + 1
                except:
                    log("ThemePlayer: Failed to save off playlist")

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
            reducedVolume = Settings.getThemeVolume()
            if reducedVolume > 0:
                # Save the volume from before any alterations
                self.original_volume = self._getVolume()
                log("ThemePlayer: volume goal: %d%% " % reducedVolume)
                self._setVolume(reducedVolume)
            else:
                log("ThemePlayer: No reduced volume option set")
        except:
            log("ThemePlayer: %s" % traceback.format_exc(), True, xbmc.LOGERROR)

    # Graceful end of the playing, will fade if set to do so
    def endPlaying(self, fastFade=False, slowFade=False):
        # If we are stopping audio and we do not have a value for the original volume
        # then it means we are stopping something that we did not start, this means that
        # before we do anything like fade the volume out we should get the current
        # volume and store it as the base level
        if self.original_volume < 0:
            self.original_volume = self._getVolume()

        if self.isPlayingAudio() and Settings.isFadeOut():
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
        # Check for the case where the user is playing a video and an audio theme in the
        # same playlist and wants to repeat the audio theme after the video finishes
        try:
            if (not self.repeatOneSet) and self.isPlayingAudio() and Settings.isRepeatSingleAudioAfterVideo():
                # Check to see if the first item was a video
                if len(self.playListItems) > 1:
                    if Settings.isVideoFile(self.playListItems[0]):
                        # So we know that we did play a video, now we are
                        # playing an audio file, so set repeat on the current item
                        log("ThemePlayer: Setting single track to repeat %s" % self.playListItems[1])
                        xbmc.executebuiltin("PlayerControl(RepeatOne)")
                        self.repeatOneSet = True
        except:
            log("ThemePlayer: Failed to check audio repeat after video")

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

        # Allow for the case where the track has just been stopped, in which
        # case the call to get the total time will fail as there is no track
        # to get the length of
        try:
            trackLength = int(self.getTotalTime())
            log("ThemePlayer: track length = %d" % trackLength)
            if trackLimit > trackLength and (Settings.isLoop() or self.remainingTracks > 0):
                self.remainingTracks = self.remainingTracks - 1
                self.trackEndTime = self.trackEndTime + trackLength
        except:
            log("ThemePlayer: Failed to get track total time as not playing")
            self.trackEndTime = -1

    # Check if tTvTunes is playing a video theme
    def isPlayingTheme(self):
        # All audio is considered a theme
        if self.isPlayingAudio():
            return True

        if not self.isPlayingVideo():
            return False

        filePlaying = ""
        try:
            # Get the currently playing file
            filePlaying = self.getPlayingFile()
        except:
            log("ThemePlayer: Exception when checking if theme is playing")

        if filePlaying in self.playListItems:
            return True
        return False

    def updateVideoRefreshRate(self, themePlayList):
        # Check if the setting is enabled to switch the refresh rate
        if not Settings.blockRefreshRateChange():
            self.original_refreshrate = 0
            return

        log("ThemePlayer: Checking for update of refresh rate")

        try:
            # Check if we have any videos in the PlayList
            hasVideoFiles = True
            i = 0
            while i < themePlayList.size():
                if Settings.isVideoFile(themePlayList[i].getfilename()):
                    hasVideoFiles = True
                    break
                i = i + 1

            if hasVideoFiles:
                # Save off the existing refresh setting
                jsonresponse = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Settings.GetSettingValue",  "params": { "setting": "videoplayer.adjustrefreshrate" }, "id": 1}')
                data = simplejson.loads(jsonresponse)
                if 'result' in data:
                    if 'value' in data['result']:
                        self.original_refreshrate = data['result']['value']
                        # Check if the refresh rate is currently set
                        log("ThemePlayer: Video refresh rate currently set to %d" % self.original_refreshrate)

                # Check if the refresh rate is currently set, if it is, then we need
                if self.original_refreshrate != 0:
                    # Disable the refresh rate setting
                    log("ThemePlayer: Disabling refresh rate")
                    xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Settings.SetSettingValue",  "params": { "setting": "videoplayer.adjustrefreshrate", "value": 0 }, "id": 1}')
        except:
            log("ThemePlayer: Failed to process video refresh")
