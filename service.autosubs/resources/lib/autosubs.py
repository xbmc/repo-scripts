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
    if debug == "true" or force:
        xbmc.log("#####[AutoSubs]##### " + msg, xbmc.LOGDEBUG)


Debug("Loading '%s' version '%s'" % (__scriptname__, __version__))


# check exclusion settings for filename passed as argument
def isExcluded(movie_full_path):
    if not movie_full_path:
        return False

    Debug("isExcluded(): Checking exclusion settings for '%s'." % movie_full_path)

    if (movie_full_path.find("pvr://") > -1) and __addon__.getSettingBool('ExcludeLiveTV'):
        Debug("isExcluded(): Video is playing via Live TV, which is currently set as excluded location.")
        return False

    if (movie_full_path.find("http://") > -1 or movie_full_path.find("https://") > -1) \
            and __addon__.getSettingBool('ExcludeHTTP'):
        Debug("isExcluded(): Video is playing via HTTP source, which is currently set as excluded location.")
        return False

    ExcludePath = __addon__.getSetting('ExcludePath')
    if ExcludePath and __addon__.getSettingBool('ExcludePathOption'):
        if movie_full_path.find(ExcludePath) > -1:
            Debug("isExcluded(): Video is playing from '%s', which is currently set as excluded path 1." % ExcludePath)
            return False

    ExcludePath2 = __addon__.getSetting('ExcludePath2')
    if ExcludePath2 and __addon__.getSettingBool('ExcludePathOption2'):
        if movie_full_path.find(ExcludePath2) > -1:
            Debug("isExcluded(): Video is playing from '%s', which is currently set as excluded path 2." % ExcludePath2)
            return False

    ExcludePath3 = __addon__.getSetting('ExcludePath3')
    if ExcludePath3 and __addon__.getSettingBool('ExcludePathOption3'):
        if movie_full_path.find(ExcludePath3) > -1:
            Debug("isExcluded(): Video is playing from '%s', which is currently set as excluded path 3." % ExcludePath3)
            return False

    ExcludePath4 = __addon__.getSetting('ExcludePath4')
    if ExcludePath4 and __addon__.getSettingBool('ExcludePathOption4'):
        if movie_full_path.find(ExcludePath4) > -1:
            Debug("isExcluded(): Video is playing from '%s', which is currently set as excluded path 4." % ExcludePath4)
            return False

    ExcludePath5 = __addon__.getSetting('ExcludePath5')
    if ExcludePath5 and __addon__.getSettingBool('ExcludePathOption5'):
        if movie_full_path.find(ExcludePath5) > -1:
            Debug("isExcluded(): Video is playing from '%s', which is currently set as excluded path 5." % ExcludePath5)
            return False

    return True


class AutoSubsPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        Debug("Initialized")
        self.run = True

    def onPlayBackStopped(self):
        Debug("Stopped")
        self.run = True

    def onPlayBackEnded(self):
        Debug("Ended")
        self.run = True

    def onPlayBackStarted(self):
        if self.isPlayingVideo():
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
                movie_full_path = self.getPlayingFile()
                Debug("movie_full_path '%s'" % movie_full_path)
                xbmc.sleep(1000)
                available_langs = self.getAvailableSubtitleStreams()
                Debug("available_langs '%s'" % available_langs)
                total_time = self.getTotalTime()
                Debug("total_time '%s'" % total_time)
                video_clip_album = ''
                if __addon__.getSettingBool('ExcludeVideoClip'):
                    video_clip_album = xbmc.InfoTagMusic.getAlbum()
                    Debug("videoclip_album '%s'" % video_clip_album)

                if (total_time > ExcludeTime and (not video_clip_album) and (
                        (not xbmc.getCondVisibility("VideoPlayer.HasSubtitles"))
                        or (check_for_specific and specific_language not in available_langs))
                        and all(movie_full_path.find(v) <= -1 for v in ignore_words)
                        and (isExcluded(movie_full_path))):
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
        monitor.waitForAbort(1)

    del player
