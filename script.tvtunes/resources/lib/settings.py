# -*- coding: utf-8 -*-
import os
import unicodedata
import uuid
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui

__addon__ = xbmcaddon.Addon(id='script.tvtunes')
__addonid__ = __addon__.getAddonInfo('id')


# Common logging module
def log(txt, debug_logging_enabled=True, loglevel=xbmc.LOGDEBUG):
    if ((__addon__.getSetting("logEnabled") == "true") and debug_logging_enabled) or (loglevel != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode("utf-8"), level=loglevel)


def normalize_string(text):
    try:
        text = text.replace(":", "")
        text = text.replace("/", "-")
        text = text.replace("\\", "-")
        text = text.replace("<", "")
        text = text.replace(">", "")
        text = text.replace("*", "")
        text = text.replace("?", "")
        text = text.replace('|', "")
        text = text.strip()
        # Remove dots from the last character as windows can not have directories
        # with dots at the end
        text = text.rstrip('.')
        text = unicodedata.normalize('NFKD', unicode(text, 'utf-8')).encode('ascii', 'ignore')
    except:
        pass
    return text


# There has been problems with calling join with non ascii characters,
# so we have this method to try and do the conversion for us
def os_path_join(dir, file):
    # Check if it ends in a slash
    if dir.endswith("/") or dir.endswith("\\"):
        # Remove the slash character
        dir = dir[:-1]

    # Convert each argument - if an error, then it will use the default value
    # that was passed in
    try:
        dir = dir.decode("utf-8")
    except:
        pass
    try:
        file = file.decode("utf-8")
    except:
        pass
    return os.path.join(dir, file)


# There has been problems with calling isfile with non ascii characters,
# so we have this method to try and do the conversion for us
def os_path_isfile(workingPath,):
    # Convert each argument - if an error, then it will use the default value
    # that was passed in
    try:
        workingPath = workingPath.decode("utf-8")
    except:
        pass
    try:
        return os.path.isfile(workingPath)
    except:
        return False


# Splits a path the same way as os.path.split but supports paths of a different
# OS than that being run on
def os_path_split(fullpath):
    # Check if it ends in a slash
    if fullpath.endswith("/") or fullpath.endswith("\\"):
        # Remove the slash character
        fullpath = fullpath[:-1]

    try:
        slash1 = fullpath.rindex("/")
    except:
        slash1 = -1

    try:
        slash2 = fullpath.rindex("\\")
    except:
        slash2 = -1

    # Parse based on the last type of slash in the string
    if slash1 > slash2:
        return fullpath.rsplit("/", 1)

    return fullpath.rsplit("\\", 1)


# Get the contents of the directory
def list_dir(dirpath):
    # There is a problem with the afp protocol that means if a directory not ending
    # in a / is given, an error happens as it just appends the filename to the end
    # without actually checking there is a directory end character
    #    http://forum.xbmc.org/showthread.php?tid=192255&pid=1681373#pid1681373
    if dirpath.startswith('afp://') and (not dirpath.endswith('/')):
        dirpath = os_path_join(dirpath, '/')
    return xbmcvfs.listdir(dirpath)


# Checks if a directory exists (Do not use for files)
def dir_exists(dirpath):
    # There is an issue with password protected smb shares, in that they seem to
    # always return false for a directory exists call, so if we have a smb with
    # a password and user name, then we return true
    if Settings.isSmbEnabled() and ('@' in dirpath):
        return True

    directoryPath = dirpath
    # The xbmcvfs exists interface require that directories end in a slash
    # It used to be OK not to have the slash in Gotham, but it is now required
    if (not directoryPath.endswith("/")) and (not directoryPath.endswith("\\")):
        dirSep = "/"
        if "\\" in directoryPath:
            dirSep = "\\"
        directoryPath = "%s%s" % (directoryPath, dirSep)
    return xbmcvfs.exists(directoryPath)


################################################################
# Class to make it easier to see which screen is being displayed
################################################################
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
    def isMusicSection():
        inMusicSection = False
        # Only record being in the music section if we have it enabled in the settings
        if Settings.isPlayMusicList():
            if xbmc.getCondVisibility("Container.Content(albums)"):
                inMusicSection = True
            elif xbmc.getCondVisibility("Container.Content(artists)"):
                inMusicSection = True
        return inMusicSection

    @staticmethod
    def isTvTunesOverrideTvShows():
        isOverride = False
        try:
            # If there is a problem with a skin where there is no current window Id, avoid the exception
            win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
            if win.getProperty("TvTunesSupported").lower() == "tvshows":
                isOverride = True
        except:
            isOverride = False

        return isOverride

    @staticmethod
    def isTvTunesOverrideMovie():
        isOverride = False
        try:
            # If there is a problem with a skin where there is no current window Id, avoid the exception
            win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
            if win.getProperty("TvTunesSupported").lower() == "movies":
                isOverride = True
        except:
            isOverride = False

        return isOverride

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

            # Only pay attention to the forced playing if there is actually media playing
            if xbmc.Player().isPlaying():
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
        return xbmc.getInfoLabel("container.folderpath") == "videodb://recentlyaddedepisodes/"

    @staticmethod
    def isTvShowTitles():
        showingTvShowTitles = (xbmc.getInfoLabel("container.folderpath") == "videodb://tvshows/titles/")
        # There is a case where the user may have created a smart playlist that then
        # groups together all the TV Shows, if they also have the option to play themes
        # while browsing TV Shows enabled, then we need to return True for this case
        if not showingTvShowTitles:
            # Check if we are viewing a video playlist
            if 'special://profile/playlists/video/' in xbmc.getInfoLabel("container.folderpath"):
                # Check if what is being showed is actually TV Shows
                showingTvShowTitles = WindowShowing.isTvShows()
        return showingTvShowTitles

    @staticmethod
    def isMusicVideoTitles():
        return xbmc.getInfoLabel("container.folderpath") == "videodb://musicvideos/"

    @staticmethod
    def isPluginPath():
        currentPath = xbmc.getInfoLabel("ListItem.Path")
        if "plugin://" in currentPath:
            # There is a special case for Emby.Kodi that supports TvTunes
            # https://github.com/MediaBrowser/Emby.Kodi
            # So we pretend that isn't a plugin as long as Custom Path is set
            if ("plugin.video.emby" in currentPath) and Settings.isCustomPathEnabled():
                return False
            return True
        return False

    @staticmethod
    def isMovieSet():
        folderPathId = "videodb://movies/sets/"
        return xbmc.getCondVisibility("!IsEmpty(ListItem.DBID) + SubString(ListItem.Path," + folderPathId + ",left)")

    @staticmethod
    def updateHideVideoInfoButton():
        if Settings.hideVideoInfoButton():
            xbmcgui.Window(12003).setProperty("TvTunes_HideVideoInfoButton", "true")
        else:
            xbmcgui.Window(12003).clearProperty("TvTunes_HideVideoInfoButton")

    @staticmethod
    def updateShowOnContextMenu():
        if Settings.showOnContextMenu():
            xbmcgui.Window(10000).setProperty("TvTunes_ShowContextMenu", "true")
        else:
            xbmcgui.Window(10000).clearProperty("TvTunes_ShowContextMenu")


##############################
# Stores Various Settings
##############################
class Settings():
    ALL_ENGINES = 'All'
    TELEVISION_TUNES = 'televisiontunes.com'
    SOUNDCLOUD = 'soundcloud.com'
    GOEAR = 'goear.com'
    THEMELIBRARY = 'themelibrary'
    PLEXLIBRARY = 'plexlibrary'
    PROMPT_ENGINE = 'Prompt User'

    # Settings for Automatically Downloading
    AUTO_DOWNLOAD_SINGLE_ITEM = 1
    AUTO_DOWNLOAD_PRIORITY_1 = 2
    AUTO_DOWNLOAD_PRIORITY_1_OR_2 = 2

    @staticmethod
    def reloadSettings():
        # Force the reload of the settings to pick up any new values
        global __addon__
        __addon__ = xbmcaddon.Addon(id='script.tvtunes')
        # The user may have change the display settings to show or hide the info button
        # so make sure we update it
        WindowShowing.updateHideVideoInfoButton()
        WindowShowing.updateShowOnContextMenu()

    # Checks if the given file is names as a video file
    @staticmethod
    def isVideoFile(filename):
        if filename in [None, ""]:
            return False
        if filename.lower().endswith('.mp4'):
            return True
        if filename.lower().endswith('.mkv'):
            return True
        if filename.lower().endswith('.avi'):
            return True
        if filename.lower().endswith('.mov'):
            return True
        if filename.lower().endswith('.m2ts'):
            return True
        return False

    @staticmethod
    def isThemePlayingEnabled():
        return __addon__.getSetting("enableThemePlaying") == 'true'

    @staticmethod
    def isCustomPathEnabled():
        return __addon__.getSetting("custom_path_enable") == 'true'

    @staticmethod
    def getCustomPath():
        return __addon__.getSetting("custom_path").decode("utf-8")

    @staticmethod
    def getThemeVolume():
        return int(float(__addon__.getSetting("volume")))

    @staticmethod
    def isLoop():
        return __addon__.getSetting("loop") == 'true'

    @staticmethod
    def isFadeOut():
        return __addon__.getSetting("fadeOut") == 'true'

    @staticmethod
    def isFadeIn():
        return __addon__.getSetting("fadeIn") == 'true'

    @staticmethod
    def isSmbEnabled():
        return __addon__.getSetting("smb_share") == 'true'

    @staticmethod
    def getSmbUser():
        if __addon__.getSetting("smb_login"):
            return __addon__.getSetting("smb_login")
        else:
            return "guest"

    @staticmethod
    def getSmbPassword():
        if __addon__.getSetting("smb_psw"):
            return __addon__.getSetting("smb_psw")
        else:
            return "guest"

    # Calculates the regular expression to use to search for theme files
    @staticmethod
    def getThemeFileRegEx(searchDir=None, extensionOnly=False, audioOnly=False, videoOnly=False):
        fileTypes = ""
        if not videoOnly:
            fileTypes = "mp3"  # mp3 is the default that is always supported
            if(__addon__.getSetting("wma") == 'true'):
                fileTypes = fileTypes + "|wma"
            if(__addon__.getSetting("flac") == 'true'):
                fileTypes = fileTypes + "|flac"
            if(__addon__.getSetting("m4a") == 'true'):
                fileTypes = fileTypes + "|m4a"
            if(__addon__.getSetting("wav") == 'true'):
                fileTypes = fileTypes + "|wav"
            if(__addon__.getSetting("wav") == 'true'):
                fileTypes = fileTypes + "|wav"
        if not audioOnly:
            videoFileTypes = Settings.getVideoThemeFileExtensions()
            if videoFileTypes not in [None, ""]:
                if len(fileTypes) > 0:
                    fileTypes = fileTypes + '|'
                fileTypes = fileTypes + videoFileTypes
        themeRegEx = '(theme[ _A-Za-z0-9.-]*.(' + fileTypes + ')$)'
        # If using the directory method then remove the requirement to have "theme" in the name
        if (searchDir is not None) and Settings.isThemeDirEnabled():
            # Make sure this is checking the theme directory, not it's parent
            if searchDir.endswith(Settings.getThemeDirectory()):
                extensionOnly = True
        # See if we do not want the theme keyword
        if extensionOnly:
            themeRegEx = '(.(' + fileTypes + ')$)'
        return themeRegEx

    @staticmethod
    def getVideoThemeFileExtensions():
        fileTypes = []
        if(__addon__.getSetting("mp4") == 'true'):
            fileTypes.append("mp4")
        if(__addon__.getSetting("mkv") == 'true'):
            fileTypes.append("mkv")
        if(__addon__.getSetting("avi") == 'true'):
            fileTypes.append("avi")
        if(__addon__.getSetting("mov") == 'true'):
            fileTypes.append("mov")
        if(__addon__.getSetting("m2ts") == 'true'):
            fileTypes.append("m2ts")
        return '|'.join(fileTypes)

    @staticmethod
    def isShuffleThemes():
        return __addon__.getSetting("shuffle") == 'true'

    @staticmethod
    def isRandomStart():
        return __addon__.getSetting("random") == 'true'

    @staticmethod
    def isPlayMovieList():
        return __addon__.getSetting("movielist") == 'true'

    @staticmethod
    def isPlayTvShowList():
        return __addon__.getSetting("tvlist") == 'true'

    @staticmethod
    def isPlayMusicVideoList():
        return __addon__.getSetting("musicvideolist") == 'true'

    @staticmethod
    def isPlayVideoInformation():
        return __addon__.getSetting("videoInformation") == 'true'

    @staticmethod
    def isPlayTvShowSeasons():
        return __addon__.getSetting("tvShowSeasons") == 'true'

    @staticmethod
    def isPlayTvShowEpisodes():
        return __addon__.getSetting("tvShowEpisodes") == 'true'

    @staticmethod
    def isPlayMusicList():
        return __addon__.getSetting("musiclist") == 'true'

    @staticmethod
    def getPlayDurationLimit():
        return int(float(__addon__.getSetting("endafter")))

    @staticmethod
    def getTrackLengthLimit():
        return int(float(__addon__.getSetting("trackLengthLimit")))

    # Check if the video info button should be hidden
    @staticmethod
    def hideVideoInfoButton():
        return __addon__.getSetting("showVideoInfoButton") != 'true'

    # Check the delay start value
    @staticmethod
    def getStartDelaySeconds(themeFile=None):
        # check if this is a video file as the delay may be different
        if Settings.isVideoFile(themeFile):
            return int(float(__addon__.getSetting("delayVideoStart")))
        return int(float(__addon__.getSetting("delayStart")))

    @staticmethod
    def isThemeDirEnabled():
        # Theme sub directory only supported when not using a custom path
        if Settings.isCustomPathEnabled():
            return False
        return __addon__.getSetting("searchSubDir") == 'true'

    @staticmethod
    def getThemeDirectory():
        # Load the information about storing themes in sub-directories
        # Only use the Theme dir if custom path is not used
        return __addon__.getSetting("subDirName")

    @staticmethod
    def getAutoDownloadSetting():
        return int(__addon__.getSetting("auto_download"))

    @staticmethod
    def isAutoDownloadPromptUser():
        # If no auto select is set, then always prompt the user
        if Settings.getAutoDownloadSetting() == 0:
            return True
        return __addon__.getSetting("auto_prompt_user_if_required") == 'true'

    @staticmethod
    def isMultiThemesSupported():
        return __addon__.getSetting("multiThemeDownload") == 'true'

    @staticmethod
    def getSearchEngine():
        index = int(__addon__.getSetting("searchSource"))
        if index == 0:
            return Settings.ALL_ENGINES
        elif index == 1:
            return Settings.TELEVISION_TUNES
        elif index == 2:
            return Settings.SOUNDCLOUD
        elif index == 3:
            return Settings.GOEAR
        elif index == 4:
            return Settings.THEMELIBRARY
        elif index == 5:
            return Settings.PLEXLIBRARY

        # Default is to prompt the user
        return Settings.PROMPT_ENGINE

    @staticmethod
    def getStartupVolume():
        # Check to see if the volume needs to be changed when the system starts
        if __addon__.getSetting("resetVolumeOnStartup") == 'true':
            return int(float(__addon__.getSetting("resetStartupVolumeValue")))
        return -1

    @staticmethod
    def isVideoThemesOnlyIfOneExists():
        index = int(__addon__.getSetting("playVideoThemeRules"))
        if index == 2:
            return True
        return False

    @staticmethod
    def isVideoThemesFirst():
        index = int(__addon__.getSetting("playVideoThemeRules"))
        if index == 1:
            return True
        return False

    @staticmethod
    def onlyPlaySingleTheme():
        return __addon__.getSetting("singleThemeOnly") == 'true'

    @staticmethod
    def isRepeatSingleAudioAfterVideo():
        if __addon__.getSetting("repeatSingleAudioAfterVideo") == 'true':
            if Settings.isVideoThemesFirst():
                return True
        return False

    @staticmethod
    def showOnContextMenu():
        return __addon__.getSetting("showOnContextMenu") == "true"

    @staticmethod
    def blockRefreshRateChange():
        return __addon__.getSetting("blockChangeInRefreshRate") == "true"

    @staticmethod
    def isUploadEnabled():
        return __addon__.getSetting("enableUploads") == "true"

    @staticmethod
    def getUploadSettings():
        return 'aHR0cHM6Ly9zaXRlcy5nb29nbGUuY29tL3NpdGUvcm9id2Vic2V0L3R2dHVuZXMtdXBsb2FkLWNvbmZpZy54bWw='

    @staticmethod
    def getTvTunesId():
        # The ID that will be used to identify this installation
        return str(uuid.getnode())

    @staticmethod
    def setTvTunesId():
        __addon__.setSetting("tvtunesId", Settings.getTvTunesId())


# Class to handle all the screen saver settings
class ScreensaverSettings():
    MODES = (
        'TableDrop',
        'StarWars',
        'RandomZoomIn',
        'AppleTVLike',
        'GridSwitch',
        'Random',
        'Slider',
        'Crossfade'
    )
    SOURCES = (
        ['movies', 'tvshows'],
        ['movies'],
        ['tvshows'],
        ['image_folder']
    )
    IMAGE_TYPES = (
        ['fanart', 'thumbnail', 'cast'],
        ['fanart', 'thumbnail'],
        ['thumbnail', 'cast'],
        ['fanart'],
        ['thumbnail'],
        ['cast']
    )
    DIM_LEVEL = (
        'FFFFFFFF',
        'FFEEEEEE',
        'FFEEEEEE',
        'FFDDDDDD',
        'FFCCCCCC',
        'FFBBBBBB',
        'FFAAAAAA',
        'FF999999',
        'FF888888',
        'FF777777',
        'FF666666',
        'FF555555',
        'FF444444',
        'FF333333',
        'FF222222',
        'FF111111'
    )
    SLIDE_FROM = (
        'Left',
        'Right',
        'Top',
        'Bottom'
    )

    @staticmethod
    def getMode():
        if __addon__.getSetting("screensaver_mode"):
            return ScreensaverSettings.MODES[int(__addon__.getSetting("screensaver_mode"))]
        else:
            return 'Random'

    @staticmethod
    def getSource():
        selectedSource = __addon__.getSetting("screensaver_source")
        sourceId = 0
        if selectedSource:
            sourceId = int(selectedSource)
        return ScreensaverSettings.SOURCES[sourceId]

    @staticmethod
    def getImageTypes():
        imageTypes = __addon__.getSetting("screensaver_image_type")
        # If dealing with a custom folder, then no image type defined
        if ScreensaverSettings.getSource() == ['image_folder']:
            return []
        imageTypeId = 0
        if imageTypes:
            imageTypeId = int(imageTypes)
        return ScreensaverSettings.IMAGE_TYPES[imageTypeId]

    @staticmethod
    def getImagePath():
        return __addon__.getSetting("screensaver_image_path").decode("utf-8")

    @staticmethod
    def isRecursive():
        return __addon__.getSetting("screensaver_recursive") == 'true'

    @staticmethod
    def getWaitTime():
        return int(float(__addon__.getSetting('screensaver_wait_time')) * 1000)

    @staticmethod
    def getSpeed():
        return float(__addon__.getSetting('screensaver_speed'))

    @staticmethod
    def getEffectTime():
        return int(float(__addon__.getSetting('screensaver_effect_time')) * 1000)

    @staticmethod
    def getAppletvlikeConcurrency():
        return float(__addon__.getSetting('screensaver_appletvlike_concurrency'))

    @staticmethod
    def getGridswitchRowsColumns():
        return int(__addon__.getSetting('screensaver_gridswitch_columns'))

    @staticmethod
    def isGridswitchRandom():
        return __addon__.getSetting("screensaver_gridswitch_random") == 'true'

    @staticmethod
    def isPlayThemes():
        return __addon__.getSetting("screensaver_playthemes") == 'true'

    @staticmethod
    def isOnlyIfThemes():
        return __addon__.getSetting("screensaver_onlyifthemes") == 'true'

    @staticmethod
    def isRepeatTheme():
        return __addon__.getSetting("screensaver_themeControl") == '1'

    @staticmethod
    def isSkipAfterThemeOnce():
        return __addon__.getSetting("screensaver_themeControl") == '2'

    @staticmethod
    def getDimValue():
        # The actual dim level (Hex) is one of
        # FF111111, FF222222 ... FFEEEEEE, FFFFFFFF
        # Where FFFFFFFF is not changed
        # So that is a total of 15 different options
        if __addon__.getSetting("screensaver_dimlevel"):
            return ScreensaverSettings.DIM_LEVEL[int(__addon__.getSetting("screensaver_dimlevel"))]
        else:
            return 'FFFFFFFF'

    @staticmethod
    def getSlideFromOrigin():
        selectedOrigin = __addon__.getSetting("screensaver_slide_from")
        originId = 0
        if selectedOrigin:
            originId = int(selectedOrigin)
        return ScreensaverSettings.SLIDE_FROM[originId]

    @staticmethod
    def includeArtworkDownloader():
        # Make sure that the fanart is actually selected to be used, otherwise there is no
        # point in searching for it
        if 'fanart' in ScreensaverSettings.getImageTypes():
            return __addon__.getSetting("screensaver_artworkdownloader") == 'true'
        else:
            return False
