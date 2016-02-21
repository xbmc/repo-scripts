# -*- coding: utf-8 -*-
import time
import xbmc
import xbmcgui
import sys

# Add JSON support for queries
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join
from settings import normalize_string
from settings import WindowShowing

from themeFinder import ThemeFiles
from themeFinder import MusicThemeFiles
from themePlayer import ThemePlayer


#########################################################
# Class to handle delaying the start of playing a theme
#########################################################
class DelayedStartTheme():
    def __init__(self):
        self.themesToStart = None
        self.anchorTime = 0

    def shouldStartPlaying(self, themes):
        delaySeconds = Settings.getStartDelaySeconds(themes.getThemeLocations()[0])

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
# Class to run the program back-end in
###########################################
class TunesBackend():
    def __init__(self):
        self.themePlayer = ThemePlayer()
        log("### starting TvTunes Backend ###")
        self.newThemeFiles = ThemeFiles("")
        self.oldThemeFiles = ThemeFiles("")
        self.prevThemeFiles = ThemeFiles("")
        self.delayedStart = DelayedStartTheme()

        self.isAlive = False

        # Only used for logging filtering
        self.lastLoggedThemePath = ""

    def runAsAService(self):
        logVideoLibraryNotShowing = True

        while not xbmc.abortRequested:
            # Wait a little before starting the check each time
            xbmc.sleep(200)

            # Check the forced TV Tunes status at the start of the loop, if this is True
            # then we don't want to stop themes until the next iteration, this stops the case
            # where some checks are done and the value changes part was through a single
            # loop iteration
            isForcedTvTunesContinue = WindowShowing.isTvTunesOverrideContinuePlaying()

            # Stop the theme if the shutdown menu appears - it normally means
            # we are about to shut the system down, so get ahead of the game
            if WindowShowing.isShutdownMenu():
                self.stop(fastFade=True)
                continue

            # NOTE: The screensaver kicking in will only be picked up if the option
            # "Use Visualization if Playing Audio" is disabled
            if WindowShowing.isScreensaver():
                if self.isAlive:
                    log("TunesBackend: Screensaver active")
                    self.stop(fastFade=True)

                    # It may be possible that we stopped for the screen-saver about to kick in
                    # If we are using Gotham or higher, it is possible for us to re-kick off the
                    # screen-saver, otherwise the action of us stopping the theme will reset the
                    # timeout and the user will have to wait longer
                    log("TunesBackend: Restarting screensaver that TvTunes stopped")
                    xbmc.executebuiltin("ActivateScreensaver", True)
                continue

            # Check if TvTunes is blocked from playing any themes
            if xbmcgui.Window(10025).getProperty('TvTunesBlocked') not in [None, ""]:
                self.stop(fastFade=True)
                continue

            if (not WindowShowing.isVideoLibrary()) and (not WindowShowing.isMusicSection()):
                log("TunesBackend: Video Library no longer visible", logVideoLibraryNotShowing)
                logVideoLibraryNotShowing = False
                # End playing cleanly (including any fade out) and then stop everything
                self.stop()
                continue
            else:
                logVideoLibraryNotShowing = True

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
                    # Now that playing has started, update the current themes that are being used
                    self.oldThemeFiles = self.newThemeFiles

            # Check the operations where wee are currently running and we need to stop
            # playing the current theme
            if self.isAlive:
                if self.themePlayer.isPlayingTheme():
                    # There is no theme at this location, so make sure we are stopped
                    if not self.newThemeFiles.hasThemes():
                        log("TunesBackend: No themes to play for current item")
                        self.themePlayer.endPlaying()
                        self.oldThemeFiles.clear()
                        self.prevThemeFiles.clear()
                        self.delayedStart.clear()
                        self.isAlive = False
                else:
                    # This will occur when a theme has stopped playing, maybe is is not set to loop
                    # There can be a delay when playing between playlist items, so give it a little
                    # time to start playing the next one
                    themeIsStillPlaying = False
                    maxLoop = 500
                    while (maxLoop > 0) and (not themeIsStillPlaying):
                        maxLoop = maxLoop - 1
                        xbmc.sleep(1)
                        if self.themePlayer.isPlayingTheme():
                            themeIsStillPlaying = True
                            break

                    if not themeIsStillPlaying:
                        log("TunesBackend: playing ended, restoring settings")
                        self.themePlayer.restoreSettings()
                        self.isAlive = False

            # This is the case where the user has moved from within an area where the themes
            # to an area where the theme is no longer played, so it will trigger a stop and
            # reset everything to highlight that nothing is playing
            if (not self.isPlayingZone()) and (not isForcedTvTunesContinue):
                self.stop()

            # Check to see if the setting to restrict the theme duration is enabled
            # and if it is we need to stop the current theme playing
            self.themePlayer.checkEnding()

        # We have finished running, just make one last check to ensure
        # we do not need to stop any audio
        self.stop(True)
        del self.themePlayer

    # Works out if the currently displayed area on the screen is something
    # that is deemed a zone where themes should be played
    def isPlayingZone(self):
        if WindowShowing.isTvTunesOverrideContinuePlaying():
            return True
        if WindowShowing.isRecentEpisodesAdded():
            return False
        if WindowShowing.isPluginPath():
            return False
        if WindowShowing.isMovieInformation() and Settings.isPlayVideoInformation():
            return True
        if WindowShowing.isSeasons() and Settings.isPlayTvShowSeasons():
            return True
        if WindowShowing.isEpisodes() and Settings.isPlayTvShowEpisodes():
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
        if WindowShowing.isMusicSection():
            return True

        # Any other area is deemed to be a non play area
        return False

    # Locates the path to look for a theme to play based on what is
    # currently being displayed on the screen
    def getThemes(self):
        themePath = ""
        # Only need the theme path for videos
        if not WindowShowing.isMusicSection():
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
            if WindowShowing.isMusicSection():
                themefile = MusicThemeFiles(debug_logging_enabled)
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
            if self.themePlayer.isPlayingTheme():
                fastFadeNeeded = True
                log("TunesBackend: Stopping previous theme: %s" % self.prevThemeFiles.getPath())
                self.themePlayer.endPlaying(fastFade=fastFadeNeeded)

            # Check if this should be delayed
            if not self.delayedStart.shouldStartPlaying(self.newThemeFiles):
                return False

            # Before we start playing the theme, highlight that TvTunes is active by
            # Setting the property that confluence reads
            xbmcgui.Window(10025).setProperty("TvTunesIsAlive", "true")
            xbmcgui.Window(10025).setProperty("PlayingBackgroundMedia", "true")

            # Store the new theme that is being played
            self.prevThemeFiles = self.newThemeFiles
            self.isAlive = True
            log("TunesBackend: start playing %s" % self.newThemeFiles.getPath())
            self.themePlayer.play(playlist, fastFade=fastFadeNeeded)
            # Set the option so other add-ons can work out if TvTunes is playing a theme
            xbmcgui.Window(10025).setProperty("TvTunesIsRunning", "true")
        else:
            log("TunesBackend: no themes found for %s" % self.newThemeFiles.getPath())
        return True

    def stop(self, immediate=False, fastFade=False):
        if self.isAlive:
            # If video is playing, check to see if it is a theme video
            if self.themePlayer.isPlayingTheme():
                if immediate:
                    log("TunesBackend: Stop playing")
                    self.themePlayer.stop()
                    while self.themePlayer.isPlaying():
                        xbmc.sleep(50)
                else:
                    log("TunesBackend: Ending playing")
                    self.themePlayer.endPlaying(fastFade)

            self.isAlive = False

            # If currently playing a video file, then we have been overridden,
            # and we need to restore all the settings, the player callbacks
            # will not be called, so just force it on stop
            self.themePlayer.restoreSettings()

        # Clear all the values stored
        self.newThemeFiles.clear()
        self.oldThemeFiles.clear()
        self.prevThemeFiles.clear()
        self.delayedStart.clear()
        # Clear the option used by other add-ons to work out if TvTunes is playing a theme
        xbmcgui.Window(10025).clearProperty("TvTunesIsRunning")
        # The following value is added for the Confluence skin to not show what is
        # currently playing, maybe change this name when we submit the pull request to
        # Confluence - new name: PlayingBackgroundMedia
        xbmcgui.Window(10025).clearProperty("TvTunesIsAlive")
        xbmcgui.Window(10025).clearProperty("PlayingBackgroundMedia")

        # Clear the Theme Player by resetting it
        self.themePlayer = ThemePlayer()
