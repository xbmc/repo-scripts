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


# Feature Options:
# Different Pins for different priorities (one a subset of the next)
# Option to have different passwords without the numbers (Remote with no numbers?)
# Cleanup database of removed library items (when screensaver starts)


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
    def promptUserForPin():
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

        # Check to see if the pin entered is correct
        if Settings.isPinCorrect(enteredPin):
            log("PinSentry: Pin entered Correctly")
            userHasAccess = True
            # Check if we are allowed to cache the pin level
            PinSentry.setCachedPinLevel(1)
        else:
            log("PinSentry: Incorrect Pin Value Entered")
            userHasAccess = False

        return userHasAccess

    @staticmethod
    def displayInvalidPinMessage():
        # Invalid Key Notification: Dialog, Popup Notification, None
        notifType = Settings.getInvalidPinNotificationType()
        if notifType == Settings.INVALID_PIN_NOTIFICATION_POPUP:
            cmd = 'XBMC.Notification("{0}", "{1}", 5, "{2}")'.format(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(32104).encode('utf-8'), __icon__)
            xbmc.executebuiltin(cmd)
        elif notifType == Settings.INVALID_PIN_NOTIFICATION_DIALOG:
            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(32104).encode('utf-8'))
        # Remaining option is to not show any error


# Class to detect shen something in the system has changed
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
            # Not a TvShow, so check for the Movie Title
            title = xbmc.getInfoLabel("VideoPlayer.Title")

            # If no title is found, check the ListItem rather then the Player
            if title in [None, ""]:
                title = xbmc.getInfoLabel("ListItem.Title")

            if title not in [None, ""]:
                log("PinSentryPlayer: Title: %s" % title)
                pinDB = PinSentryDB()
                securityLevel = pinDB.getMovieSecurityLevel(title)
                del pinDB

                # If no security found for the Movie - check the Music Video
                if securityLevel < 1:
                    # Now check to see if this is  music video
                    log("PinSentryPlayer: Checking Music video for: %s" % title)
                    pinDB = PinSentryDB()
                    securityLevel = pinDB.getMusicVideoSecurityLevel(title)
                    del pinDB

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
                cert = cert.replace('Rated ', '', 1).strip()
                pinDB = PinSentryDB()
                if isTvShow:
                    # Look up the TV Shows Certificate to see if it is restricted
                    securityLevel = pinDB.getTvClassificationSecurityLevel(cert)
                else:
                    # Look up the Movies Certificate to see if it is restricted
                    securityLevel = pinDB.getMovieClassificationSecurityLevel(cert)
                del pinDB

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
        if PinSentry.promptUserForPin():
            log("PinSentryPlayer: Resuming video")
            # Pausing again will start the video playing again
            self.pause()
        else:
            log("PinSentryPlayer: Stopping video")
            self.stop()
            PinSentry.displayInvalidPinMessage()

        xbmcgui.Window(10000).clearProperty("PinSentryPrompting")


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
        if PinSentry.promptUserForPin():
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
            PinSentry.displayInvalidPinMessage()

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
        if PinSentry.promptUserForPin():
            log("NavigationRestrictions: Allowed access to movie set %s" % moveSetName)
        else:
            log("NavigationRestrictions: Not allowed access to movie set %s which has security level %d" % (moveSetName, securityLevel))
            # Move back to the Movie Section as they are not allowed where they are at the moment
            xbmc.executebuiltin("ActivateWindow(Videos,videodb://movies/titles/)", True)
            # Clear the previous Movie Set as we will want to prompt for the pin again if the
            # user navigates there again
            self.lastMovieSetChecked = ""
            PinSentry.displayInvalidPinMessage()

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
                securityLevel = 1
            else:
                log("NavigationRestrictions: No security enabled for plugin %s" % pluginName)
                return
        del pinDB

        # Check if we have already cached the pin number and at which level
        if PinSentry.getCachedPinLevel() >= securityLevel:
            log("NavigationRestrictions: Already cached pin at level %d, allowing access" % PinSentry.getCachedPinLevel())
            return

        # Prompt the user for the pin, returns True if they knew it
        if PinSentry.promptUserForPin():
            log("NavigationRestrictions: Allowed access to plugin %s" % pluginName)
        else:
            log("NavigationRestrictions: Not allowed access to plugin %s which has security level %d" % (pluginName, securityLevel))
            # Move back to the Video plugin Screen as they are not allowed where they are at the moment
            xbmc.executebuiltin("ActivateWindow(Video,addons://sources/video/)", True)
            # Clear the previous plugin as we will want to prompt for the pin again if the
            # user navigates there again
            self.lastPluginChecked = ""
            PinSentry.displayInvalidPinMessage()

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
            securityLevel = 1

        # Check if we have already cached the pin number and at which level
        if PinSentry.getCachedPinLevel() >= securityLevel:
            log("NavigationRestrictions: Already cached pin at level %d, allowing access" % PinSentry.getCachedPinLevel())
            return

        # Before we prompt the user we need to close the dialog, otherwise the pin
        # dialog will appear behind it
        xbmc.executebuiltin("Dialog.Close(all, true)", True)

        # Prompt the user for the pin, returns True if they knew it
        if PinSentry.promptUserForPin():
            log("NavigationRestrictions: Allowed access to settings")
            # Allow the user 5 minutes to change the settings
            self.canChangeSettings = int(time.time()) + 300

            cmd = 'XBMC.Notification("{0}", "{1}", 10, "{2}")'.format(__addon__.getLocalizedString(32001).encode('utf-8'), __addon__.getLocalizedString(32110).encode('utf-8'), __icon__)
            xbmc.executebuiltin(cmd)

            # Open the dialogs that should be shown, we don't reopen the Information dialog
            # as if we do the Close Dialog will not close it and the pin screen will not show correctly
            if addonSettings:
                # Open the addon settings dialog
                xbmc.executebuiltin("Addon.OpenSettings(script.pinsentry)", False)
        else:
            log("NavigationRestrictions: Not allowed access to settings which has security level %d" % securityLevel)
            self.canChangeSettings = False
            PinSentry.displayInvalidPinMessage()

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
        if PinSentry.promptUserForPin():
            log("NavigationRestrictions: Allowed access to File Source %s" % navPath)
        else:
            log("NavigationRestrictions: Not allowed access to File Source %s which has security level %d" % (navPath, securityLevel))
            # Move back to the Movie Section as they are not allowed where they are at the moment
            xbmc.executebuiltin("ActivateWindow(Videos,sources://video/)", True)
            self.lastFileSource = ""
            PinSentry.displayInvalidPinMessage()


##################################
# Main of the PinSentry Service
##################################
if __name__ == '__main__':
    log("Starting Pin Sentry Service")

    # Make sure that the database exists if this is the first time
    pinDB = PinSentryDB()
    pinDB.createOrUpdateDB()
    del pinDB

    playerMonitor = PinSentryPlayer()
    systemMonitor = PinSentryMonitor()
    navRestrictions = NavigationRestrictions()

    while (not xbmc.abortRequested):
        xbmc.sleep(100)
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

    log("Stopping Pin Sentry Service")
    del navRestrictions
    del playerMonitor
    del systemMonitor
