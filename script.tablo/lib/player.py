import xbmc
import xbmcgui
import threading
import copy
import os
import urllib

from lib import util
from lib.tablo import bif
from lib.windows import kodigui
from lib.util import T


class TrickModeWindow(kodigui.BaseWindow):
    name = 'TRICKMODE'
    xmlFile = 'script-tablo-trick-mode.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'

    IMAGE_LIST_ID = 100

    PROGRESS_IMAGE_ID = 200
    PROGRESS_SELECT_IMAGE_ID = 201
    PROGRESS_WIDTH = 880
    PROGRESS_SELECT_IMAGE_X = 199
    PROGRESS_SELECT_IMAGE_Y = -50

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.url = kwargs.get('url')
        self.callback = kwargs.get('callback')
        self.playlist = kwargs.get('playlist')
        self.select = None
        self.maxTimestamp = 0
        self._duration = 0

        self.trickPath = os.path.join(util.PROFILE, 'trick')
        if not os.path.exists(self.trickPath):
            os.makedirs(self.trickPath)

        self.getBif()

    def onFirstInit(self):
        self.imageList = kodigui.ManagedControlList(self, self.IMAGE_LIST_ID, 4)
        self.progressImage = self.getControl(self.PROGRESS_IMAGE_ID)
        self.progressSelectImage = self.getControl(self.PROGRESS_SELECT_IMAGE_ID)

        self.fillImageList()

        self.setProperty('end', util.durationToShortText(self.duration))

    def onAction(self, action):
        try:
            self.updateProgressSelection()

            if action in (xbmcgui.ACTION_STOP, xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                self.callback(False)
                self.doClose()
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID != self.IMAGE_LIST_ID:
            return

        item = self.imageList.getSelectedItem()
        if not item:
            return

        if self.bif:
            timestamp = item.dataSource['timestamp']
        else:
            timestamp = float(item.getProperty('timestamp'))

        self.setProgress(timestamp)
        self.callback(timestamp)

    def onFocus(self, controlID):
        if self.select is not None:
            self.imageList.selectItem(self.select)
            self.select = None

    @property
    def duration(self):
        return self._duration or self.maxTimestamp

    def blank(self):
        self.setProperty('show', '')

    def unBlank(self):
        self.setProperty('show', '1')

    def setPosition(self, position):
        position = min(position, self.maxTimestamp)

        self.setProperty('current', util.durationToShortText(position))

        util.DEBUG_LOG('TrickMode: Setting position at {0} of {1}'.format(position, self.duration))

        if not (self.maxTimestamp):
            return

        self.setProgress(position)
        self.setProgressSelect(position)

        if self.bif:
            i = -1
            for i, frame in enumerate(self.bif.frames):
                if position > frame['timestamp']:
                    continue
                break
            i -= 1

            if i >= 0:
                self.select = i
        else:
            timestamp = 0
            for i, segment in enumerate(self.playlist.segments):
                timestamp += segment.duration
                if timestamp > position:
                    self.select = i
                    break
            else:
                self.select = 0

    def setProgress(self, position):
        if not self.started:
            return
        w = int((position / float(self.duration)) * self.PROGRESS_WIDTH) or 1
        self.progressImage.setWidth(w)

    def setProgressSelect(self, position):
        if not self.started:
            return

        x = self.PROGRESS_SELECT_IMAGE_X + int((position / float(self.maxTimestamp)) * self.PROGRESS_WIDTH)
        self.progressSelectImage.setPosition(x, self.PROGRESS_SELECT_IMAGE_Y)

        self.setProperty('select', util.durationToShortText(position))

    def updateProgressSelection(self):
        item = self.imageList.getSelectedItem()
        if not item:
            return

        self.setProgressSelect(float(item.getProperty('timestamp')))

    def cleanTrickPath(self):
        for f in os.listdir(self.trickPath):
            os.remove(os.path.join(self.trickPath, f))

    def getBif(self):
        self.bif = None
        if not self.url:
            return

        self.cleanTrickPath()
        bifPath = os.path.join(self.trickPath, 'bif')
        urllib.urlretrieve(self.url, bifPath)
        self.bif = bif.Bif(bifPath)
        self.bif.dumpImages(self.trickPath)
        self.maxTimestamp = self.bif.maxTimestamp
        util.DEBUG_LOG('TrickMode: Bif frames ({0}) - max timestamp ({1})'.format(self.bif.size, self.bif.maxTimestamp))

    def fillImageList(self):
        items = []

        if self.bif:
            for i in range(self.bif.size):
                timestamp = self.bif.frames[i]['timestamp']
                item = kodigui.ManagedListItem(
                    str(timestamp),
                    thumbnailImage=os.path.join(self.trickPath, str(i) + '.jpg'),
                    data_source=self.bif.frames[i]
                )
                item.setProperty('timestamp', str(timestamp))
                items.append(item)
        else:
            timestamp = 0
            for segment in self.playlist.segments:
                item = kodigui.ManagedListItem(
                    str(timestamp),
                    thumbnailImage='',
                    data_source=segment
                )
                item.setProperty('timestamp', str(timestamp))
                self.maxTimestamp = timestamp
                timestamp += segment.duration

                items.append(item)

            self._duration = self.maxTimestamp

        self.imageList.addItems(items)


class ThreadedWatch(object):
    def __init__(self, airing, dialog):
        self.dialog = dialog
        self.airing = airing
        self.watch = None
        self.thread = None

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def start(self):
        self.thread = threading.Thread(target=self.watchThread)
        self.thread.start()
        return self

    def watchThread(self):
        util.DEBUG_LOG('ThreadedWatch: Started')
        self.watch = self.airing.watch()
        util.DEBUG_LOG('ThreadedWatch: Finished')

    def getWatch(self):
        util.DEBUG_LOG('ThreadedWatch: getWatch - Started')
        while self.thread.isAlive() and not self.dialog.canceled:
            self.thread.join(0.1)
        util.DEBUG_LOG('ThreadedWatch: getWatch - Finished')
        return self.watch


class PlayerHandler(object):
    def __init__(self, player):
        self.player = player
        self._thread = threading.Thread()
        self.init()

    def init(self):
        pass

    def play(self):
        raise NotImplementedError

    def startWait(self):
        if not self._thread.isAlive():
            self._thread = threading.Thread(target=self.wait)
            self._thread.start()

    def onPlayBackStarted(self):
        pass

    def onPlayBackStopped(self):
        pass

    def onPlayBackEnded(self):
        pass

    def onPlayBackSeek(self, time, offset):
        pass

    def onPlayBackFailed(self):
        pass

    def onVideoWindowClosed(self):
        pass

    def onVideoWindowOpened(self):
        pass

    def waitForStop(self):
        self._waiting.wait()


class RecordingHandler(PlayerHandler):
    def init(self):
        self.playlistFilename = os.path.join(util.PROFILE, 'pl.m3u8')
        self.reset()

    def reset(self):
        self.airing = None
        self.watch = None
        self.trickWindow = None
        self.item = None
        self.finished = False
        self.startPosition = 0
        self.softReset()

    def softReset(self):
        self._waiting = threading.Event()
        self._waiting.set()
        self.position = 0
        self.seeking = False
        self.playlist = None
        self.segments = None

    @property
    def absolutePosition(self):
        return self.startPosition + self.position

    def makeSeekedPlaylist(self, position):
        m = self.playlist
        m.segments = copy.copy(self.segments)
        if position > 0:
            duration = m.segments[0].duration
            while duration < position:
                del m.segments[0]
                if not m.segments:
                    break
                duration += m.segments[0].duration

        m.dump(self.playlistFilename)

    def setupTrickMode(self, watch):
        self.trickWindow = TrickModeWindow.create(url=watch.bifHD, callback=self.trickWindowCallback, playlist=self.watch.getSegmentedPlaylist())

    def play(self, rec, show=None, resume=True):
        self.reset()
        self.airing = rec
        watch = rec.watch()
        if watch.error:
            return watch.error

        self.watch = watch
        title = rec.title or (show and show.title or '{0} {1}'.format(rec.displayChannel(), rec.network))
        thumb = show and show.thumb or ''
        self.item = xbmcgui.ListItem(title, title, thumbnailImage=thumb, path=watch.url)
        self.item.setInfo('video', {'title': title, 'tvshowtitle': title})
        self.item.setIconImage(thumb)

        self.playlist = watch.getSegmentedPlaylist()
        self.segments = copy.copy(self.playlist.segments)

        self.setupTrickMode(watch)

        if rec.position and resume:
            util.DEBUG_LOG('Player (Recording): Resuming at {0}'.format(rec.position))
            self.playAtPosition(rec.position)
        else:
            util.DEBUG_LOG('Player (Recording): Playing from beginning')
            self.playAtPosition(0)
            # self.player.play(watch.url, self.item, False, 0)

        return None

    def trickWindowCallback(self, position):
        if position is False:
            return self.finish(force=True)
        self.playAtPosition(position)

    def playAtPosition(self, position):
        self.startPosition = position
        self.position = 0
        self.makeSeekedPlaylist(position)
        self.trickWindow.setPosition(self.absolutePosition)

        self.player.play(self.playlistFilename, self.item, False, 0)

    def wait(self):
        self._waiting.clear()
        try:
            cacheCount = 0
            while (self.player.isPlayingVideo() or self.seeking) and not xbmc.abortRequested:
                if xbmc.getCondVisibility('Player.Seeking'):
                    self.onPlayBackSeek(self.position, 0)
                elif self.player.isPlayingVideo():
                    self.position = self.player.getTime()
                xbmc.sleep(100)

                if xbmc.getCondVisibility('Player.Caching') and self.position - self.startPosition < 10:
                    cacheCount += 1
                    if cacheCount > 4 and not xbmc.getCondVisibility('IntegerGreaterThan(Player.CacheLevel,0)'):
                        util.DEBUG_LOG(
                            'Player (Recording): Forcing resume at {0} - cache level: {1}'.format(self.position, xbmc.getInfoLabel('Player.CacheLevel'))
                        )
                        xbmc.executebuiltin('PlayerControl(play)')
                        cacheCount = 0
                else:
                    cacheCount = 0

            if self.position:
                util.DEBUG_LOG('Player (Recording): Saving position [{0}]'.format(self.absolutePosition))
                self.airing.setPosition(self.absolutePosition)
        finally:
            self._waiting.set()

            self.finish()

    def onPlayBackStarted(self):
        try:
            self.trickWindow.setPosition(self.absolutePosition)
            self.trickWindow.blank()
        except:
            util.ERROR()

        self.startWait()

    def onPlayBackSeek(self, time, offset):
        if self.seeking:
            return
        self.seeking = True

        self.trickWindow.setPosition(self.absolutePosition)
        self.trickWindow.unBlank()
        if self.player.isPlayingVideo():
            util.DEBUG_LOG('Player (Recording): Stopping video for seek')
            self.player.stop()
        util.DEBUG_LOG('Player (Recording): Seek started at {0} (absolute: {1})'.format(self.position, self.absolutePosition))

    def onPlaybackFailed(self):
        self.finish(force=True)

    def onVideoWindowOpened(self):
        self.seeking = False

    def onVideoWindowClosed(self):
        if not self.seeking:
            if self.player.isPlayingVideo():
                util.DEBUG_LOG('Player (Recording): Stopping video on video window closed')
                self.player.stop()

    def closeTrickWindow(self):
        try:
            if not self.trickWindow:
                return

            util.DEBUG_LOG('Player (Recording): Closing trick window')

            self.trickWindow.doClose()
            del self.trickWindow
        except AttributeError:
            pass

        self.trickWindow = None

    def finish(self, force=False):
        if self.finished:
            return

        self.finished = True
        self.seeking = False

        util.DEBUG_LOG('Player (Recording): Played for {0} seconds'.format(self.position))

        self.closeTrickWindow()


class LiveRecordingHandler(RecordingHandler):
    def reset(self):
        self.loadingDialog = None
        self.seekableEnded = False
        RecordingHandler.reset(self)

    def softReset(self):
        self.nextPlay = None
        RecordingHandler.softReset(self)

    def checkForNext(self):
        util.DEBUG_LOG('Player (Recording): Checking for remaining live portion')
        if not self.seekableEnded or not self.nextPlay:
            self.finish()
            return

        util.DEBUG_LOG('Player (Recording): Playing live portion')
        url = self.nextPlay

        self.softReset()

        self.loadingDialog = util.LoadingDialog().show()
        self.closeTrickWindow()

        self.startPosition = self.absolutePosition
        self.position = 0

        self.player.play(url, self.item, False, 0)

    def playAtPosition(self, position):
        self.startPosition = position
        self.position = 0
        self.makeSeekedPlaylist(position)
        self.trickWindow.setPosition(self.absolutePosition)

        with open(self.playlistFilename, 'a') as f:
            f.write('\n#EXT-X-ENDLIST')
        self.nextPlay = self.watch.url

        self.player.play(self.playlistFilename, self.item, False, 0)

    def saveLivePosition(self):
        if self.position:
            util.DEBUG_LOG('Player (Recording): Live - saving position [{0}]'.format(self.absolutePosition))
            self.airing.setPosition(self.absolutePosition)

    def wait(self):
        RecordingHandler.wait(self)
        self.checkForNext()

    def waitLive(self):
        if not self._thread.isAlive():
            self._thread = threading.Thread(target=self._waitLive)
            self._thread.start()

    def _waitLive(self):
        self._waiting.clear()
        try:
            while self.player.isPlayingVideo() and not xbmc.abortRequested:
                self.position = self.player.getTime()
                xbmc.sleep(100)
        finally:
            self._waiting.set()

            self.saveLivePosition()

    def onPlayBackStarted(self):
        if not self.nextPlay:
            self.waitLive()
            return
        RecordingHandler.onPlayBackStarted(self)

    def onPlayBackEnded(self):
        if self.nextPlay:
            self.seeking = False
            self.seekableEnded = True

    def onPlayBackSeek(self, time, offset):
        if not self.nextPlay:
            return
        RecordingHandler.onPlayBackSeek(self, time, offset)

    def onVideoWindowOpened(self):
        self.seeking = False
        if not self.nextPlay:
            self.closeLoadingDialog()

    def onVideoWindowClosed(self):
        if not self.nextPlay:
            self.closeTrickWindow()
            return

        RecordingHandler.onVideoWindowClosed(self)

    def finish(self, force=False):
        if not force:
            if self.seekableEnded:
                return
        RecordingHandler.finish(self)

    def closeLoadingDialog(self):
        if self.loadingDialog:
            self.loadingDialog.close()
        self.loadingDialog = None


class LiveTVHandler(PlayerHandler):
    def init(self):
        self.loadingDialog = None
        self.reset()

    def reset(self):
        self.airing = None

        self.closeLoadingDialog()
        self.softReset()

    def softReset(self):
        self._waiting = threading.Event()
        self._waiting.set()

    def play(self, airing):
        self.reset()
        self.airing = airing

        self.loadingDialog = util.LoadingDialog().show()

        threading.Thread(target=self._playAiringChannel).start()

    def _playAiringChannel(self):
        airing = self.airing

        with ThreadedWatch(airing, self.loadingDialog) as tw:
            watch = tw.getWatch()
            if watch:
                if watch.error:
                    util.DEBUG_LOG('Player (LiveTV): Watch error: {0}'.format(watch.error))
                    xbmcgui.Dialog().ok(T(32196), T(32197), ' ', str(watch.errorDisplay))
                    self.closeLoadingDialog()
                    return watch.error
                util.DEBUG_LOG('Player (LiveTV): Watch URL: {0}'.format(watch.url))
            else:
                util.DEBUG_LOG('Player (LiveTV): Canceled before start')
                self.closeLoadingDialog()
                return

        self.watch = watch
        title = '{0} {1}'.format(airing.displayChannel(), airing.network)
        thumb = airing.thumb
        li = xbmcgui.ListItem(title, title, thumbnailImage=thumb, path=watch.url)
        li.setInfo('video', {'title': title, 'tvshowtitle': title})
        li.setIconImage(thumb)

        util.DEBUG_LOG('Player (LiveTV): Playing channel')

        self.player.play(watch.url, li, False, 0)
        self.loadingDialog.wait()

        return None

    def wait(self):
        self._waiting.clear()
        try:
            while self.player.isPlayingVideo() and not xbmc.abortRequested:
                xbmc.sleep(100)
        finally:
            self._waiting.set()

    def onPlayBackStarted(self):
        self.startWait()

    def onVideoWindowOpened(self):
        self.closeLoadingDialog()

    def onVideoWindowClosed(self):
        if self.player.isPlayingVideo():
            util.DEBUG_LOG('Player (LiveTV): Stopping video')
            self.player.stop()

    def closeLoadingDialog(self):
        if self.loadingDialog:
            self.loadingDialog.close()
        self.loadingDialog = None


class TabloPlayer(xbmc.Player):
    def init(self):
        self.reset()
        self.monitor()
        return self

    def reset(self):
        self.started = False
        self.handler = None

    def playAiringChannel(self, airing):
        self.reset()
        self.handler = LiveTVHandler(self)
        return self.handler.play(airing)

    def playRecording(self, rec, show=None, resume=True):
        self.reset()
        self.handler = RecordingHandler(self)
        return self.handler.play(rec, show, resume)

    def playLiveRecording(self, rec, show=None, resume=True):
        self.reset()
        self.handler = LiveRecordingHandler(self)
        return self.handler.play(rec, show, resume)

    def onPlayBackStarted(self):
        self.started = True
        util.DEBUG_LOG('Player - STARTED')
        if not self.handler:
            return
        self.handler.onPlayBackStarted()

    def onPlayBackStopped(self):
        if not self.started:
            self.onPlaybackFailed()

        util.DEBUG_LOG('Player - STOPPED' + (not self.started and ': FAILED' or ''))
        if not self.handler:
            return
        self.handler.onPlayBackStopped()

    def onPlayBackEnded(self):
        if not self.started:
            self.onPlaybackFailed()

        util.DEBUG_LOG('Player - ENDED' + (not self.started and ': FAILED' or ''))
        if not self.handler:
            return
        self.handler.onPlayBackEnded()

    def onPlayBackSeek(self, time, offset):
        util.DEBUG_LOG('Player - SEEK')
        if not self.handler:
            return
        self.handler.onPlayBackSeek(time, offset)

    def onPlaybackFailed(self):
        if not self.handler:
            return
        self.handler.onPlayBackFailed()

    def onVideoWindowOpened(self):
        util.DEBUG_LOG('Player: Video window opened')
        try:
            self.handler.onVideoWindowOpened()
        except:
            util.ERROR()

    def onVideoWindowClosed(self):
        util.DEBUG_LOG('Player: Video window closed')
        try:
            self.handler.onVideoWindowClosed()
            self.stop()
        except:
            util.ERROR()

    def stopAndWait(self):
        if self.isPlayingVideo():
            util.DEBUG_LOG('Player (Recording): Stopping for external wait')
            self.stop()
            self.handler.waitForStop()

    def monitor(self):
        threading.Thread(target=self._monitor).start()

    def _monitor(self):

        while not xbmc.abortRequested:
            # Monitor loop
            if self.isPlayingVideo():
                util.DEBUG_LOG('Player: Monitoring')

            hasFullScreened = False

            while self.isPlayingVideo() and not xbmc.abortRequested:
                xbmc.sleep(100)
                if xbmc.getCondVisibility('VideoPlayer.IsFullscreen'):
                    if not hasFullScreened:
                        hasFullScreened = True
                        self.onVideoWindowOpened()
                elif hasFullScreened and not xbmc.getCondVisibility('Window.IsVisible(busydialog)'):
                    hasFullScreened = False
                    self.onVideoWindowClosed()

            if hasFullScreened:
                self.onVideoWindowClosed()

            # Idle loop
            if not self.isPlayingVideo():
                util.DEBUG_LOG('Player: Idling...')

            while not self.isPlayingVideo() and not xbmc.abortRequested:
                xbmc.sleep(100)

PLAYER = TabloPlayer().init()
