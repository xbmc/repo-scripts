# -*- coding: utf-8 -*-
import sys
import os
import time
import xbmc
import xbmcaddon
import xbmcgui


__addon__ = xbmcaddon.Addon(id='script.pinsentry')
__icon__ = __addon__.getAddonInfo('icon')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__lib__)

# Import the common settings
from settings import log
from settings import Settings

from numberpad import NumberPad
from database import PinSentryDB
from background import Background


# Class to handle core Pin Sentry behaviour
class PinSentry():
    pinLevelCached = 0
    pinLevelCacheExpires = -1

    @staticmethod
    def isPinSentryEnabled():
        # Check if the Pin is set, as no point prompting if it is not
        if (not Settings.isPinSet()) or (not Settings.isPinActive()):
            return False
        return True

    @staticmethod
    def clearPinCached():
        log("PinSentry: Clearing Cached pin that was at level %d" % PinSentry.pinLevelCached)
        PinSentry.pinLevelCached = 0

    @staticmethod
    def setCachedPinLevel(level):
        # Check if the pin cache is enabled, if it is not then the cache level will
        # always remain at 0 (i.e. always need to enter the pin)
        # Cache duration is set to zero if disabled
        cacheDuration = Settings.getPinCachingEnabledDuration()
        if cacheDuration != 0:
            if PinSentry.pinLevelCached < level:
                log("PinSentry: Updating cached pin level to %d" % level)
                PinSentry.pinLevelCached = level
        # Check to see if the duration expires
        if cacheDuration > 0:
            PinSentry.pinLevelCacheExpires = int(time.time()) + (cacheDuration * 60)
        else:
            PinSentry.pinLevelCacheExpires = -1

    @staticmethod
    def getCachedPinLevel():
        # Check to see if the pin was only cached for a set time
        if PinSentry.pinLevelCacheExpires > 0:
            if int(time.time()) > PinSentry.pinLevelCacheExpires:
                # The cached time has expired, so reset the security
                PinSentry.pinLevelCacheExpires = -1
                PinSentry.pinLevelCached = 0
        return PinSentry.pinLevelCached

    @staticmethod
    def promptUserForPin(requiredLevel=1):
        userHasAccess = True

        # Set the background
        background = Background.createBackground()
        if background is not None:
            background.show()

        # Prompt the user to enter the pin
        numberpad = NumberPad.createNumberPad()
        numberpad.doModal()

        # Remove the background if we had one
        if background is not None:
            background.close()
            del background

        # Get the code that the user entered
        enteredPin = numberpad.getPin()
        del numberpad

        # Find out what level this pin gives access to
        # This will be the highest level
        pinMatchLevel = Settings.getSecurityLevelForPin(enteredPin)

        # Check to see if the pin entered is correct
        if pinMatchLevel >= requiredLevel:
            log("PinSentry: Pin entered correctly for security level %d" % pinMatchLevel)
            userHasAccess = True
            # Check if we are allowed to cache the pin level
            PinSentry.setCachedPinLevel(pinMatchLevel)
        else:
            log("PinSentry: Incorrect Pin Value Entered, required level %d entered level %d" % (requiredLevel, pinMatchLevel))
            userHasAccess = False

        return userHasAccess

    @staticmethod
    def displayInvalidPinMessage(level=1):
        # Invalid Key Notification: Dialog, Popup Notification, None
        notifType = Settings.getInvalidPinNotificationType()
        if notifType == Settings.INVALID_PIN_NOTIFICATION_POPUP:
            cmd = ""
            if Settings.getNumberOfLevels() > 1:
                cmd = 'Notification("{0}", "{1} {2}", 3000, "{3}")'.format(__addon__.getLocalizedString(32104).encode('utf-8'), __addon__.getLocalizedString(32211).encode('utf-8'), str(level), __icon__)
            else:
                cmd = 'Notification("{0}", "{1}", 3000, "{2}")'.format(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(32104).encode('utf-8'), __icon__)
            xbmc.executebuiltin(cmd)
        elif notifType == Settings.INVALID_PIN_NOTIFICATION_DIALOG:
            line3 = None
            if Settings.getNumberOfLevels() > 1:
                line3 = "%s %d" % (__addon__.getLocalizedString(32211), level)
            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(32104).encode('utf-8'), line3)
        # Remaining option is to not show any error


# Class to detect when something in the system has changed
class PinSentryMonitor(xbmc.Monitor):
    def onSettingsChanged(self):
        log("PinSentryMonitor: Notification of settings change received")
        Settings.reloadSettings()

    def onScreensaverActivated(self):
        log("PinSentryMonitor: Screensaver started, clearing cached pin")
        PinSentry.clearPinCached()


# Our Monitor class so we can find out when a video file has been selected to play
class PinSentryPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)

    def onPlayBackStarted(self):
        if not Settings.isActiveVideoPlaying():
            return

        log("PinSentryPlayer: Notification that something started playing")

        # Only interested if it is not playing music
        if self.isPlayingAudio():
            return

        # Ignore screen saver videos
        if xbmcgui.Window(10000).getProperty("VideoScreensaverRunning"):
            log("PinSentryPlayer: Detected VideoScreensaver playing")
            return

        # Check if the Pin is set, as no point prompting if it is not
        if not PinSentry.isPinSentryEnabled():
            return

        isMusicVideo = False
        isTvShow = False
        # Get the information for what is currently playing
        # http://kodi.wiki/view/InfoLabels#Video_player
        title = xbmc.getInfoLabel("VideoPlayer.TVShowTitle")

        # If the TvShow Title is not set, then Check the ListItem as well
        if title in [None, ""]:
            title = xbmc.getInfoLabel("ListItem.TVShowTitle")

        securityLevel = 0
        # If it is a TvShow, then check to see if it is enabled for this one
        if title not in [None, ""]:
            isTvShow = True
            log("PinSentryPlayer: TVShowTitle: %s" % title)
            pinDB = PinSentryDB()
            securityLevel = pinDB.getTvShowSecurityLevel(title)
            del pinDB
        else:
            # Check if the video is a music video
            isMusicVideo = self.isMusicVideoPlaying()

            # Not a TvShow, so check for the Movie Title
            title = xbmc.getInfoLabel("VideoPlayer.Title")

            # If no title is found, check the ListItem rather then the Player
            if title in [None, ""]:
                title = xbmc.getInfoLabel("ListItem.Title")

            if title not in [None, ""]:
                if not isMusicVideo:
                    # Check for a Movie
                    log("PinSentryPlayer: Title: %s" % title)
                    pinDB = PinSentryDB()
                    securityLevel = pinDB.getMovieSecurityLevel(title)
                    del pinDB
                else:
                    # Now check to see if this is  music video
                    log("PinSentryPlayer: Checking Music video for: %s" % title)
                    pinDB = PinSentryDB()
                    securityLevel = pinDB.getMusicVideoSecurityLevel(title)
                    del pinDB

        # For video files it is possible to set them to always be allowed to play, in this case
        # the security value is -1 and we don't want to perform any new checking
        if securityLevel == -1:
            log("PinSentryPlayer: Security level is -1, so allowing access")
            return

        # Now perform the check that restricts if a file is in a file source
        # that should not be played
        if securityLevel < 1 and Settings.isActiveFileSource() and Settings.isActiveFileSourcePlaying():
            # Get the path of the file being played
            filePath = xbmc.getInfoLabel("Player.Folderpath")
            if filePath in [None, ""]:
                filePath = xbmc.getInfoLabel("Player.Filenameandpath")
            if filePath in [None, ""]:
                filePath = xbmc.getInfoLabel("ListItem.FolderPath")
            if filePath in [None, ""]:
                filePath = xbmc.getInfoLabel("ListItem.FileNameAndPath")
            log("PinSentryPlayer: Checking file path: %s" % filePath)

            # Get all the sources that are protected
            pinDB = PinSentryDB()
            securityDetails = pinDB.getAllFileSourcesPathsSecurity()
            del pinDB

            # Each key is in path with security applied
            for key in securityDetails.keys():
                if key in filePath:
                    securityLevel = securityDetails[key]
                    log("PinSentryPlayer: Setting path based security to %d" % securityLevel)

        # Now check to see if this item has a certificate restriction
        if securityLevel < 1:
            cert = xbmc.getInfoLabel("VideoPlayer.mpaa")
            if cert in [None, ""]:
                cert = xbmc.getInfoLabel("ListItem.Mpaa")

            if cert not in [None, ""]:
                log("PinSentryPlayer: Checking for certification restrictions: %s" % str(cert))
                # Now split based on a colon and spaces, we only want the last bit of the
                # MPAA setting as the first bit can change based on scraper
                cert = cert.strip().split(':')[-1]
                cert = cert.strip().split()[-1]
                pinDB = PinSentryDB()
                if isTvShow:
                    # Look up the TV Shows Certificate to see if it is restricted
                    securityLevel = pinDB.getTvClassificationSecurityLevel(cert)
                else:
                    # Look up the Movies Certificate to see if it is restricted
                    securityLevel = pinDB.getMovieClassificationSecurityLevel(cert)
                del pinDB

            # If we have still not set security yet, check to make sure that the classification was actually
            # one of our supported types
            if securityLevel < 1:
                if isTvShow:
                    if not Settings.isSupportedTvShowClassification(cert):
                        securityLevel = Settings.getDefaultTvShowsWithoutClassification()
                        log("PinSentryPlayer: Setting TV Show to level %d as there is no valid MPAA value" % securityLevel)
                elif not isMusicVideo:
                    if not Settings.isSupportedMovieClassification(cert):
                        securityLevel = Settings.getDefaultMoviesWithoutClassification()
                        log("PinSentryPlayer: Setting Movie to level %d as there is no valid MPAA value" % securityLevel)

            # Check if we have set security based off of the classification
            if securityLevel > 0:
                # Before we check to make sure the user can access this video based on the
                # movie or TV Show classification, check for the case where there is background
                # media playing, this can be the case if TvTunes has started a Video while browsing
                # We do not want to prompt for the user to input the key for this
                isBackgroundMedia = True
                # Total wait for not playing background media is 1 second
                loopCount = 100
                while isBackgroundMedia and (loopCount > 0):
                    loopCount = loopCount - 1
                    if xbmcgui.Window(10025).getProperty("PlayingBackgroundMedia") in [None, ""]:
                        isBackgroundMedia = False
                        break
                    xbmc.sleep(10)

                if isBackgroundMedia:
                    securityLevel = 0
                    log("PinSentryPlayer: Playing background media")

        # Check if security has been set on this item
        if securityLevel < 1:
            if title in [None, ""]:
                # Not a TvShow or Movie - so allow the user to continue
                # without entering a pin code
                log("PinSentryPlayer: No security enabled, no title available")
            else:
                log("PinSentryPlayer: No security enabled for %s" % title)
            return

        # Check if we have already cached the pin number and at which level
        if PinSentry.getCachedPinLevel() >= securityLevel:
            log("PinSentryPlayer: Already cached pin at level %d, allowing access" % PinSentry.getCachedPinLevel())
            return

        # Before we start prompting the user for the pin, check to see if we
        # have already been called and are prompting in another thread
        if xbmcgui.Window(10000).getProperty("PinSentryPrompting"):
            log("PinSentryPlayer: Already prompting for security code")
            return

        # Set the flag so other threads know we are processing this play request
        xbmcgui.Window(10000).setProperty("PinSentryPrompting", "true")

        # Pause the video so that we can prompt for the Pin to be entered
        # On some systems we could get notified that we have started playing a video
        # before it has actually been started, so keep trying to pause until we get
        # one that works
        while not xbmc.getCondVisibility("Player.Paused"):
            self.pause()

        log("PinSentryPlayer: Pausing video to check if OK to play")

        # Prompt the user for the pin, returns True if they knew it
        if PinSentry.promptUserForPin(securityLevel):
            log("PinSentryPlayer: Resuming video")
            # Pausing again will start the video playing again
            self.pause()
        else:
            log("PinSentryPlayer: Stopping video")
            self.stop()
            PinSentry.displayInvalidPinMessage(securityLevel)

        xbmcgui.Window(10000).clearProperty("PinSentryPrompting")

    # Checks if the current item is a Music Video
    def isMusicVideoPlaying(self):
        if xbmc.getInfoLabel("VideoPlayer.Album") not in [None, ""]:
            return True
        if xbmc.getInfoLabel("VideoPlayer.Artist") not in [None, ""]:
            return True
        if xbmc.getInfoLabel("ListItem.Artist") not in [None, ""]:
            return True
        if xbmc.getInfoLabel("ListItem.AlbumArtist") not in [None, ""]:
            return True
        if xbmc.getInfoLabel("ListItem.Album") not in [None, ""]:
            return True
        return False


# Class to handle prompting for a pin when navigating the menu's
class NavigationRestrictions():
    def __init__(self):
        self.lastTvShowChecked = ""
        self.lastMovieSetChecked = ""
        self.lastPluginChecked = ""
        self.canChangeSettings = False
        self.lastFileSource = ""

    # Checks if the user has navigated to a TvShow that needs a pin
    def checkTvShows(self):
        # For TV Shows Users could either be in Seasons or Episodes
        if (not xbmc.getCondVisibility("Container.Content(seasons)")) and (not xbmc.getCondVisibility("Container.Content(episodes)")):
            # Not in a TV Show view, so nothing to do, Clear any previously
            # recorded TvShow
            if 'videodb://' in xbmc.getInfoLabel("Container.FolderPath"):
                self.lastTvShowChecked = ""
            return

        # Get the name of the TvShow
        tvshow = xbmc.getInfoLabel("ListItem.TVShowTitle")

        if tvshow in [None, "", self.lastTvShowChecked]:
            # No TvShow currently set - this can take a little time
            # So do nothing this time and wait until the next time
            # or this is a TvShow that has already been checked
            return

        # If we reach here we have a TvShow that we need to check
        log("NavigationRestrictions: Checking access to view TvShow: %s" % tvshow)
        self.lastTvShowChecked = tvshow

        # Check to see if the user should have access to this show
        pinDB = PinSentryDB()
        securityLevel = pinDB.getTvShowSecurityLevel(tvshow)
        if securityLevel < 1:
            log("NavigationRestrictions: No security enabled for %s" % tvshow)
            return
        del pinDB

        # Check if we have already cached the pin number and at which level
        if PinSentry.getCachedPinLevel() >= securityLevel:
            log("NavigationRestrictions: Already cached pin at level %d, allowing access" % PinSentry.getCachedPinLevel())
            return

        # Prompt the user for the pin, returns True if they knew it
        if PinSentry.promptUserForPin(securityLevel):
            log("NavigationRestrictions: Allowed access to %s" % tvshow)
        else:
            log("NavigationRestrictions: Not allowed access to %s which has security level %d" % (tvshow, securityLevel))
            # Move back to the TvShow Section as they are not allowed where they are at the moment
            # The following does seem strange, but you can't just call the TV Show list on it's own
            # In order to get there I had to first go via the home screen
            xbmc.executebuiltin("ActivateWindow(home)", True)
            xbmc.executebuiltin("ActivateWindow(Videos,videodb://tvshows/titles/)", True)
            # Clear the previous TV Show as we will want to prompt for the pin again if the
            # user navigates there again
            self.lastTvShowChecked = ""
            PinSentry.displayInvalidPinMessage(securityLevel)

    # Checks if the user has navigated to a Movie Set that needs a pin
    def checkMovieSets(self):
        # Check if the user has navigated into a movie set
        navPath = xbmc.getInfoLabel("Container.FolderPath")

        if 'videodb://movies/sets/' not in navPath:
            # Not in a Movie Set view, so nothing to do
            if 'videodb://' in navPath:
                self.lastMovieSetChecked = ""
            return

        # Get the name of the movie set
        moveSetName = xbmc.getInfoLabel("Container.FolderName")

        if moveSetName in [None, "", self.lastMovieSetChecked]:
            # No Movie Set currently set - this can take a little time
            # So do nothing this time and wait until the next time
            # or this is a Movie set that has already been checked
            return

        # If we reach here we have a Movie Set that we need to check
        log("NavigationRestrictions: Checking access to view Movie Set: %s" % moveSetName)
        self.lastMovieSetChecked = moveSetName

        # Check to see if the user should have access to this set
        pinDB = PinSentryDB()
        securityLevel = pinDB.getMovieSetSecurityLevel(moveSetName)
        if securityLevel < 1:
            log("NavigationRestrictions: No security enabled for movie set %s" % moveSetName)
            return
        del pinDB

        # Check if we have already cached the pin number and at which level
        if PinSentry.getCachedPinLevel() >= securityLevel:
            log("NavigationRestrictions: Already cached pin at level %d, allowing access" % PinSentry.getCachedPinLevel())
            return

        # Prompt the user for the pin, returns True if they knew it
        if PinSentry.promptUserForPin(securityLevel):
            log("NavigationRestrictions: Allowed access to movie set %s" % moveSetName)
        else:
            log("NavigationRestrictions: Not allowed access to movie set %s which has security level %d" % (moveSetName, securityLevel))
            # Move back to the Movie Section as they are not allowed where they are at the moment
            xbmc.executebuiltin("ActivateWindow(Videos,videodb://movies/titles/)", True)
            # Clear the previous Movie Set as we will want to prompt for the pin again if the
            # user navigates there again
            self.lastMovieSetChecked = ""
            PinSentry.displayInvalidPinMessage(securityLevel)

    # Check if a user has navigated to a Plugin that requires a Pin
    def checkPlugins(self):
        navPath = xbmc.getInfoLabel("Container.FolderPath")
        if 'plugin://' not in navPath:
            # No Plugin currently set
            self.lastPluginChecked = ""
            return

        # Check if we are in a plugin location
        pluginName = xbmc.getInfoLabel("Container.FolderName")

        if pluginName in [None, "", self.lastPluginChecked]:
            # No Plugin currently set or this is a Plugin that has already been checked
            return

        # If we reach here we have aPlugin that we need to check
        log("NavigationRestrictions: Checking access to view Plugin: %s" % pluginName)
        self.lastPluginChecked = pluginName

        # Check for the case where the user does not want to check plugins
        # but the Pin Sentry plugin is selected, we always need to check this
        # as it is how permissions are set
        if (not Settings.isActivePlugins()) and ('PinSentry' not in pluginName):
            return

        securityLevel = 0
        # Check to see if the user should have access to this plugin
        pinDB = PinSentryDB()
        securityLevel = pinDB.getPluginSecurityLevel(pluginName)
        if securityLevel < 1:
            # Check for the special case that we are accessing ourself
            # in which case we have a minimum security level
            if 'PinSentry' in pluginName:
                securityLevel = Settings.getSettingsSecurityLevel()
            else:
                log("NavigationRestrictions: No security enabled for plugin %s" % pluginName)
                return
        del pinDB

        # Check if we have already cached the pin number and at which level
        if PinSentry.getCachedPinLevel() >= securityLevel:
            log("NavigationRestrictions: Already cached pin at level %d, allowing access" % PinSentry.getCachedPinLevel())
            return

        # Prompt the user for the pin, returns True if they knew it
        if PinSentry.promptUserForPin(securityLevel):
            log("NavigationRestrictions: Allowed access to plugin %s" % pluginName)
        else:
            log("NavigationRestrictions: Not allowed access to plugin %s which has security level %d" % (pluginName, securityLevel))
            # Move back to the Video plugin Screen as they are not allowed where they are at the moment
            xbmc.executebuiltin("ActivateWindow(Video,addons://sources/video/)", True)
            # Clear the previous plugin as we will want to prompt for the pin again if the
            # user navigates there again
            self.lastPluginChecked = ""
            PinSentry.displayInvalidPinMessage(securityLevel)

    # Checks to see if the PinSentry addons screen has been opened
    def checkSettings(self):
        # Check if we are in the Addon Information page (which can be used to disable the addon)
        # or the actual setting page
        addonSettings = xbmc.getCondVisibility("Window.IsActive(10140)")
        addonInformation = xbmc.getCondVisibility("Window.IsActive(10146)")

        if not addonSettings and not addonInformation:
            # If not looking at an info or settings page, and the time for
            # allowed edits has ended, then reset it
            if self.canChangeSettings > 0:
                # If we have reached the home page, reset the timer
                if xbmc.getCondVisibility("Window.IsVisible(home)"):
                    self.canChangeSettings = 0
                elif time.time() > self.canChangeSettings:
                    self.canChangeSettings = 0
            return

        # Check if the addon is the PinSentry addon
        addonId = xbmc.getInfoLabel("ListItem.Property(Addon.ID)")
        if 'script.pinsentry' not in addonId:
            self.canChangeSettings = 0
            return

        # If we have already allowed the user to change settings, no need to check again
        # Check if we are still in the allowed time limit to edit
        if int(time.time()) < self.canChangeSettings:
            return

        # Need to make sure this user has access to change the settings
        pinDB = PinSentryDB()
        securityLevel = pinDB.getPluginSecurityLevel('PinSentry')
        del pinDB

        if securityLevel < 1:
            # If the user hasn't reset the permissions, then set it to the highest
            # security level available
            securityLevel = Settings.getSettingsSecurityLevel()
            log("NavigationRestrictions: Settings screen requires security level %d" % securityLevel)

        # Check if we have already cached the pin number and at which level
        if PinSentry.getCachedPinLevel() >= securityLevel:
            log("NavigationRestrictions: Already cached pin at level %d, allowing access" % PinSentry.getCachedPinLevel())
            return

        # Before we prompt the user we need to close the dialog, otherwise the pin
        # dialog will appear behind it
        xbmc.executebuiltin("Dialog.Close(all, true)", True)

        # Prompt the user for the pin, returns True if they knew it
        if PinSentry.promptUserForPin(securityLevel):
            log("NavigationRestrictions: Allowed access to settings")
            # Allow the user 5 minutes to change the settings
            self.canChangeSettings = int(time.time()) + 300
            xbmcgui.Dialog().notification(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(32110).encode('utf-8'), __icon__, 3000, False)

            # Open the dialogs that should be shown, we don't reopen the Information dialog
            # as if we do the Close Dialog will not close it and the pin screen will not show correctly
            if addonSettings:
                # Open the addon settings dialog
                xbmc.executebuiltin("Addon.OpenSettings(script.pinsentry)", False)
        else:
            log("NavigationRestrictions: Not allowed access to settings which has security level %d" % securityLevel)
            self.canChangeSettings = False
            PinSentry.displayInvalidPinMessage(securityLevel)

    # Checks to see if the PinSentry addons screen has been opened
    def checkSystemSettings(self):
        # Check if the system restriction is enabled
        if not Settings.isActiveSystemSettings():
            return

        # Check to see if the main system settings has been selected
        systemSettings = xbmc.getCondVisibility("Window.IsActive(10004)")
        addonBrowser = xbmc.getCondVisibility("Window.IsActive(10040)")
        profiles = xbmc.getCondVisibility("Window.IsActive(10034)")

        # Check if we are in any of the restricted sections
        if not systemSettings and not addonBrowser and not profiles:
            log("NavigationRestrictions: Not is restricted system settings")
            return

        # If we have already allowed the user to change settings, no need to check again
        # Check if we are still in the allowed time limit to edit
        if int(time.time()) < self.canChangeSettings:
            return

        # Need to make sure this user has access to change the settings
        pinDB = PinSentryDB()
        securityLevel = pinDB.getPluginSecurityLevel('PinSentry')
        del pinDB

        if securityLevel < 1:
            # If the user hasn't reset the permissions, then set it to the highest
            # security level available
            securityLevel = Settings.getSettingsSecurityLevel()
            log("NavigationRestrictions: Settings screen requires security level %d" % securityLevel)

        # Check if we have already cached the pin number and at which level
        if PinSentry.getCachedPinLevel() >= securityLevel:
            log("NavigationRestrictions: Already cached pin at level %d, allowing access" % PinSentry.getCachedPinLevel())
            return

        # Before we prompt the user we need to close the dialog, otherwise the pin
        # dialog will appear behind it
        xbmc.executebuiltin("Dialog.Close(all, true)", True)

        # Prompt the user for the pin, returns True if they knew it
        if PinSentry.promptUserForPin(securityLevel):
            log("NavigationRestrictions: Allowed access to settings")
            # Allow the user 5 minutes to change the settings
            self.canChangeSettings = int(time.time()) + 300
            xbmcgui.Dialog().notification(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(32110).encode('utf-8'), __icon__, 3000, False)
        else:
            log("NavigationRestrictions: Not allowed access to settings which has security level %d" % securityLevel)
            self.canChangeSettings = False
            PinSentry.displayInvalidPinMessage(securityLevel)
            # Return the user to the home page as they should not be here
            xbmc.executebuiltin("ActivateWindow(home)", True)

    def checkFileSources(self):
        # Check if the user has navigated into a file source
        navPath = xbmc.getInfoLabel("Container.FolderPath")

        if navPath in [self.lastFileSource]:
            return

        if navPath in [None, ""]:
            self.lastFileSource = ""
            return

        # Skip over the internal items, quicker than doing a lookup
        if 'videodb://' in navPath:
            self.lastFileSource = ""
            return
        if 'special://' in navPath:
            self.lastFileSource = ""
            return
        if 'addons://' in navPath:
            self.lastFileSource = ""
            return
        if 'musicdb://' in navPath:
            self.lastFileSource = ""
            return

        # If we reach here we have a Movie Set that we need to check
        log("NavigationRestrictions: Checking access to view File Source: %s" % navPath)
        self.lastFileSource = navPath

        # Check to see if the user should have access to this file path
        pinDB = PinSentryDB()
        securityLevel = pinDB.getFileSourceSecurityLevelForPath(navPath)
        if securityLevel < 1:
            log("NavigationRestrictions: No security enabled for File Source %s" % navPath)
            return
        del pinDB

        # Check if we have already cached the pin number and at which level
        if PinSentry.getCachedPinLevel() >= securityLevel:
            log("NavigationRestrictions: Already cached pin at level %d, allowing access" % PinSentry.getCachedPinLevel())
            return

        # Prompt the user for the pin, returns True if they knew it
        if PinSentry.promptUserForPin(securityLevel):
            log("NavigationRestrictions: Allowed access to File Source %s" % navPath)
        else:
            log("NavigationRestrictions: Not allowed access to File Source %s which has security level %d" % (navPath, securityLevel))
            # Move back to the Movie Section as they are not allowed where they are at the moment
            xbmc.executebuiltin("ActivateWindow(Videos,sources://video/)", True)
            self.lastFileSource = ""
            PinSentry.displayInvalidPinMessage(securityLevel)

    # Checks to see if the PinSentry is being requested to be shown
    def checkForcedDisplay(self):
        # Check if the property is set
        if xbmcgui.Window(10000).getProperty("PinSentryPrompt") != 'true':
            return

        # Set the lowest security level for the forced display
        securityLevel = 1

        # Before we prompt the user we need to close the dialog, otherwise the pin
        # dialog will appear behind it
        xbmc.executebuiltin("Dialog.Close(all, true)", True)
        xbmc.executebuiltin("ActivateWindow(home)", True)

        # Prompt the user for the pin, returns True if they knew it
        if PinSentry.promptUserForPin(securityLevel):
            log("NavigationRestrictions: Forced Pin Display Unlocked")
            xbmcgui.Window(10000).clearProperty("PinSentryPrompt")
        else:
            log("NavigationRestrictions: Not allowed access after forced lock at security level %d" % securityLevel)
            # The pin dalog will be automatically re-opened as the window property has not been cleared


# Class the handle user control
class UserPinControl():
    def __init__(self):
        self.isEnabled = False
        self.userId = None
        self.allowedStartTime = 0
        self.allowedEndTime = 2439  # Number of minutes in a day
        self.usedViewingLimit = 0
        self.startedViewing = 0
        self.screensaverStart = 0
        self.warningDisplayed = False

    def startupCheck(self):
        # When the system starts up we need to check to see if User restriction is enabled
        if Settings.getNumberOfLimitedUsers() < 1:
            log("UserPinControl: No Limited users configured")
            self.isEnabled = False
            return

        self.isEnabled = True

        # Set the background
        background = Background.createBackground()
        if background is not None:
            background.show()

        preventAccess = False
        tryAgain = True
        while tryAgain:
            tryAgain = False
            # Need to find out which user this is, so prompt them for a pin
            numberpad = NumberPad.createNumberPad()
            numberpad.doModal()

            # Get the code that the user entered
            enteredPin = numberpad.getPin()
            del numberpad

            # Find out which user owns this pin
            self.userId = Settings.getUserForPin(enteredPin)

            # Check for the unrestricted user
            if self.userId == "unrestrictedUserPin":
                log("UserPinControl: Unrestricted user pin entered")
                self.isEnabled = False
                break

            if self.userId in [None, ""]:
                log("UserPinControl: Unknown pin entered, offering retry")
                # This is not a valid user, so display the error message and work out
                # if we should prompt the user again or shutdown the system
                tryAgain = xbmcgui.Dialog().yesno(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(32104).encode('utf-8'), __addon__.getLocalizedString(32129).encode('utf-8'))

                if not tryAgain:
                    # Need to stop this user accessing the system
                    preventAccess = True

        # Remove the background if we had one
        if background is not None:
            background.close()
            del background

        if preventAccess:
            log("UserPinControl: Shutting down as unknown user pin entered")
            self.shutdown()
        elif self.isEnabled:
            log("UserPinControl: User logged in is %s" % self.userId)
            # Load the settings for this user
            self.allowedStartTime, displayStartTime = Settings.getUserStartTime(self.userId)
            self.allowedEndTime, displayEndTime = Settings.getUserEndTime(self.userId)
            self.usedViewingLimit = Settings.getUserViewingUsedTime(self.userId)

            self.displaySummary()

            # Now we can record when this user started viewing in this session
            localTime = time.localtime()
            self.startedViewing = (localTime.tm_hour * 60) + localTime.tm_min

            # We actually want to also record how many minutes have already been viewed in previous
            # sessions, so roll the clock back by that much
            self.startedViewing = self.startedViewing - self.usedViewingLimit

            log("UserPinControl: Time already used for user is %d" % self.usedViewingLimit)

            # Record that we are running as a restricted user so that the default script
            # can display the status of how long is left when it is selected
            xbmcgui.Window(10000).setProperty("PinSentry_RestrictedUser", self.userId)

    def checkDisplayStatus(self):
        # This method will display the current time remaining if the property is set
        # by the script being run as a program
        if xbmcgui.Window(10000).getProperty("PinSentry_DisplayStatus") not in ["", None]:
            xbmcgui.Window(10000).clearProperty("PinSentry_DisplayStatus")
            self.displaySummary()

    def displaySummary(self):
        # Load the settings for this user
        allowedStartTime, displayStartTime = Settings.getUserStartTime(self.userId)
        allowedEndTime, displayEndTime = Settings.getUserEndTime(self.userId)
        viewingLimit = Settings.getUserViewingLimit(self.userId)
        usersName = Settings.getUserName(self.userId)

        # Work out how much time is remaining
        displayRemainingTime = viewingLimit - self.usedViewingLimit
        if displayRemainingTime < 0:
            displayRemainingTime = 0

        # Do a notification to let the user know how long they have left today
        summaryUserName = "%s:    %s" % (__addon__.getLocalizedString(32035), usersName)
        summaryLimit = "%s:    %d" % (__addon__.getLocalizedString(32033), viewingLimit)
        summaryLimitRemaining = "%s:    %d" % (__addon__.getLocalizedString(32131), displayRemainingTime)
        summaryAccess = "%s:    %s - %s" % (__addon__.getLocalizedString(32132), displayStartTime, displayEndTime)
        fullSummary = "%s\n%s\n%s\n%s" % (summaryUserName, summaryLimit, summaryLimitRemaining, summaryAccess)
        xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001).encode('utf-8'), fullSummary)

    # Check the current user access status
    def check(self):
        # If we have found the correct user, then we need to ensure we are
        # in the valid time duration and have not exceeded the limit
        if not self.isEnabled:
            return True
        # Check for the case where we didn't get the user ID - this means we are
        # already shutting down
        if self.userId in [None, ""]:
            return False

        log("UserPinControl: Performing check for user %s" % self.userId)

        # First check that the current time is within the allowed boundaries
        localTime = time.localtime()
        currentTime = (localTime.tm_hour * 60) + localTime.tm_min

        if self.allowedStartTime > currentTime or self.allowedEndTime < currentTime:
            log("UserPinControl: User not allowed access until %d to %d currently %d" % (self.allowedStartTime, self.allowedEndTime, currentTime))
            self.shutdown(32130)
            return False

        # Check if the screensaver is running, if so we need to make sure we do not
        # class that as time used by the user
        if xbmc.getCondVisibility("System.ScreenSaverActive"):
            if self.screensaverStart < 1:
                self.screensaverStart = currentTime
        else:
            # Not the screensaver, check to see if this is the first check
            # after the screensaver stopped
            if self.screensaverStart > 0:
                screensaverDuration = currentTime - self.screensaverStart
                self.screensaverStart = 0
                log("UserPinControl: Updating duration for screensaver, %d minutes" % screensaverDuration)
                # Now we roll the time forward that we started viewing so that
                # we are not counting the screensaver
                self.startedViewing = self.startedViewing + screensaverDuration

            # Check to see if we need to update the record for how long the user has already been viewing
            viewingLimit = Settings.getUserViewingLimit(self.userId)
            self.usedViewingLimit = currentTime - self.startedViewing
            log("UserPinControl: Time used by user is %d" % self.usedViewingLimit)

            # Update the settings record for how much this user has viewed so far
            Settings.setUserViewingUsedTime(self.userId, self.usedViewingLimit)

            # Now check to see if the user has exceeded their limit
            if self.usedViewingLimit >= viewingLimit:
                self.shutdown(32133)
                return False

            # Check if we need to warn the user that the time is running out
            warningTime = Settings.getWarnExpiringTime()
            if (not self.warningDisplayed) and ((self.usedViewingLimit + warningTime) >= viewingLimit):
                self.warningDisplayed = True
                # Calculate the time left
                remainingTime = viewingLimit - self.usedViewingLimit
                msg = "%d %s" % (remainingTime, __addon__.getLocalizedString(32134))
                xbmcgui.Dialog().notification(__addon__.getLocalizedString(32001).encode('utf-8'), msg, __icon__, 3000, False)

        return True

    def shutdown(self, reason=0):
        # Check to see if anything is playing
        if xbmc.Player().isPlaying():
            # Stop what is playing as we are going to be exiting
            xbmc.Player().stop()

        # Make sure there are no dialogs being displayed
        xbmc.executebuiltin("Dialog.Close(all, true)", True)

        # Display a notification to let the user know why we are about to shut down
        if reason > 0:
            cmd = 'Notification("{0}", "{1}", 3000, "{2}")'.format(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(reason).encode('utf-8'), __icon__)
            xbmc.executebuiltin(cmd)

        # Give the user time to see why we are shutting down
        waitTime = 35
        while (waitTime > 0) and (not xbmc.abortRequested):
            xbmc.sleep(100)
            waitTime = waitTime - 1

        # Using ShutDown will perform the default behaviour that Kodi has in the system settings
        xbmc.executebuiltin("ShutDown")


##################################
# Main of the PinSentry Service
##################################
if __name__ == '__main__':
    log("Starting Pin Sentry Service %s" % __addon__.getAddonInfo('version'))

    # Tidy up any old pins and set any warnings when we first start
    Settings.checkPinSettings()

    # Make sure that the database exists if this is the first time
    pinDB = PinSentryDB()
    pinDB.createOrUpdateDB()
    del pinDB

    # Check to see if we need to restrict based on a given user to ensure they
    # are allowed to use the system
    userCtrl = UserPinControl()
    userCtrl.startupCheck()

    playerMonitor = PinSentryPlayer()
    systemMonitor = PinSentryMonitor()
    navRestrictions = NavigationRestrictions()

    # Check if we need to prompt for the pin when the system starts
    if Settings.isPromptForPinOnStartup():
        log("PinSentry: Prompting for pin on startup")
        xbmcgui.Window(10000).setProperty("PinSentryPrompt", "true")

    loopsUntilUserControlCheck = 0
    while (not xbmc.abortRequested):
        # No need to perform the user control check every fraction of a second
        # about every minute will be OK
        if loopsUntilUserControlCheck < 1:
            # If we are going to shut down then start closing down this script
            if not userCtrl.check():
                break
            loopsUntilUserControlCheck = 600
        else:
            loopsUntilUserControlCheck = loopsUntilUserControlCheck - 1

        xbmc.sleep(100)
        userCtrl.checkDisplayStatus()

        # Check if the Pin is set, as no point prompting if it is not
        if PinSentry.isPinSentryEnabled():
            # Check to see if we need to restrict navigation access
            if Settings.isActiveNavigation():
                navRestrictions.checkTvShows()
                navRestrictions.checkMovieSets()
                if Settings.isActiveFileSource():
                    navRestrictions.checkFileSources()
            # Always call the plugin check as we have to check if the user is setting
            # permissions using the PinSentry plugin
            navRestrictions.checkPlugins()
            navRestrictions.checkSettings()
            navRestrictions.checkSystemSettings()
            # Check if the dialog is being forced to display
            navRestrictions.checkForcedDisplay()

    log("Stopping Pin Sentry Service")
    del userCtrl
    del navRestrictions
    del playerMonitor
    del systemMonitor
