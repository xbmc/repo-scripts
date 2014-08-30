# -*- coding: utf-8 -*-
import os
import threading
import time
import traceback
import xbmc
import xbmcgui
import sys
import xbmcaddon

# Add JSON support for queries
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson


__addon__ = xbmcaddon.Addon(id='script.tvtunes')
__addonid__ = __addon__.getAddonInfo('id')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join
from settings import normalize_string

from themeFinder import ThemeFiles


###################################
# Custom Player to play the themes
###################################
class Player(xbmc.Player):
    def __init__(self, *args):
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

        # Save off the current repeat state before we started playing anything
        if xbmc.getCondVisibility('Playlist.IsRepeat'):
            self.repeat = "all"
        elif xbmc.getCondVisibility('Playlist.IsRepeatOne'):
            self.repeat = "one"
        else:
            self.repeat = "off"

        xbmc.Player.__init__(self, *args)

    def onPlayBackStopped(self):
        log("Player: Received onPlayBackStopped")
        self.restoreSettings()
        xbmc.Player.onPlayBackStopped(self)

    def onPlayBackEnded(self):
        log("Player: Received onPlayBackEnded")
        self.restoreSettings()
        xbmc.Player.onPlayBackEnded(self)

    def restoreSettings(self):
        log("Player: Restoring player settings")
        while self.isPlayingAudio():
            xbmc.sleep(1)
        # Force the volume to the starting volume
        self._setVolume(self.original_volume)
        # restore repeat state
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.SetRepeat", "params": {"playerid": 0, "repeat": "%s" }, "id": 1 }' % self.repeat)
        # Record the time that playing was started (0 is stopped)
        self.startTime = 0
        log("Player: Restored volume to %d" % self.original_volume)

    def stop(self):
        log("Player: stop called")
        # Only stop if playing audio
        if self.isPlayingAudio():
            xbmc.Player.stop(self)
        self.restoreSettings()

    def play(self, item=None, listitem=None, windowed=False, fastFade=False):
        # if something is already playing, then we do not want
        # to replace it with the theme
        if not self.isPlaying():
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
                while not self.isPlayingAudio():
                    xbmc.sleep(30)

                for step in range(0, (numSteps - 1)):
                    # If the system is going to be shut down then we need to reset
                    # everything as quickly as possible
                    if WindowShowing.isShutdownMenu() or xbmc.abortRequested:
                        log("Player: Shutdown menu detected, cancelling fade in")
                        break
                    vol = cur_vol_perc + vol_step
                    log("Player: fadeIn_vol: %s" % str(vol))
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

            # Record the time that playing was started
            self.startTime = int(time.time())

            # Save off the number of items in the playlist
            if item is not None:
                self.playlistSize = item.size()
                log("Player: Playlist size = %d" % self.playlistSize)
                # Check if we are limiting each track in the list
                if not Settings.isLoop():
                    # Already started laying the first, so the remaining number of
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

        log("Player: current volume: %s%%" % str(volume))
        return volume

    # Sets the volume in the range 0-100
    def _setVolume(self, newvolume):
        # Can't use the RPC version as that will display the volume dialog
        # '{"jsonrpc": "2.0", "method": "Application.SetVolume", "params": { "volume": %d }, "id": 1}'
        xbmc.executebuiltin('XBMC.SetVolume(%d)' % newvolume, True)

    def _lowerVolume(self):
        try:
            if Settings.getDownVolume() != 0:
                current_volume = self._getVolume()
                vol = current_volume - Settings.getDownVolume()
                # Make sure the volume still has a value
                if vol < 1:
                    vol = 1
                log("Player: volume goal: %d%% " % vol)
                self._setVolume(vol)
            else:
                log("Player: No reduced volume option set")
        except:
            log("Player: %s" % traceback.format_exc())

    # Graceful end of the playing, will fade if set to do so
    def endPlaying(self, fastFade=False, slowFade=False):
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
                    log("Player: Shutdown menu detected, cancelling fade out")
                    break
                vol = cur_vol - vol_step
                log("Player: fadeOut_vol: %s" % str(vol))
                self._setVolume(vol)
                cur_vol = vol
                xbmc.sleep(200)
            # The final stop and reset of the settings will be done
            # outside of this "if"
        # Need to always stop by the end of this
        self.stop()

    # Checks if the play duration has been exceeded and then stops playing
    def checkEnding(self):
        if self.isPlayingAudio() and (self.startTime > 0):
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
                        log("Player: Skipping to next track after %s" % self.getPlayingFile())
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
        log("Player: track length = %d" % trackLength)
        if trackLimit > trackLength and (Settings.isLoop() or self.remainingTracks > 0):
            self.remainingTracks = self.remainingTracks - 1
            self.trackEndTime = self.trackEndTime + trackLength


###############################################################
# Class to make it easier to see which screen is being checked
###############################################################
class WindowShowing():
    @staticmethod
    def isHome():
        return xbmc.getCondVisibility("Window.IsVisible(home)")

    @staticmethod
    def isVideoLibrary():
        return xbmc.getCondVisibility("Window.IsVisible(videolibrary)") or WindowShowing.isTvTunesOverrideTvShows() or WindowShowing.isTvTunesOverrideMovie() or WindowShowing.isTvTunesOverrideContinuePlaying()

    @staticmethod
    def isMovieInformation():
        return xbmc.getCondVisibility("Window.IsVisible(movieinformation)") or WindowShowing.isTvTunesOverrideMovie()

    @staticmethod
    def isTvShows():
        return xbmc.getCondVisibility("Container.Content(tvshows)") or WindowShowing.isTvTunesOverrideTvShows()

    @staticmethod
    def isSeasons():
        return xbmc.getCondVisibility("Container.Content(Seasons)") or WindowShowing.isTvTunesOverrideTvShows()

    @staticmethod
    def isEpisodes():
        return xbmc.getCondVisibility("Container.Content(Episodes)") or WindowShowing.isTvTunesOverrideTvShows()

    @staticmethod
    def isMovies():
        return xbmc.getCondVisibility("Container.Content(movies)") or WindowShowing.isTvTunesOverrideMovie()

    @staticmethod
    def isScreensaver():
        return xbmc.getCondVisibility("System.ScreenSaverActive")

    @staticmethod
    def isShutdownMenu():
        return xbmc.getCondVisibility("Window.IsVisible(shutdownmenu)")

    @staticmethod
    def isTvTunesOverrideTvShows():
        win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        return win.getProperty("TvTunesSupported").lower() == "tvshows"

    @staticmethod
    def isTvTunesOverrideMovie():
        win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        return win.getProperty("TvTunesSupported").lower() == "movies"

    @staticmethod
    def isTvTunesOverrideContinuePlaying():
        # Check the home screen for the forced continue playing flag
        if xbmcgui.Window(12000).getProperty("TvTunesContinuePlaying").lower() == "true":
            # Never allow continues playing on the Home Screen
            if WindowShowing.isHome():
                # An addon may have forgotten to undet the flag, or crashed
                # force the unsetting of the flag
                log("WindowShowing: Removing TvTunesContinuePlaying property when on Home screen")
                xbmcgui.Window(12000).clearProperty("TvTunesContinuePlaying")
                return False

            # Only pay attention to the forced playing if there is actually audio playing
            if xbmc.Player().isPlayingAudio():
                return True
        return False

    # Works out if the custom window option to play the TV Theme is set
    # and we have just opened a dialog over that
    @staticmethod
    def isTvTunesOverrideContinuePrevious():
        # Check the master override that forces the existing playing theme
        if WindowShowing.isTvTunesOverrideContinuePlaying():
            return True

        if WindowShowing.isTvTunesOverrideTvShows() or WindowShowing.isTvTunesOverrideMovie():
            # Check if this is a dialog, in which case we just continue playing
            try:
                dialogid = xbmcgui.getCurrentWindowDialogId()
            except:
                dialogid = 9999
            if dialogid != 9999:
                # Is a dialog so return True
                return True
        return False

    @staticmethod
    def isRecentEpisodesAdded():
        folderPathId = "videodb://5/"
        # The ID for the Recent Episodes changed in Gotham
        if Settings.getXbmcMajorVersion() > 12:
            folderPathId = "videodb://recentlyaddedepisodes/"
        return xbmc.getInfoLabel("container.folderpath") == folderPathId

    @staticmethod
    def isTvShowTitles(currentPath=None):
        folderPathId = "videodb://2/2/"
        # The ID for the TV Show Title changed in Gotham
        if Settings.getXbmcMajorVersion() > 12:
            folderPathId = "videodb://tvshows/titles/"
        if currentPath is None:
            return xbmc.getInfoLabel("container.folderpath") == folderPathId
        else:
            return currentPath == folderPathId

    @staticmethod
    def isMusicVideoTitles(currentPath=None):
        folderPathId = "videodb://3/2/"
        # The ID for the TV Show Title changed in Gotham
        if Settings.getXbmcMajorVersion() > 12:
            folderPathId = "videodb://musicvideos/"
        if currentPath is None:
            return xbmc.getInfoLabel("container.folderpath") == folderPathId
        else:
            return currentPath == folderPathId

    @staticmethod
    def isPluginPath():
        return "plugin://" in xbmc.getInfoLabel("ListItem.Path")

    @staticmethod
    def isMovieSet():
        folderPathId = "videodb://1/7/"
        # The ID for the TV Show Title changed in Gotham
        if Settings.getXbmcMajorVersion() > 12:
            folderPathId = "videodb://movies/sets/"
        return xbmc.getCondVisibility("!IsEmpty(ListItem.DBID) + SubString(ListItem.Path," + folderPathId + ",left)")


###############################################################
# Class to make it easier to see the current state of TV Tunes
###############################################################
class TvTunesStatus():
    @staticmethod
    def isAlive():
        return xbmcgui.Window(10025).getProperty("TvTunesIsAlive") == "true"

    @staticmethod
    def setAliveState(state):
        if state:
            xbmcgui.Window(10025).setProperty("TvTunesIsAlive", "true")
        else:
            xbmcgui.Window(10025).clearProperty('TvTunesIsAlive')

    @staticmethod
    def clearRunningState():
        xbmcgui.Window(10025).clearProperty('TvTunesIsRunning')

    # Check if the is a different version running
    @staticmethod
    def isOkToRun():
        # Get the current thread ID
        curThreadId = threading.currentThread().ident
        log("TvTunesStatus: Thread ID = %d" % curThreadId)

        # Check if the "running state" is set
        existingvalue = xbmcgui.Window(10025).getProperty("TvTunesIsRunning")
        if existingvalue == "":
            log("TvTunesStatus: Current running state is empty, setting to %d" % curThreadId)
            xbmcgui.Window(10025).setProperty("TvTunesIsRunning", str(curThreadId))
        else:
            # If it is check if it is set to this thread value
            if existingvalue != str(curThreadId):
                log("TvTunesStatus: Running ID already set to %s" % existingvalue)
                return False
        # Default return True unless we have a good reason not to run
        return True


#########################################################
# Class to handle delaying the start of playing a theme
#########################################################
class DelayedStartTheme():
    def __init__(self):
        self.themesToStart = None
        self.anchorTime = 0

    def shouldStartPlaying(self, themes):
        delaySeconds = Settings.getStartDelaySeconds()

        # Check is the start playing should be delayed
        if delaySeconds < 1:
            # Start playing straight away, but check for List playing built in delay first
            return self._checkListPlayingDelay(themes)

        currentTime = int(time.time())

        if themes != self.themesToStart:
            log("DelayedStartTheme: Themes do not match, new anchor = %s" % str(currentTime))
            self.themesToStart = themes
            # Reset the current time as we need the delay from here
            self.anchorTime = currentTime
        else:
            log("DelayedStartTheme: Target time = %s current time = %s" % (str(self.anchorTime + delaySeconds), str(currentTime)))
            # Themes are the same, see if it is time to play the the theme yet
            if currentTime > (self.anchorTime + delaySeconds):
                log("DelayedStartTheme: Start playing")
                # Now we are going to start the theme, clear the values
                self.clear()
                return True
        return False

    def clear(self):
        self.themesToStart = None
        self.anchorTime = 0

    # Method to support a small delay if running on the list screen
    def _checkListPlayingDelay(self, themes):
        # Check if we are playing themes on the list view, in which case we will want to delay them
        if (Settings.isPlayMovieList() and WindowShowing.isMovies()) or (Settings.isPlayTvShowList() and WindowShowing.isTvShowTitles()) or (Settings.isPlayMusicVideoList() and WindowShowing.isMusicVideoTitles()):
            log("DelayedStartTheme: Movie List playing delay detected, anchorTime = %s" % str(self.anchorTime))
            if themes != self.themesToStart:
                # Theme selection has changed
                self.themesToStart = themes
                # Reset the current time as we need the delay from here
                self.anchorTime = 2  # for movie list delay, it is just a counter
            else:
                # reduce the anchor by one
                self.anchorTime = self.anchorTime - 1
                if self.anchorTime < 1:
                    self.clear()
                    return True
            return False

        # Default is to allow playing
        return True


###########################################
# Thread to run the program back-end in
###########################################
class TunesBackend():
    def __init__(self):
        self.themePlayer = Player()
        self._stop = False
        log("### starting TvTunes Backend ###")
        self.newThemeFiles = ThemeFiles("")
        self.oldThemeFiles = ThemeFiles("")
        self.prevThemeFiles = ThemeFiles("")
        self.delayedStart = DelayedStartTheme()

        # Only used for logging filtering
        self.lastLoggedThemePath = ""

    def run(self):
        try:
            # Before we actually start playing something, make sure it is OK
            # to run, need to ensure there are not multiple copies running
            if not TvTunesStatus.isOkToRun():
                return

            while (not self._stop):
                # Check the forced TV Tunes status at the start of the loop, if this is True
                # then we don't want to stop themes until the next iteration, this stops the case
                # where some checks are done and the value changes part was through a single
                # loop iteration
                isForcedTvTunesContinue = WindowShowing.isTvTunesOverrideContinuePlaying()

                # If shutdown is in progress, stop quickly (no fade out)
                if WindowShowing.isShutdownMenu() or xbmc.abortRequested:
                    self.stop()
                    break

                # We only stop looping and exit this script if we leave the Video library
                # We get called when we enter the library, and the only times we will end
                # will be if:
                # 1) A Video is selected to play
                # 2) We exit to the main menu away from the video view
                if (not WindowShowing.isVideoLibrary()) or WindowShowing.isScreensaver() or Settings.isTimout():
                    log("TunesBackend: Video Library no longer visible")
                    # End playing cleanly (including any fade out) and then stop everything
                    if TvTunesStatus.isAlive():
                        self.themePlayer.endPlaying()
                    self.stop()

                    # It may be possible that we stopped for the screen-saver about to kick in
                    # If we are using Gotham or higher, it is possible for us to re-kick off the
                    # screen-saver, otherwise the action of us stopping the theme will reset the
                    # timeout and the user will have to wait longer
                    if Settings.isTimout() and (Settings.getXbmcMajorVersion() > 12):
                        xbmc.executebuiltin("xbmc.ActivateScreensaver", True)
                    break

                # There is a valid page selected and there is currently nothing playing
                if self.isPlayingZone() and not WindowShowing.isTvTunesOverrideContinuePrevious():
                    newThemes = self.getThemes()
                    if self.newThemeFiles != newThemes:
                        self.newThemeFiles = newThemes

                # Check if the file path has changed, if so there is a new file to play
                if self.newThemeFiles != self.oldThemeFiles and self.newThemeFiles.hasThemes():
                    log("TunesBackend: old path: %s" % self.oldThemeFiles.getPath())
                    log("TunesBackend: new path: %s" % self.newThemeFiles.getPath())
                    if self.start_playing():
                        self.oldThemeFiles = self.newThemeFiles

                # There is no theme at this location, so make sure we are stopped
                if not self.newThemeFiles.hasThemes() and self.themePlayer.isPlayingAudio() and TvTunesStatus.isAlive():
                    self.themePlayer.endPlaying()
                    self.oldThemeFiles.clear()
                    self.prevThemeFiles.clear()
                    self.delayedStart.clear()
                    TvTunesStatus.setAliveState(False)

                # This will occur when a theme has stopped playing, maybe is is not set to loop
                if TvTunesStatus.isAlive() and not self.themePlayer.isPlayingAudio():
                    log("TunesBackend: playing ends")
                    self.themePlayer.restoreSettings()
                    TvTunesStatus.setAliveState(False)

                # This is the case where the user has moved from within an area where the themes
                # to an area where the theme is no longer played, so it will trigger a stop and
                # reset everything to highlight that nothing is playing
                # Note: TvTunes is still running in this case, just not playing a theme
                if (not self.isPlayingZone()) and (not isForcedTvTunesContinue):
                    self.newThemeFiles.clear()
                    self.oldThemeFiles.clear()
                    self.prevThemeFiles.clear()
                    self.delayedStart.clear()
                    if self.themePlayer.isPlaying() and TvTunesStatus.isAlive():
                        log("TunesBackend: end playing")
                        self.themePlayer.endPlaying()
                    TvTunesStatus.setAliveState(False)

                self.themePlayer.checkEnding()

                # Wait a little before starting the check again
                xbmc.sleep(200)
        except:
            log("TunesBackend: %s" % traceback.format_exc())
            self.stop()

    # Works out if the currently displayed area on the screen is something
    # that is deemed a zone where themes should be played
    def isPlayingZone(self):
        if WindowShowing.isTvTunesOverrideContinuePlaying():
            return True
        if WindowShowing.isRecentEpisodesAdded():
            return False
        if WindowShowing.isPluginPath():
            return False
        if WindowShowing.isMovieInformation():
            return True
        if WindowShowing.isSeasons():
            return True
        if WindowShowing.isEpisodes():
            return True
        # Only valid if wanting theme on movie list
        if WindowShowing.isMovies() and Settings.isPlayMovieList():
            return True
        # Only valid if wanting theme on TV list
        if WindowShowing.isTvShowTitles() and Settings.isPlayTvShowList():
            return True
        # Only valid if wanting theme on Music Video list
        if WindowShowing.isMusicVideoTitles() and Settings.isPlayMusicVideoList():
            return True
        # Any other area is deemed to be a non play area
        return False

    # Locates the path to look for a theme to play based on what is
    # currently being displayed on the screen
    def getThemes(self):
        themePath = ""

        # Check if the files are stored in a custom path
        if Settings.isCustomPathEnabled():
            if not WindowShowing.isMovies():
                videotitle = xbmc.getInfoLabel("ListItem.TVShowTitle")
            else:
                videotitle = xbmc.getInfoLabel("ListItem.Title")
            videotitle = normalize_string(videotitle)
            themePath = os_path_join(Settings.getCustomPath(), videotitle)

        # Looking at the TV Show information page
        elif WindowShowing.isMovieInformation() and (WindowShowing.isTvShowTitles() or WindowShowing.isTvShows()):
            themePath = xbmc.getInfoLabel("ListItem.FilenameAndPath")
        else:
            themePath = xbmc.getInfoLabel("ListItem.Path")

        # To try and reduce the amount of "noise" in the logging, where the
        # same check is logged again and again, we record if it has been
        # logged for this video, and then do not do it again until the
        # video changes and what we would print wound be different
        debug_logging_enabled = False

        # Only log if something is different from the last time we logged
        if self.lastLoggedThemePath != themePath:
            debug_logging_enabled = True
            self.lastLoggedThemePath = themePath

        log("TunesBackend: themePath = %s" % themePath, debug_logging_enabled)

        # Check if the selection is a Movie Set
        if WindowShowing.isMovieSet():
            movieSetMap = self._getMovieSetFileList()

            if Settings.isCustomPathEnabled():
                # Need to make the values part (the path) point to the custom path
                # rather than the video file
                for aKey in movieSetMap.keys():
                    videotitle = normalize_string(aKey)
                    movieSetMap[aKey] = os_path_join(Settings.getCustomPath(), videotitle)

            if len(movieSetMap) < 1:
                themefile = ThemeFiles("", debug_logging_enabled=debug_logging_enabled)
            else:
                themefile = ThemeFiles(themePath, movieSetMap.values(), debug_logging_enabled=debug_logging_enabled)

        # When the reference is into the database and not the file system
        # then don't return it
        elif themePath.startswith("videodb:"):
            # If in either the Tv Show List or the Movie list then
            # need to stop the theme is selecting the back button
            if WindowShowing.isMovies() or WindowShowing.isTvShowTitles():
                themefile = ThemeFiles("", debug_logging_enabled=debug_logging_enabled)
            else:
                # Load the previous theme
                themefile = self.newThemeFiles
        else:
            themefile = ThemeFiles(themePath, debug_logging_enabled=debug_logging_enabled)

        return themefile

    # Gets the list of movies in a movie set
    def _getMovieSetFileList(self):
        # Create a map for Program name to video file
        movieSetMap = dict()

        # Check if the selection is a Movie Set
        if WindowShowing.isMovieSet():
            # Get Movie Set Data Base ID
            dbid = xbmc.getInfoLabel("ListItem.DBID")
            # Get movies from Movie Set
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieSetDetails", "params": {"setid": %s, "properties": [ "thumbnail" ], "movies": { "properties":  [ "file", "title"], "sort": { "order": "ascending",  "method": "title" }} },"id": 1 }' % dbid)
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_query = simplejson.loads(json_query)
            if ("result" in json_query) and ('setdetails' in json_query['result']):
                # Get the list of movies paths from the movie set
                items = json_query['result']['setdetails']['movies']
                for item in items:
                    log("TunesBackend: Movie Set file (%s): %s" % (item['title'], item['file']))
                    movieSetMap[item['title']] = item['file']

        return movieSetMap

    # Returns True is started playing, False is delayed
    def start_playing(self):
        playlist = self.newThemeFiles.getThemePlaylist()

        if self.newThemeFiles.hasThemes():
            if self.newThemeFiles == self.prevThemeFiles:
                log("TunesBackend: Not playing the same files twice %s" % self.newThemeFiles.getPath())
                return True  # don't play the same tune twice (when moving from season to episodes etc)
            # Value that will force a quicker than normal fade in and out
            # this is needed if switching from one theme to the next, we
            # do not want a long pause starting and stopping
            fastFadeNeeded = False
            # Check if a theme is already playing, if there is we will need
            # to stop it before playing the new theme
            # Stop any audio playing
            if self.themePlayer.isPlayingAudio():  # and self.prevThemeFiles.hasThemes()
                fastFadeNeeded = True
                log("TunesBackend: Stopping previous theme: %s" % self.prevThemeFiles.getPath())
                self.themePlayer.endPlaying(fastFade=fastFadeNeeded)

            # Check if this should be delayed
            if not self.delayedStart.shouldStartPlaying(self.newThemeFiles):
                return False

            # Store the new theme that is being played
            self.prevThemeFiles = self.newThemeFiles
            TvTunesStatus.setAliveState(True)
            log("TunesBackend: start playing %s" % self.newThemeFiles.getPath())
            self.themePlayer.play(playlist, fastFade=fastFadeNeeded)
        else:
            log("TunesBackend: no themes found for %s" % self.newThemeFiles.getPath())
        return True

    def stop(self):
        log("TunesBackend: ### Stopping TvTunes Backend ###")
        if TvTunesStatus.isAlive() and not self.themePlayer.isPlayingVideo():
            log("TunesBackend: stop playing")
            self.themePlayer.stop()
            while self.themePlayer.isPlayingAudio():
                xbmc.sleep(50)
        TvTunesStatus.setAliveState(False)
        TvTunesStatus.clearRunningState()

        # If currently playing a video file, then we have been overridden,
        # and we need to restore all the settings, the player callbacks
        # will not be called, so just force it on stop
        self.themePlayer.restoreSettings()

        log("TunesBackend: ### Stopped TvTunes Backend ###")
        self._stop = True


#########################
# Main
#########################


# Make sure that we are not already running on another thread
# we do not want two running at the same time
if TvTunesStatus.isOkToRun():
    # Check if the video info button should be hidden, we do this here as this will be
    # called when the video info screen is loaded, it can then be read by the skin
    # when it comes to draw the button
    if Settings.hideVideoInfoButton():
        xbmcgui.Window(12003).setProperty("TvTunes_HideVideoInfoButton", "true")
    else:
        xbmcgui.Window(12003).clearProperty("TvTunes_HideVideoInfoButton")

    # Create the main class to control the theme playing
    main = TunesBackend()

    # Start the themes running
    main.run()
else:
    log("TvTunes Already Running")
