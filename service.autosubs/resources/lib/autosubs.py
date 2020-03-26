#!/usr/bin/python

import os
import xbmc
import xbmcaddon

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString
debug = __addon__.getSetting("debug")
__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path'))
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources'))

__settings__ = xbmcaddon.Addon("service.autosubs")

ignore_words = (__settings__.getSetting('ignore_words').split(','))
ExcludeTime = int((__settings__.getSetting('ExcludeTime'))) * 60

currentPlaying = ""

monitor = xbmc.Monitor()


def Debug(msg, force=False):
    if (debug == "true" or force):
        xbmc.log("#####[AutoSubs]##### " + msg, xbmc.LOGDEBUG)

Debug("Loading '%s' version '%s'" % (__scriptname__, __version__))


# check exclusion settings for filename passed as argument
def isExcluded(movieFullPath):
    if not movieFullPath:
        return False

    Debug("isExcluded(): Checking exclusion settings for '%s'." % movieFullPath)

    if (movieFullPath.find("pvr://") > -1) and __addon__.getSettingBool('ExcludeLiveTV'):
        Debug("isExcluded(): Video is playing via Live TV, which is currently set as excluded location.")
        return False

    if (movieFullPath.find("http://") > -1 or movieFullPath.find("https://") > -1) and __addon__.getSettingBool('ExcludeHTTP'):
        Debug("isExcluded(): Video is playing via HTTP source, which is currently set as excluded location.")
        return False

    ExcludePath = __addon__.getSetting('ExcludePath')
    if ExcludePath and __addon__.getSettingBool('ExcludePathOption'):
        if (movieFullPath.find(ExcludePath) > -1):
            Debug("isExcluded(): Video is playing from '%s', which is currently set as excluded path 1." % ExcludePath)
            return False

    ExcludePath2 = __addon__.getSetting('ExcludePath2')
    if ExcludePath2 and __addon__.getSettingBool('ExcludePathOption2'):
        if (movieFullPath.find(ExcludePath2) > -1):
            Debug("isExcluded(): Video is playing from '%s', which is currently set as excluded path 2." % ExcludePath2)
            return False

    ExcludePath3 = __addon__.getSetting('ExcludePath3')
    if ExcludePath3 and __addon__.getSettingBool('ExcludePathOption3'):
        if (movieFullPath.find(ExcludePath3) > -1):
            Debug("isExcluded(): Video is playing from '%s', which is currently set as excluded path 3." % ExcludePath3)
            return False

    ExcludePath4 = __addon__.getSetting('ExcludePath4')
    if ExcludePath4 and __addon__.getSettingBool('ExcludePathOption4'):
        if (movieFullPath.find(ExcludePath4) > -1):
            Debug("isExcluded(): Video is playing from '%s', which is currently set as excluded path 4." % ExcludePath4)
            return False

    ExcludePath5 = __addon__.getSetting('ExcludePath5')
    if ExcludePath5 and __addon__.getSettingBool('ExcludePathOption5'):
        if (movieFullPath.find(ExcludePath5) > -1):
            Debug("isExcluded(): Video is playing from '%s', which is currently set as excluded path 5." % ExcludePath5)
            return False

    return True


class AutoSubsPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        Debug("Initalized")
        self.run = True

    def onPlayBackStopped(self):
        Debug("Stopped")
        self.run = True

    def onPlayBackEnded(self):
        Debug("Ended")
        self.run = True

    def onPlayBackStarted(self):
        if (self.isPlayingVideo()):
            check_for_specific = __addon__.getSettingBool('check_for_specific')
            specific_language = __addon__.getSetting('selected_language')
            Debug("Specific language from settings '%s'" % specific_language)
            specific_language = xbmc.convertLanguage(specific_language, xbmc.ISO_639_2)
            Debug("Specific language ISO_639_2 '%s'" % specific_language)
            try:
                monitor.waitForAbort(3)
                if self.getSubtitles():
                    Debug("Subtitles already present '%s'" % self.getSubtitles())
                    self.run = False
            except:
                pass
            if self.run:
                movieFullPath = self.getPlayingFile()
                Debug("movieFullPath '%s'" % movieFullPath)
                xbmc.sleep(1000)
                availableLangs = self.getAvailableSubtitleStreams()
                Debug("availableLangs '%s'" % availableLangs)
                totalTime = self.getTotalTime()
                Debug("totalTime '%s'" % totalTime)
                videoclipAlbum = ''
                if __addon__.getSettingBool('ExcludeVideoClip'):
                    videoclipAlbum = xbmc.InfoTagMusic.getAlbum()
                    Debug("videoclipAlbum '%s'" % videoclipAlbum)

                if (totalTime > ExcludeTime and (not videoclipAlbum) and (
                    (not xbmc.getCondVisibility("VideoPlayer.HasSubtitles")) or (
                        check_for_specific and not specific_language in availableLangs)) and all(
                        movieFullPath.find(v) <= -1 for v in ignore_words) and (isExcluded(movieFullPath))):
                    self.run = False
                    xbmc.sleep(1000)
                    Debug('Started: AutoSearching for Subs')
                    xbmc.executebuiltin('ActivateWindow(SubtitleSearch)')
                else:
                    Debug('Started: Subs found or Excluded')
                    self.showSubtitles(True)
                    self.run = False
        else:
            Debug('Started: Not a video file, finishing')


class AutoSubsRunner:
    player = AutoSubsPlayer()

    while not monitor.abortRequested():
        if player.isPlaying():
            if (not xbmc.getCondVisibility("VideoPlayer.HasSubtitles")):
                monitor.waitForAbort(3)
                if player.isPlayingVideo() and player.getPlayingFile() != currentPlaying:
                    xbmc.executebuiltin('ActivateWindow(SubtitleSearch)')
                    currentPlaying = player.getPlayingFile()
        monitor.waitForAbort(1)

    del player
