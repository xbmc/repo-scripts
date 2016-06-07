#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2015 KenV99
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
import json
import threading

import xbmc
from resources.lib.events import Events
from resources.lib.pubsub import Publisher, Topic, Message
from resources.lib.utils.poutil import KodiPo

kodipo = KodiPo()
_ = kodipo.getLocalizedString


class PlayerPublisher(threading.Thread, Publisher):
    publishes = Events.Player.keys()

    def __init__(self, dispatcher, settings):
        assert settings is not None
        Publisher.__init__(self, dispatcher)
        threading.Thread.__init__(self, name='PlayerPublisher')
        self.dispatcher = dispatcher
        self.publishes = Events.Player.keys()
        self._abortevt = threading.Event()
        self._abortevt.clear()

    def run(self):
        publish = super(PlayerPublisher, self).publish
        player = Player()
        player.publish = publish
        while not self._abortevt.is_set():
            if player.isPlaying():
                player.playingTime = player.getTime()
            xbmc.sleep(500)
        del player

    def abort(self, timeout=0):
        self._abortevt.set()
        if timeout > 0:
            self.join(timeout)
            if self.is_alive():
                xbmc.log(msg=_('Could not stop PlayerPublisher T:%i') % self.ident)


class Player(xbmc.Player):
    def __init__(self):
        super(Player, self).__init__()
        self.publish = None
        self.totalTime = -1
        self.playingTime = 0
        self.info = {}

    def playing_type(self):
        """
        @return: [music|movie|episode|stream|liveTV|recordedTV|PVRradio|unknown]
        """
        substrings = ['-trailer', 'http://']
        isMovie = False
        if self.isPlayingAudio():
            return "music"
        else:
            if xbmc.getCondVisibility('VideoPlayer.Content(movies)'):
                isMovie = True
        try:
            filename = self.getPlayingFile()
        except RuntimeError:
            filename = ''
        if filename != '':
            if filename[0:3] == 'pvr':
                if xbmc.getCondVisibility('Pvr.IsPlayingTv'):
                    return 'liveTV'
                elif xbmc.getCondVisibility('Pvr.IsPlayingRecording'):
                    return 'recordedTV'
                elif xbmc.getCondVisibility('Pvr.IsPlayingRadio'):
                    return 'PVRradio'
                else:
                    for string in substrings:
                        if string in filename:
                            isMovie = False
                            break
        if isMovie:
            return "movie"
        elif xbmc.getCondVisibility('VideoPlayer.Content(episodes)'):
            # Check for tv show title and season to make sure it's really an episode
            if xbmc.getInfoLabel('VideoPlayer.Season') != "" and xbmc.getInfoLabel('VideoPlayer.TVShowTitle') != "":
                return "episode"
        elif xbmc.getCondVisibility('Player.IsInternetStream'):
            return 'stream'
        else:
            return 'unknown'

    def getTitle(self):
        if self.isPlayingAudio():
            tries = 0
            while xbmc.getInfoLabel('MusicPlayer.Title') is None and tries < 8:
                xbmc.sleep(250)
                tries += 1
            title = xbmc.getInfoLabel('MusicPlayer.Title')
            if title is None or title == '':
                return u'Kodi cannot detect title'
            else:
                return title
        elif self.isPlayingVideo():
            tries = 0
            while xbmc.getInfoLabel('VideoPlayer.Title') is None and tries < 8:
                xbmc.sleep(250)
                tries += 1
            if xbmc.getCondVisibility('VideoPlayer.Content(episodes)'):
                if xbmc.getInfoLabel('VideoPlayer.Season') != "" and xbmc.getInfoLabel('VideoPlayer.TVShowTitle') != "":
                    return '%s-S%sE%s-%s' % (xbmc.getInfoLabel('VideoPlayer.TVShowTitle'),
                                             xbmc.getInfoLabel('VideoPlayer.Season'),
                                             xbmc.getInfoLabel('VideoPlayer.Episode'),
                                             xbmc.getInfoLabel('VideoPlayer.Title'))
            else:
                title = xbmc.getInfoLabel('VideoPlayer.Title')
                if title is None or title == '':
                    try:
                        ret = json.loads(xbmc.executeJSONRPC(
                            '{"jsonrpc": "2.0", "method": "Player.GetItem", "params": { "properties": ["title"], "playerid": 1 }, "id": "1"}'))
                    except RuntimeError:
                        title = ''
                    else:
                        try:
                            title = ret[u'result'][u'item'][u'title']
                        except KeyError:
                            title = u'Kodi cannot detect title'
                        else:
                            if title == u'':
                                title = ret[u'result'][u'item'][u'label']
                            if title == u'':
                                title = u'Kodi cannot detect title'
                    return title
                else:
                    return title
        else:
            return u'Kodi cannot detect title - none playing'

    def getAudioInfo(self, playerid):
        try:
            info = json.loads(xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Player.GetItem", "params": { "properties": ["title", "album",'
                ' "artist", "duration", "file", "streamdetails"], "playerid": %s }, "id": "AudioGetItem"}'
                % playerid))['result']['item']
            if u'artist' in info.keys():
                t = info[u'artist']
                if isinstance(t, list) and len(t) > 0:
                    info[u'artist'] = t[0]
                elif isinstance(t, unicode):
                    if t != u'':
                        info[u'artist'] = t
                    else:
                        info[u'artist'] = u'unknown'
                else:
                    info[u'artist'] = u'unknown'
            else:
                info[u'artist'] = u'unknown'
            items = [u'duration', u'id', u'label', u'type']
            for item in items:
                try:
                    del info[item]
                except KeyError:
                    pass
            info[u'mediaType'] = u'audio'
        except RuntimeError:
            self.info = {}
        else:
            self.info = info

    def getVideoInfo(self, playerid):
        try:
            info = json.loads(xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Player.GetItem", "params": { "properties": ["title", "album",'
                ' "artist", "season", "episode", "duration", "showtitle", "tvshowid", "file",  "streamdetails"],'
                ' "playerid": %s }, "id": "VideoGetItem"}' % playerid))['result']['item']
        except RuntimeError:
            self.info = {}
        else:
            items = [u'label', u'id', u'tvshowid']
            for item in items:
                try:
                    del info[item]
                except KeyError:
                    pass
            items = {u'mediaType': u'type', u'fileName': u'file'}
            for item in items.keys():
                try:
                    t = items[item]
                    info[item] = info.pop(t, 'unknown')
                except KeyError:
                    info[item] = u'unknown'
            if info['mediaType'] != 'musicvideo':
                items = [u'artist', u'album']
                for item in items:
                    try:
                        del info[item]
                    except KeyError:
                        pass
            else:
                try:
                    info[u'artist'] = info[u'artist'][0]
                except (KeyError, IndexError):
                    info[u'artist'] = u'unknown'
            if u'streamdetails' in info.keys():
                sd = info.pop(u'streamdetails', {})
                try:
                    info[u'stereomode'] = sd[u'video'][0][u'stereomode']
                except (KeyError, IndexError):
                    info[u'stereomode'] = u'unknown'
                else:
                    if info[u'stereomode'] == u'':
                        info[u'stereomode'] = u'unknown'
                try:
                    info[u'width'] = unicode(sd[u'video'][0][u'width'])
                except (KeyError, IndexError):
                    info[u'width'] = u'unknown'
                try:
                    info[u'height'] = unicode(sd[u'video'][0][u'height'])
                except (KeyError, IndexError):
                    info[u'height'] = u'unknown'
                try:
                    info[u'aspectRatio'] = unicode(int((sd[u'video'][0][u'aspect'] * 100.0) + 0.5) / 100.0)
                except (KeyError, IndexError):
                    info[u'aspectRatio'] = u'unknown'
            if info[u'mediaType'] == u'episode':
                items = [u'episode', u'season']
                for item in items:
                    try:
                        info[item] = unicode(info[item]).zfill(2)
                    except KeyError:
                        info[item] = u'unknown'
            else:
                items = [u'episode', u'season', u'showtitle']
                for item in items:
                    try:
                        del info[item]
                    except KeyError:
                        pass
            self.info = info

    def getInfo(self):
        tries = 0
        while tries < 8 and self.isPlaying() is False:
            xbmc.sleep(250)
        try:
            player = json.loads(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}'))
        except RuntimeError:
            playerid = -1
            playertype = 'none'
        else:
            try:
                playerid = player['result'][0]['playerid']
                playertype = player['result'][0]['type']
            except KeyError:
                playerid = -1
                playertype = 'none'
        if playertype == 'audio':
            self.getAudioInfo(playerid)
            self.rectifyUnknowns()
        elif playertype == 'video':
            self.getVideoInfo(playerid)
            self.rectifyUnknowns()
        else:
            self.info = {}

    def rectifyUnknowns(self):
        items = {u'fileName': self.getPlayingFileX, u'aspectRatio': self.getAspectRatio, u'height': self.getResoluion,
                 u'title': self.getTitle}
        for item in items.keys():
            if item not in self.info.keys():
                self.info[item] = items[item]()
            else:
                try:
                    if self.info[item] == '' or self.info[item] == u'unknown':
                        self.info[item] = items[item]()
                except KeyError:
                    pass
        pt = self.playing_type()
        if u'mediaType' not in self.info.keys():
            self.info[u'mediaType'] = pt
        else:
            try:
                if pt != u'unknown' and self.info[u'mediaType'] != pt:
                    self.info[u'mediaType'] = pt
            except KeyError:
                pass

    def getPlayingFileX(self):
        try:
            fn = self.getPlayingFile()
        except RuntimeError:
            fn = u'unknown'
        if fn is None or fn == '':
            fn = u'unknown'
        return xbmc.translatePath(fn)

    @staticmethod
    def getAspectRatio():
        ar = xbmc.getInfoLabel("VideoPlayer.VideoAspect")
        if ar is None:
            ar = u'unknown'
        elif ar == '':
            ar = u'unknown'
        return str(ar)

    @staticmethod
    def getResoluion():
        vr = xbmc.getInfoLabel("VideoPlayer.VideoResolution")
        if vr is None:
            vr = u'unknown'
        elif vr == '':
            vr = u'unknown'
        return str(vr)

    def onPlayBackStarted(self):
        self.getInfo()
        try:
            self.totalTime = self.getTotalTime()
        except RuntimeError:
            self.totalTime = -1
        finally:
            if self.totalTime == 0:
                self.totalTime = -1
        topic = Topic('onPlayBackStarted')
        self.publish(Message(topic, **self.info))

    def onPlayBackEnded(self):
        topic = Topic('onPlayBackEnded')
        try:
            tt = self.totalTime
            tp = self.playingTime
            pp = int(100 * tp / tt)
        except RuntimeError:
            pp = -1
        except OverflowError:
            pp = -1
        self.publish(Message(topic, percentPlayed=str(pp), **self.info))
        self.totalTime = -1.0
        self.playingTime = 0.0
        self.info = {}

    def onPlayBackStopped(self):
        self.onPlayBackEnded()

    def onPlayBackPaused(self):
        topic = Topic('onPlayBackPaused')
        self.publish(Message(topic, time=str(self.getTime()), **self.info))

    def onPlayBackResumed(self):
        topic = Topic('onPlayBackResumed')
        self.publish(Message(topic, time=str(self.getTime()), **self.info))

    def onPlayBackSeek(self, time, seekOffset):
        topic = Topic('onPlayBackSeek')
        self.publish(Message(topic, time=str(time), **self.info))

    def onPlayBackSeekChapter(self, chapter):
        topic = Topic('onPlayBackSeekChapter')
        self.publish(Message(topic, chapter=str(chapter), **self.info))

    def onPlayBackSpeedChanged(self, speed):
        topic = Topic('onPlayBackSpeedChanged')
        self.publish(Message(topic, speed=str(speed), **self.info))

    def onQueueNextItem(self):
        topic = Topic('onQueueNextItem')
        self.publish(Message(topic, **self.info))
