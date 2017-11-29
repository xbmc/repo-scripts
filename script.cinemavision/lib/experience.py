import os
import re
import time
import threading

import xbmc
import xbmcgui

from kodijsonrpc import rpc

import kodigui
import kodiutil

kodiutil.LOG('Version: {0}'.format(kodiutil.ADDON.getAddonInfo('version')))

import cvutil  # noqa E402

import cinemavision  # noqa E402


AUDIO_FORMATS = {
    "dts": "DTS",
    "dca": "DTS",
    "dtsma": "DTS-HD Master Audio",
    "dtshd_ma": "DTS-HD Master Audio",
    "dtshd_hra": "DTS-HD Master Audio",
    "dtshr": "DTS-HD Master Audio",
    "ac3": "Dolby Digital",
    "eac3": "Dolby Digital Plus",
    "a_truehd": "Dolby TrueHD",
    "truehd": "Dolby TrueHD"
}

# aac, ac3, cook, dca, dtshd_hra, dtshd_ma, eac3, mp1, mp2, mp3, pcm_s16be, pcm_s16le, pcm_u8, truehd, vorbis, wmapro, wmav2


def DEBUG_LOG(msg):
    kodiutil.DEBUG_LOG('Experience: {0}'.format(msg))


def isURLFile(path):
    if path and path.endswith('.cvurl'):
        return True
    return False


def resolveURLFile(path):
    import YDStreamExtractor as StreamExtractor

    StreamExtractor.overrideParam('noplaylist', True)
    StreamExtractor.generateBlacklist(('.*:(?:user|channel|search)$', '(?i)generic.*'))

    import xbmcvfs
    f = xbmcvfs.File(path, 'r')
    try:
        url = f.read().strip()
    except:
        kodiutil.ERROR()
        return
    finally:
        f.close()

    vid = StreamExtractor.getVideoInfo(url)

    if not vid:
        return None

    return vid.streamURL()


class KodiVolumeControl:
    def __init__(self, abort_flag):
        self.saved = None
        self.abortFlag = abort_flag
        self._stopFlag = False
        self._fader = None
        self._restoring = False

    def current(self):
        return rpc.Application.GetProperties(properties=['volume'])['volume']

    def fading(self):
        if not self._fader:
            return False

        return self._fader.isAlive()

    def _set(self, volume):
        xbmc.executebuiltin("XBMC.SetVolume({0})".format(volume))
        # rpc.Application.SetVolume(volume=volume)  # This works but displays the volume indicator :(

    def store(self):
        if self.saved:
            return

        self.saved = self.current()

    def restore(self, delay=0):
        if self._restoring:
            return

        self._restoring = True
        try:
            if self.saved is None:
                return

            if delay:
                xbmc.sleep(delay)

            DEBUG_LOG('Restoring volume to: {0}'.format(self.saved))

            self._set(self.saved)
            self.saved = None
        finally:
            self._restoring = False

    def set(self, volume_or_pct, fade_time=0, relative=False):
        self.store()
        if relative:
            volume = int(self.saved * (volume_or_pct / 100.0))
            DEBUG_LOG('Setting volume to: {0} ({1}%)'.format(volume, volume_or_pct))
        else:
            volume = volume_or_pct
            DEBUG_LOG('Setting volume to: {0}'.format(volume))

        if fade_time:
            current = self.current()
            self._fade(current, volume, fade_time)
        else:
            self._set(volume)

    def stop(self):
        self._stopFlag = True

    def _stop(self):
        if self._stopFlag:
            self._stopFlag = False
            return True
        return False

    def _fade(self, start, end, fade_time_millis):
        if self.fading():
            self.stop()
            self._fader.join()
        self._fader = threading.Thread(target=self._fadeWorker, args=(start, end, fade_time_millis))
        self._fader.start()

    def _fadeWorker(self, start, end, fade_time_millis):
        volWidth = end - start

        func = end > start and min or max

        duration = fade_time_millis / 1000.0
        endTime = time.time() + duration
        vol = start
        left = duration

        DEBUG_LOG('Fade: START ({0}) - {1}ms'.format(start, fade_time_millis))
        while time.time() < endTime and not kodiutil.wait(0.1):
            while xbmc.getCondVisibility('Player.Paused') and not kodiutil.wait(0.1):
                endTime = time.time() + left

            if xbmc.abortRequested or not xbmc.getCondVisibility('Player.Playing') or self.abortFlag.isSet() or self._stop():
                DEBUG_LOG(
                    'Fade ended early({0}): {1}'.format(vol, not xbmc.getCondVisibility('Player.Playing') and 'NOT_PLAYING' or 'ABORT')
                )
                return
            left = endTime - time.time()
            vol = func(end, int(start + (((duration - left) / duration) * volWidth)))
            self._set(vol)

        DEBUG_LOG('Fade: END ({0})'.format(vol))


class SettingControl:
    def __init__(self, setting, log_display, disable_value=''):
        self.setting = setting
        self.logDisplay = log_display
        self.disableValue = disable_value
        self._originalMode = None
        self.store()

    def disable(self):
        rpc.Settings.SetSettingValue(setting=self.setting, value=self.disableValue)
        DEBUG_LOG('{0}: DISABLED'.format(self.logDisplay))

    def store(self):
        try:
            self._originalMode = rpc.Settings.GetSettingValue(setting=self.setting).get('value')
            DEBUG_LOG('{0}: Mode stored ({1})'.format(self.logDisplay, self._originalMode))
        except:
            kodiutil.ERROR()

    def restore(self):
        if not self._originalMode:
            return
        rpc.Settings.SetSettingValue(setting=self.setting, value=self._originalMode)
        DEBUG_LOG('{0}: RESTORED'.format(self.logDisplay))


class ExperienceWindow(kodigui.BaseWindow):
    xmlFile = 'script.cinemavision-experience.xml'
    path = kodiutil.ADDON_PATH
    theme = 'Main'
    res = '1080i'

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        kodiutil.setGlobalProperty('paused', '')
        kodiutil.setGlobalProperty('number', '')
        kodiutil.setScope()
        self.player = None
        self.action = None
        self.volume = None
        self.abortFlag = None
        self.effect = None
        self.duration = 400
        self.lastImage = ''
        self.initialized = False
        self._paused = False
        self._pauseStart = 0
        self._pauseDuration = 0
        self.clear()

    def onInit(self):
        kodigui.BaseWindow.onInit(self)
        self.image = (self.getControl(100), self.getControl(101))
        self.skipNotice = self.getControl(200)
        self.initialized = True

    def join(self):
        while not kodiutil.wait(0.1) and not self.abortFlag.isSet():
            if self.initialized:
                return

    def initialize(self):
        self.clear()
        self.action = None

    def setImage(self, url):
        self._paused = False
        self._pauseStart = 0
        self._pauseDuration = 0

        if not self.effect:
            return

        if self.effect == 'none':
            self.none(url)
        elif self.effect == 'fade':
            self.change(url)
        elif self.effect == 'fadesingle':
            self.change(url)
        elif self.effect.startswith('slide'):
            self.change(url)

    def none(self, url):
        self.lastImage = url
        kodiutil.setGlobalProperty('image0', url)

    # def fade(self, url):
    #     kodiutil.setGlobalProperty('image{0}'.format(self.currentImage), url)
    #     self.currentImage = int(not self.currentImage)
    #     kodiutil.setGlobalProperty('show1', not self.currentImage and '1' or '')

    def change(self, url):
        kodiutil.setGlobalProperty('image0', self.lastImage)
        kodiutil.setGlobalProperty('show1', '')
        xbmc.sleep(100)
        kodiutil.setGlobalProperty('image1', url)
        kodiutil.setGlobalProperty('show1', '1')
        self.lastImage = url

    def clear(self):
        self.currentImage = 0
        self.lastImage = ''
        kodiutil.setGlobalProperty('image0', '')
        kodiutil.setGlobalProperty('image1', '')
        kodiutil.setGlobalProperty('show1', '')

    def setTransition(self, effect=None, duration=400):
        self.duration = duration
        self.effect = effect or 'none'
        if self.effect == 'none':
            self.image[1].setAnimations([])
        elif self.effect == 'fade':
            self.image[1].setAnimations([
                ('Visible', 'effect=fade start=0 end=100 time={duration}'.format(duration=self.duration)),
                ('Hidden', 'effect=fade start=100 end=0 time=0')
            ])
        elif self.effect == 'fadesingle':  # Used for single image fade in/out
            self.image[1].setAnimations([
                ('Visible', 'effect=fade start=0 end=100 time={duration}'.format(duration=self.duration)),
                ('Hidden', 'effect=fade start=100 end=0 time={duration}'.format(duration=self.duration))
            ])
        elif self.effect == 'slideL':
            self.image[1].setAnimations([
                ('Visible', 'effect=slide start=1980,0 end=0,0 time={duration}'.format(duration=self.duration)),
                ('Hidden', 'effect=slide start=0,0 end=1980,0 time=0')
            ])
        elif self.effect == 'slideR':
            self.image[1].setAnimations([
                ('Visible', 'effect=slide start=-1980,0 end=0,0 time={duration}'.format(duration=self.duration)),
                ('Hidden', 'effect=slide start=0,0 end=-1980,0 time=0')
            ])
        elif self.effect == 'slideU':
            self.image[1].setAnimations([
                ('Visible', 'effect=slide start=0,1080 end=0,0 time={duration}'.format(duration=self.duration)),
                ('Hidden', 'effect=slide start=0,0 end=0,1080 time=0')
            ])
        elif self.effect == 'slideD':
            self.image[1].setAnimations([
                ('Visible', 'effect=slide start=0,-1080 end=0,0 time={duration}'.format(duration=self.duration)),
                ('Hidden', 'effect=slide start=0,0 end=-1080 time=0')
            ])

    def fadeOut(self):
        kodiutil.setGlobalProperty('show1', '')

    def onAction(self, action):
        # print action.getId()
        try:
            if action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK or action == xbmcgui.ACTION_STOP:
                self.volume.stop()
                self.abortFlag.set()
                self.doClose()
            elif action == xbmcgui.ACTION_MOVE_RIGHT:
                if self.action != 'SKIP':
                    self.action = 'NEXT'
            elif action == xbmcgui.ACTION_MOVE_LEFT:
                if self.action != 'BACK':
                    self.action = 'PREV'
            elif action == xbmcgui.ACTION_MOVE_UP:
                if self.action != 'SKIP':
                    self.action = 'BIG_NEXT'
            elif action == xbmcgui.ACTION_MOVE_DOWN:
                if self.action != 'BACK':
                    self.action = 'BIG_PREV'
            elif action == xbmcgui.ACTION_PAGE_UP or action == xbmcgui.ACTION_NEXT_ITEM:
                self.action = 'SKIP'
            elif action == xbmcgui.ACTION_PAGE_DOWN or action == xbmcgui.ACTION_PREV_ITEM:
                self.action = 'BACK'
            elif action == xbmcgui.ACTION_PAUSE:
                self.pause()
            elif action == xbmcgui.ACTION_CONTEXT_MENU:
                return
        except:
            kodiutil.ERROR()
            return kodigui.BaseWindow.onAction(self, action)

        kodigui.BaseWindow.onAction(self, action)

    def onPause(self):
        self.player.onPlayBackPaused()
        kodiutil.setGlobalProperty('paused', '1')

    def onResume(self):
        self.player.onPlayBackResumed()
        kodiutil.setGlobalProperty('paused', '')

    def hasAction(self):
        return bool(self.action)

    def pause(self):
        if xbmc.getCondVisibility('Player.HasAudio'):
            if xbmc.getCondVisibility('Player.Paused'):
                self._pauseStart = time.time()
                self._paused = True
            else:
                self._pauseDuration = time.time() - self._pauseStart
                self.action = 'RESUME'
        else:
            if self._paused:
                self._pauseDuration = time.time() - self._pauseStart
                self.action = 'RESUME'
                self.onResume()
            else:
                self._pauseStart = time.time()
                self._paused = True
                self.onPause()

    def pauseDuration(self):
        pd = self._pauseDuration
        self._pauseDuration = 0
        return pd

    def finishPause(self):
        self._paused = False
        self._pauseStart = 0

    def getAction(self):
        action = self.action
        self.action = None
        return action

    def skip(self):
        if self.action == 'SKIP':
            self.action = None
            return True
        return False

    def back(self):
        if self.action == 'BACK':
            self.action = None
            return True
        return False

    def next(self):
        if self.action == 'NEXT':
            self.action = None
            return True
        return False

    def prev(self):
        if self.action == 'PREV':
            self.action = None
            return True
        return False

    def bigNext(self):
        if self.action == 'BIG_NEXT':
            self.action = None
            return True
        return False

    def bigPrev(self):
        if self.action == 'BIG_PREV':
            self.action = None
            return True
        return False

    def paused(self):
        return self._paused

    def resume(self):
        if self.action == 'RESUME':
            self.action = None
            return True
        return False

    def setSkipNotice(self, msg):
        kodiutil.setGlobalProperty('number', msg)
        self.skipNotice.setAnimations([('Conditional', 'effect=fade start=100 end=0 time=500 delay=1000 condition=true')])


class ExperiencePlayer(xbmc.Player):
    NOT_PLAYING = 0
    PLAYING_DUMMY_NEXT = -1
    PLAYING_DUMMY_PREV = -2
    PLAYING_MUSIC = -10

    DUMMY_FILE_PREV = 'script.cinemavision.dummy_PREV.mpeg'
    DUMMY_FILE_NEXT = 'script.cinemavision.dummy_NEXT.mpeg'

    def create(self, from_editor=False):
        # xbmc.Player.__init__(self)
        self.fromEditor = from_editor
        self.playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.fakeFilePrev = os.path.join(kodiutil.ADDON_PATH, 'resources', 'videos', self.DUMMY_FILE_PREV)
        self.fakeFileNext = os.path.join(kodiutil.ADDON_PATH, 'resources', 'videos', self.DUMMY_FILE_NEXT)
        self.featureStub = os.path.join(kodiutil.ADDON_PATH, 'resources', 'videos', 'script.cinemavision.feature_stub.mp4')
        self.playStatus = 0
        self.hasFullscreened = False
        self.loadActions()
        self.init()
        return self

    @property
    def has3D(self):
        for f in self.features:
            if f.is3D:
                return True
        return False

    def doPlay(self, item, listitem=None, windowed=None, startpos=None):
        self.playStatus = self.NOT_PLAYING
        self.play(item)

    # PLAYER EVENTS
    def onPlayBackEnded(self):
        if self.playStatus != self.PLAYING_MUSIC:
            self.volume.restore()

        if self.playStatus == self.PLAYING_MUSIC:
            self.log('MUSIC ENDED')
            return
        elif self.playStatus == self.NOT_PLAYING:
            return self.onPlayBackFailed()

        self.playStatus = self.NOT_PLAYING

        if self.playlist.getposition() != -1:
            DEBUG_LOG('PLAYBACK ENDED')
            if self.playlist.size():
                return

        self.next()

    def onPlayBackPaused(self):
        DEBUG_LOG('PLAYBACK PAUSED')
        if self.pauseAction:
            DEBUG_LOG('Executing pause action: {0}'.format(self.pauseAction))
            self.pauseAction.run()

    def onPlayBackResumed(self):
        DEBUG_LOG('PLAYBACK RESUMED')
        if self.resumeAction is True:
            resumeAction = self.processor.lastAction()
            if resumeAction:
                DEBUG_LOG('Executing resume action (last): {0}'.format(resumeAction))
                resumeAction.run()
        elif self.resumeAction:
            DEBUG_LOG('Executing resume action: {0}'.format(self.resumeAction))
            self.resumeAction.run()

    def onPlayBackStarted(self):
        if self.playStatus == self.PLAYING_MUSIC:
            DEBUG_LOG('MUSIC STARTED')
            return

        self.playStatus = time.time()
        if self.DUMMY_FILE_PREV in self.getPlayingFile():
            self.playStatus = self.PLAYING_DUMMY_PREV
            kodiutil.DEBUG_LOG('Stopping for PREV dummy')
            self.stop()
            return
        elif self.DUMMY_FILE_NEXT in self.getPlayingFile():
            self.playStatus = self.PLAYING_DUMMY_NEXT
            kodiutil.DEBUG_LOG('Stopping for NEXT dummy')
            self.stop()
            return
        else:
            self.hasFullscreened = False

        DEBUG_LOG('PLAYBACK STARTED')

    def onPlayBackStopped(self):
        if self.playStatus != self.PLAYING_MUSIC:
            self.volume.restore()

        if self.playStatus == self.PLAYING_MUSIC:
            DEBUG_LOG('MUSIC STOPPED')
            return
        elif self.playStatus == self.NOT_PLAYING:
            return self.onPlayBackFailed()
        elif self.playStatus == self.PLAYING_DUMMY_NEXT:
            self.playStatus = self.NOT_PLAYING
            DEBUG_LOG('PLAYBACK INTERRUPTED')
            self.next()
            return
        elif self.playStatus == self.PLAYING_DUMMY_PREV:
            self.playStatus = self.NOT_PLAYING
            DEBUG_LOG('SKIP BACK')
            self.next(prev=True)
            return

        self.playStatus = self.NOT_PLAYING
        DEBUG_LOG('PLAYBACK STOPPED')
        self.abort()

    def onPlayBackFailed(self):
        self.playStatus = self.NOT_PLAYING
        DEBUG_LOG('PLAYBACK FAILED')
        self.next()

    def onAbort(self):
        if self.abortAction:
            DEBUG_LOG('Executing abort action: {0}'.format(self.abortAction))
            self.abortAction.run()

    def getPlayingFile(self):
        if self.isPlaying():
            try:
                return xbmc.Player.getPlayingFile(self)
            except RuntimeError:
                pass
            return ''
        return ''

    def init(self):
        self.abortFlag = threading.Event()
        self.window = None
        self.volume = KodiVolumeControl(self.abortFlag)
        self.screensaver = SettingControl('screensaver.mode', 'Screensaver')
        self.visualization = SettingControl('musicplayer.visualisation', 'Visualization')
        self.playGUISounds = SettingControl('audiooutput.guisoundmode', 'Play GUI sounds', disable_value=0)
        self.features = []

        result = rpc.Playlist.GetItems(
            playlistid=xbmc.PLAYLIST_VIDEO, properties=['file', 'genre', 'mpaa', 'streamdetails', 'title', 'thumbnail', 'runtime', 'year']
        )
        for r in result.get('items', []):
            feature = self.featureFromJSON(r)
            self.features.append(feature)

        if self.fromEditor and not self.features:
            feature = cinemavision.sequenceprocessor.Feature(self.featureStub)
            feature.title = 'Feature Stub'
            feature.rating = 'MPAA:PG-13'
            feature.audioFormat = 'Dolby Digital'

            self.features.append(feature)

    def loadActions(self):
        self.pauseAction = None
        self.resumeAction = None
        self.abortAction = None

        if kodiutil.getSetting('action.onPause', False):
            actionFile = kodiutil.getSetting('action.onPause.file')
            self.pauseAction = actionFile and cinemavision.actions.ActionFileProcessor(actionFile) or None

        if kodiutil.getSetting('action.onResume', 0) == 2:
            actionFile = kodiutil.getSetting('action.onResume.file')
            self.resumeAction = actionFile and cinemavision.actions.ActionFileProcessor(actionFile) or None
        elif kodiutil.getSetting('action.onResume', 0) == 1:
            self.resumeAction = True

        if kodiutil.getSetting('action.onAbort', False):
            actionFile = kodiutil.getSetting('action.onAbort.file')
            self.abortAction = actionFile and cinemavision.actions.ActionFileProcessor(actionFile) or None

    def getCodecAndChannelsFromStreamDetails(self, details):
        try:
            streams = sorted(details['audio'], key=lambda x: x['channels'], reverse=True)
            for s in streams:
                codec = s['codec']
                if codec in AUDIO_FORMATS:
                    return (codec, s['channels'])
            return (streams[0]['codec'], streams[0]['channels'])
        except:
            return ('', '')

    def featureFromJSON(self, r):
        tags3DRegEx = kodiutil.getSetting('3D.tag.regex', cvutil.DEFAULT_3D_RE)

        feature = cinemavision.sequenceprocessor.Feature(r['file'])
        feature.title = r.get('title') or r.get('label', '')
        ratingString = cvutil.ratingParser().getActualRatingFromMPAA(r.get('mpaa', ''), debug=True)
        if ratingString:
            feature.rating = ratingString
        feature.ID = kodiutil.intOrZero(r.get('movieid', r.get('episodeid', r.get('id', 0))))
        feature.dbType = r.get('type', '')
        feature.genres = r.get('genre', [])
        feature.thumb = r.get('thumbnail', '')
        feature.runtime = r.get('runtime', 0)
        feature.year = r.get('year', 0)

        try:
            stereomode = r['streamdetails']['video'][0]['stereomode']
        except:
            stereomode = ''

        if stereomode not in ('mono', ''):
            feature.is3D = True
        else:
            feature.is3D = bool(re.search(tags3DRegEx, r['file']))

        try:
            codec, channels = self.getCodecAndChannelsFromStreamDetails(r['streamdetails'])

            DEBUG_LOG('CODEC ({0}): {1} ({2} channels)'.format(kodiutil.strRepr(feature.title), codec, channels or '?'))
            DEBUG_LOG('STREAMDETAILS: {0}'.format(repr(r.get('streamdetails'))))

            feature.audioFormat = AUDIO_FORMATS.get(codec)
            feature.codec = codec
            feature.channels = channels
        except:
            DEBUG_LOG('CODEC ({0}): NOT DETECTED'.format(kodiutil.strRepr(feature.title)))
            DEBUG_LOG('STREAMDETAILS: {0}'.format(repr(r.get('streamdetails'))))

        return feature

    def addCollectionMovies(self):
        DBID = kodiutil.intOrZero(xbmc.getInfoLabel('ListItem.DBID'))

        try:
            details = rpc.VideoLibrary.GetMovieSetDetails(setid=DBID)
            for m in details['setdetails']['movies']:
                try:
                    r = rpc.VideoLibrary.GetMovieDetails(
                        movieid=m['movieid'], properties=['file', 'genre', 'mpaa', 'streamdetails', 'title', 'thumbnail', 'runtime', 'year']
                    )['moviedetails']
                    feature = self.featureFromJSON(r)
                    self.features.append(feature)
                except:
                    kodiutil.ERROR()
        except:
            kodiutil.ERROR()
            return False

        return True

    def getDBTypeAndID(self):
        return xbmc.getInfoLabel('ListItem.DBTYPE'), xbmc.getInfoLabel('ListItem.DBID')

    def addFromID(self, movieid=None, episodeid=None, selection=False, dbtype=None, dbid=None):
        if selection:
            DEBUG_LOG('Adding from selection')
            stype, ID = self.getDBTypeAndID()
            if stype == 'movie':
                movieid = ID
            elif stype in ('tvshow', 'episode'):
                episodeid = ID
            else:
                return False
        elif dbtype:
            DEBUG_LOG('Adding from DB: dbtype={0} dbid={1}'.format(dbtype, dbid))
            if dbtype == 'movie':
                movieid = dbid
            elif dbtype in ('tvshow', 'episode'):
                episodeid = dbid
        else:
            DEBUG_LOG('Adding from id: movieid={0} episodeid={1}'.format(movieid, episodeid))

        self.features = []

        if movieid:
            for movieid in str(movieid).split('|'):  # ID could be int or \ seperated int string
                movieid = kodiutil.intOrZero(movieid)
                if not movieid:
                    continue

                r = rpc.VideoLibrary.GetMovieDetails(
                    movieid=movieid,
                    properties=['file', 'genre', 'mpaa', 'streamdetails', 'title', 'thumbnail', 'runtime', 'year']
                )['moviedetails']
                r['type'] = 'movie'

                feature = self.featureFromJSON(r)
                self.features.append(feature)
        elif episodeid:
            for episodeid in str(episodeid).split('|'):  # ID could be int or \ seperated int string
                episodeid = kodiutil.intOrZero(episodeid)
                if not episodeid:
                    continue

                r = rpc.VideoLibrary.GetEpisodeDetails(
                    episodeid=episodeid,
                    properties=['file', 'streamdetails', 'title', 'thumbnail', 'runtime']
                )['episodedetails']
                r['type'] = 'tvshow'
                feature = self.featureFromJSON(r)
                self.features.append(feature)

        if not self.features:
            return False

        return True

    def addDBFeature(self, dbtype, dbid):
        return self.addFromID(dbtype=dbtype, dbid=dbid)

    def addSelectedFeature(self, movieid=None, episodeid=None, selection=False):
        if selection or movieid or episodeid:
            return self.addFromID(movieid, episodeid, selection)

        if xbmc.getCondVisibility('ListItem.IsCollection'):
            kodiutil.DEBUG_LOG('Selection is a collection')
            return self.addCollectionMovies()

        title = kodiutil.infoLabel('ListItem.Title')
        if not title:
            return False
        feature = cinemavision.sequenceprocessor.Feature(kodiutil.infoLabel('ListItem.FileNameAndPath'))
        feature.title = title

        ratingString = cvutil.ratingParser().getActualRatingFromMPAA(kodiutil.infoLabel('ListItem.Mpaa'), debug=True)
        if ratingString:
            feature.rating = ratingString

        feature.ID = kodiutil.intOrZero(xbmc.getInfoLabel('ListItem.DBID'))
        feature.dbType = xbmc.getInfoLabel('ListItem.DBTYPE')
        feature.genres = kodiutil.infoLabel('ListItem.Genre').split(' / ')
        feature.thumb = kodiutil.infoLabel('ListItem.Thumb')
        feature.year = kodiutil.infoLabel('ListItem.Year')

        try:
            feature.runtime = kodiutil.intOrZero(xbmc.getInfoLabel('ListItem.Duration')) * 60
        except TypeError:
            pass

        feature.is3D = xbmc.getCondVisibility('ListItem.IsStereoscopic')

        if not feature.is3D:
            tags3DRegEx = kodiutil.getSetting('3D.tag.regex', cvutil.DEFAULT_3D_RE)

            feature.is3D = bool(re.search(tags3DRegEx, feature.path))

        codec = xbmc.getInfoLabel('ListItem.AudioCodec')
        channels = kodiutil.intOrZero(xbmc.getInfoLabel('ListItem.AudioChannels'))

        if codec:
            feature.audioFormat = AUDIO_FORMATS.get(codec)
            feature.codec = codec
            feature.channels = channels
            DEBUG_LOG('CODEC ({0}): {1} ({2} channels)'.format(kodiutil.strRepr(feature.title), codec, channels or '?'))
        else:
            DEBUG_LOG('CODEC ({0}): NOT DETECTED'.format(kodiutil.strRepr(feature.title)))

        self.features.append(feature)
        return True

    def hasFeatures(self):
        return bool(self.features)

    def selectionAvailable(self):
        return bool(kodiutil.intOrZero(xbmc.getInfoLabel('ListItem.DBID')))

    def getPathAndListItemFromVideo(self, video):
        path = video.path

        if isURLFile(path):
            path = resolveURLFile(path)
        else:
            if video.userAgent:
                path += '|User-Agent=' + video.userAgent

        li = xbmcgui.ListItem(video.title, 'CinemaVision', thumbnailImage=video.thumb, path=path)
        li.setInfo('video', {'title': video.title})
        li.setIconImage(video.thumb)

        return path, li

    def playVideos(self, videos, features=None):
        self.playlist.clear()
        rpc.Playlist.Clear(playlistid=xbmc.PLAYLIST_VIDEO)

        volume = (features or videos)[0].volume
        if volume != 100:
            self.volume.set(volume, relative=True)

        self.playlist.add(self.fakeFilePrev)
        if features:
            for feature in features:
                self.addFeatureToPlaylist(feature)
        else:
            for video in videos:
                pli = self.getPathAndListItemFromVideo(video)
                self.playlist.add(*pli)

        self.playlist.add(self.fakeFileNext)
        self.videoPreDelay()
        rpc.Player.Open(item={'playlistid': xbmc.PLAYLIST_VIDEO, 'position': 1}, options={'shuffled': False, 'resume': False, 'repeat': 'off'})
        xbmc.sleep(100)
        while not xbmc.getCondVisibility('VideoPlayer.IsFullscreen') and not xbmc.abortRequested and not self.abortFlag.isSet() and self.isPlaying():
            xbmc.executebuiltin('ActivateWindow(fullscreenvideo)')
            xbmc.sleep(100)
        self.hasFullscreened = True
        DEBUG_LOG('VIDEO HAS GONE FULLSCREEN')

    def addFeatureToPlaylist(self, feature):
        if feature.dbType == 'movie':
            item = {'movieid': feature.ID}
        elif feature.dbType == 'tvshow':
            item = {'episodeid': feature.ID}
        else:
            item = {'file': feature.path}
        rpc.Playlist.Add(playlistid=xbmc.PLAYLIST_VIDEO, item=item)

    def videoPreDelay(self):
        delay = kodiutil.getSetting('video.preDelay', 0)
        if delay:
            kodiutil.DEBUG_LOG('Video pre-dalay: {0}ms'.format(delay))
            xbmc.sleep(delay)

    def isPlayingMinimized(self):
        if not xbmc.getCondVisibility('Player.Playing'):  # isPlayingVideo() returns True before video actually plays (ie. is fullscreen)
            return False

        if xbmc.getCondVisibility('VideoPlayer.IsFullscreen'):  # If all is good, let's return now
            return False

        if self.playStatus <= 0:
            return False

        if xbmc.getCondVisibility('Window.IsVisible(busydialog)'):
            return False

        if time.time() - self.playStatus < 5 and not self.hasFullscreened:  # Give it a few seconds to make sure fullscreen has happened
            return False

        if xbmcgui.getCurrentWindowId() == 10028:
            xbmc.executebuiltin('Action(back)')
            return False

        if xbmcgui.getCurrentWindowId() == 10000:
            self.window.show()
            xbmc.executebuiltin('ActivateWindow(fullscreenvideo)')
            return False

        if not xbmc.getCondVisibility('VideoPlayer.IsFullscreen'):
            xbmc.sleep(500)

        print '{0} {1} {2} {3} {4}'.format(
            self.isPlayingVideo(),
            xbmc.getCondVisibility('Player.Playing'),
            self.playStatus,
            xbmc.getCondVisibility('VideoPlayer.IsFullscreen'),
            xbmcgui.getCurrentWindowId()
        )

        return not xbmc.getCondVisibility('VideoPlayer.IsFullscreen')

    def start(self, sequence_path):
        kodiutil.setGlobalProperty('running', '1')
        xbmcgui.Window(10025).setProperty('CinemaExperienceRunning', 'True')
        self.initSkinVars()
        self.playGUISounds.disable()
        self.screensaver.disable()
        self.visualization.disable()
        try:
            return self._start(sequence_path)
        finally:
            self.playGUISounds.restore()
            self.screensaver.restore()
            self.visualization.restore()
            kodiutil.setGlobalProperty('running', '')
            xbmcgui.Window(10025).setProperty('CinemaExperienceRunning', '')
            self.initSkinVars()

    def _start(self, sequence_path):
        import cvutil

        self.processor = cinemavision.sequenceprocessor.SequenceProcessor(sequence_path, content_path=cvutil.getContentPath())
        [self.processor.addFeature(f) for f in self.features]

        kodiutil.DEBUG_LOG('\n.')
        DEBUG_LOG('[ -- Started --------------------------------------------------------------- ]')

        self.openWindow()
        self.processor.process()
        self.setSkinFeatureVars()
        self.next()
        self.waitLoop()

        del self.window
        self.window = None

    def openWindow(self):
        self.window = ExperienceWindow.create()
        self.window.player = self
        self.window.volume = self.volume
        self.window.abortFlag = self.abortFlag
        self.window.join()

    def waitLoop(self):
        while not kodiutil.wait(0.1) and self.window.isOpen:
            if self.processor.atEnd():
                break

            if self.isPlayingMinimized():
                DEBUG_LOG('Fullscreen video closed - stopping')
                self.stop()
        else:
            if not self.processor.atEnd():
                self.onAbort()

        DEBUG_LOG('[ -- Finished -------------------------------------------------------------- ]\n.')
        self.window.doClose()
        rpc.Playlist.Clear(playlistid=xbmc.PLAYLIST_VIDEO)
        self.stop()

    def initSkinVars(self):
        kodiutil.setGlobalProperty('module.current', '')
        kodiutil.setGlobalProperty('module.current.name', '')
        kodiutil.setGlobalProperty('module.next', '')
        kodiutil.setGlobalProperty('module.next.name', '')
        self.initSkinFeatureVars()

    def initSkinFeatureVars(self):
        kodiutil.setGlobalProperty('feature.next.title', '')
        kodiutil.setGlobalProperty('feature.next.dbid', '')
        kodiutil.setGlobalProperty('feature.next.dbtype', '')
        kodiutil.setGlobalProperty('feature.next.path', '')

    def setSkinFeatureVars(self):
        feature = self.processor.nextFeature()

        if feature:
            kodiutil.setGlobalProperty('feature.next.title', feature.title)
            kodiutil.setGlobalProperty('feature.next.dbid', str(feature.ID))
            kodiutil.setGlobalProperty('feature.next.dbtype', feature.dbType)
            kodiutil.setGlobalProperty('feature.next.path', feature.path)
        else:
            self.initSkinFeatureVars()

    def playMusic(self, image_queue):
        if not image_queue.music:
            return

        pl = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        pl.clear()
        for s in image_queue.music:
            pl.add(s.path)

        xbmc.sleep(100)  # Without this, it will sometimes not play anything

        DEBUG_LOG('Playing music playlist: {0} song(s)'.format(len(pl)))

        self.volume.store()
        self.volume.set(1)

        self.playStatus = self.PLAYING_MUSIC
        self.play(pl, windowed=True)

        self.waitForPlayStart()  # Wait playback so fade will work
        self.volume.set(image_queue.musicVolume, fade_time=int(image_queue.musicFadeIn * 1000), relative=True)

    def stopMusic(self, image_queue=None):
        try:
            rpc.Playlist.Clear(playlistid=xbmc.PLAYLIST_MUSIC)

            if image_queue and image_queue.music:
                self.volume.set(1, fade_time=int(image_queue.musicFadeOut * 1000))
                while self.volume.fading() and not self.abortFlag.isSet() and not kodiutil.wait(0.1):
                    if self.window.hasAction() and self.window.action != 'RESUME':
                        break

            kodiutil.DEBUG_LOG('Stopping music')
            self.stop()
            self.waitForPlayStop()
            self.playStatus = self.NOT_PLAYING
        finally:
            self.volume.restore(delay=500)

    def waitForPlayStart(self, timeout=10000):
        giveUpTime = time.time() + timeout / 1000.0
        while not xbmc.getCondVisibility('Player.Playing') and time.time() < giveUpTime and not self.abortFlag.isSet():
            xbmc.sleep(100)

    def waitForPlayStop(self):
        while self.isPlaying() and not self.abortFlag.isSet():
            xbmc.sleep(100)

    def showImage(self, image):
        try:
            if image.fade:
                self.window.setTransition('fadesingle', image.fade)

            self.window.setImage(image.path)

            stop = time.time() + image.duration
            fadeStop = image.fade and stop - (image.fade / 1000) or 0

            while not kodiutil.wait(0.1) and (time.time() < stop or self.window.paused()):
                if fadeStop and time.time() >= fadeStop and not self.window.paused():
                    fadeStop = None
                    self.window.fadeOut()

                if not self.window.isOpen:
                    return False
                elif self.window.action:
                    if self.window.next():
                        return 'NEXT'
                    elif self.window.prev():
                        return 'PREV'
                    elif self.window.skip():
                        return 'SKIP'
                    elif self.window.back():
                        return 'BACK'
                    elif self.window.resume():
                        stop += self.window.pauseDuration()
                        self.window.finishPause()

            return True
        finally:
            self.window.clear()

    def showImageFromQueue(self, image, info, first=None):
        self.window.setImage(image.path)

        stop = time.time() + image.duration

        while not kodiutil.wait(0.1) and (time.time() < stop or self.window.paused()):
            if not self.window.isOpen:
                return False

            if info.musicEnd and time.time() >= info.musicEnd and not self.window.paused():
                info.musicEnd = None
                self.stopMusic(info.imageQueue)
            elif self.window.action:
                if self.window.next():
                    return 'NEXT'
                elif self.window.prev():
                    return 'PREV'
                if self.window.bigNext():
                    return 'BIG_NEXT'
                elif self.window.bigPrev():
                    return 'BIG_PREV'
                elif self.window.skip():
                    return 'SKIP'
                elif self.window.back():
                    return 'BACK'
                elif self.window.resume():
                    stop += self.window.pauseDuration()
                    self.window.finishPause()

            if xbmcgui.getCurrentWindowId() != self.window._winID:  # Prevent switching to another window as it's not a good idea
                self.window.show()

        return True

    class ImageQueueInfo:
        def __init__(self, image_queue, music_end):
            self.imageQueue = image_queue
            self.musicEnd = music_end

    def showImageQueue(self, image_queue):
        image_queue.reset()
        image = image_queue.next()

        start = time.time()
        end = time.time() + image_queue.duration
        musicEnd = [end - image_queue.musicFadeOut]

        info = self.ImageQueueInfo(image_queue, musicEnd)

        self.window.initialize()
        self.window.setTransition('none')

        xbmc.enableNavSounds(False)

        self.playMusic(image_queue)

        if xbmc.getCondVisibility('Window.IsVisible(visualisation)'):
            DEBUG_LOG('Closing visualisation window')
            xbmc.executebuiltin('Action(back)')

        self.window.setTransition(image_queue.transition, image_queue.transitionDuration)

        action = None

        try:
            while image:
                DEBUG_LOG(' -IMAGE.QUEUE: {0}'.format(image))

                action = self.showImageFromQueue(image, info, first=True)

                if action:
                    if action == 'NEXT':
                        image = image_queue.next(extend=True) or image
                        continue
                    elif action == 'PREV':
                        image = image_queue.prev() or image
                        continue
                    elif action == 'BIG_NEXT':
                        self.window.setSkipNotice('+3')
                        image = image_queue.next(count=3, extend=True) or image
                        continue
                    elif action == 'BIG_PREV':
                        self.window.setSkipNotice('-3')
                        image = image_queue.prev(count=3) or image
                        continue
                    elif action == 'BACK':
                        DEBUG_LOG(' -IMAGE.QUEUE: Skipped after {0}secs'.format(int(time.time() - start)))
                        return False
                    elif action == 'SKIP':
                        DEBUG_LOG(' -IMAGE.QUEUE: Skipped after {0}secs'.format(int(time.time() - start)))
                        return True
                    else:
                        if action is True:
                            image_queue.mark(image)

                        image = image_queue.next(start)
                else:
                    return
        finally:
            kodiutil.setGlobalProperty('paused', '')
            xbmc.enableNavSounds(True)
            self.stopMusic(action != 'BACK' and image_queue or None)
            if self. window.hasAction():
                if self.window.getAction() == 'BACK':
                    return False
            self.window.clear()

        DEBUG_LOG(' -IMAGE.QUEUE: Finished after {0}secs'.format(int(time.time() - start)))
        return True

    def showVideoQueue(self, video_queue):
        pl = []
        for v in video_queue.queue:
            pl.append(v.path)
            video_queue.mark(v)

        self.playVideos(pl)

    def showVideo(self, video):
        if kodiutil.getSetting('allow.video.skip', True):
            if video.type == 'FEATURE':
                self.playVideos(None, features=[video])
                self.setSkinFeatureVars()
            else:
                self.playVideos([video])
        else:
            self.play(*self.getPathAndListItemFromVideo(video))

    def doAction(self, action):
        action.run()

    def next(self, prev=False):
        if not self.processor or self.processor.atEnd():
            return

        if not self.window.isOpen:
            self.abort()
            return

        if prev:
            playable = self.processor.prev()
        else:
            playable = self.processor.next()

        if playable is None:
            self.window.doClose()
            return

        DEBUG_LOG('Playing next item: {0}'.format(playable))

        if playable.type not in ('ACTION', 'COMMAND'):
            kodiutil.setGlobalProperty('module.current', playable.module._type)
            kodiutil.setGlobalProperty('module.current.name', playable.module.displayRaw())
            kodiutil.setGlobalProperty('module.next', self.processor.upNext() and self.processor.upNext().module._type or '')
            kodiutil.setGlobalProperty('module.next.name', self.processor.upNext() and self.processor.upNext().module.displayRaw() or '')

        if playable.type == 'IMAGE':
            try:
                action = self.showImage(playable)
            finally:
                self.window.clear()

            if action == 'BACK':
                self.next(prev=True)
            else:
                self.next()

        elif playable.type == 'IMAGE.QUEUE':
            if not self.showImageQueue(playable):
                self.next(prev=True)
            else:
                self.next()

        elif playable.type == 'VIDEO.QUEUE':
            self.showVideoQueue(playable)

        elif playable.type in ('VIDEO', 'FEATURE'):
            self.showVideo(playable)

        elif playable.type == 'ACTION':
            self.doAction(playable)
            self.next()

        else:
            DEBUG_LOG('NOT PLAYING: {0}'.format(playable))
            self.next()

    def abort(self):
        self.abortFlag.set()
        DEBUG_LOG('ABORT')
        self.window.doClose()
