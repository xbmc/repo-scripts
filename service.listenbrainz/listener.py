# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with Kodi; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
import time

import xbmc

from utils import (
    __version__, LANGUAGE, notification,
    log, read_file, write_file, read_settings,
    Listen, listenbrainz,
)
from helpers import is_local

SESSION = 'listener'


class Main(object):
    def __init__(self):
        # get addon settings
        self._get_settings()
        # initialize variables
        self._init_vars()
        # initial token validation
        listenbrainz.validate_token()
        # read listen cache from file
        log('read from file from disk', SESSION)
        data = read_file(self.file)
        if data:
            self.queue = data
        # start daemon
        self.monitor.waitForAbort()

    def _get_settings(self, puser=False, ptoken=False, pserver=False):
        log('get settings', SESSION)
        # if available, pass the old user and token to readsettings
        settings = read_settings(SESSION, puser, ptoken, pserver)
        user = settings['user']
        token = settings['token']
        server = settings['server']
        songs = settings['songs']
        videos = settings['videos']
        radio = settings['radio']
        # init the player class (re-init when settings have changed)
        self.player = MyPlayer(
            action=self._listenbrainz_submit,
            user=user,
            token=token,
            server=server,
            songs=songs,
            videos=videos,
            radio=radio)
        # init the monitor class (re-init when settings have changed)
        self.monitor = MyMonitor(
            action=self._get_settings,
            user=user,
            token=token,
            server=server)
        if not listenbrainz.validate_server():
            notification(LANGUAGE(32011), LANGUAGE(32029), time=12000)

    def _init_vars(self):
        # init vars
        self.queue = []
        self.file = 'listenbrainz.xml'

    def _listenbrainz_submit(self, listen):
        tstamp = int(round(time.time()))
        # check if there's something in our queue for submission
        log('submission queue %s' % str(self.queue), SESSION)
        if self.queue:
            self._listenbrainz_listen(tstamp)
        # check if there's something to announce (playback ended/stopped will
        # call us with None)
        if listen:
            # nowplaying announce
            self._listenbrainz_nowplaying(listen)
            # add track to the submission queue
            self.queue.extend([listen])
            # save queue to disk
            log('save file to disk', SESSION)
            write_file(self.file, self.queue)

    def _listenbrainz_nowplaying(self, listen):
        # update now playing status on ListenBrainz
        log('nowplaying', SESSION)
        result = listenbrainz.submit_playingnow(listen)
        if not result:
            return
        # parse response
        if 'status' in result and result['status'] == 'ok':
            return
        elif 'error' in result:
            msg = result['error']
            notification(LANGUAGE(32011), msg, time=7000)
            log('ListenBrainz nowplaying returned failed response: %s' %
                msg, SESSION)
            return
        else:
            log('ListenBrainz returned an unknown nowplaying response',
                SESSION)
            return

    def _listenbrainz_listen(self, tstamp):
        # submit track
        log('listening', SESSION)
        # check the backlog
        if len(self.queue) > 250:
            # something is wrong, reset the queue
            self.queue = []
            log('error: queue exceeded 250 items', SESSION)
            return
        # we are allowed to submit max 50 tracks in one go
        submitlist = self.queue[:50]
        qualified = []
        unqualified = []
        for listen in submitlist:
            # only submit items that are at least 30 secs long and have been
            # played at least half or at least 4 minutes
            listen_time = tstamp - int(round(listen.timestamp))
            half_duration = int(round(listen.metadata['duration']))//2
            if (int(listen.metadata['duration']) > 30) and (
                    listen_time > half_duration or listen_time > 240):
                qualified.append(listen)
            else:
                # item does not qualify for a listen
                unqualified.append(listen)
        # remove tracks from the queue that don't qualify
        self._remove_invalid(unqualified)
        # check if we have any valid tracks to submit
        if not qualified:
            # sync queue to disk
            log('save file to disk', SESSION)
            write_file(self.file, self.queue)
            return

        result = listenbrainz.import_listens(qualified)

        # in case we don't get a response
        if not result:
            # sync queue to disk
            log('save file to disk', SESSION)
            write_file(self.file, self.queue)
            return
        # parse response
        if 'status' in result and result['status'] == 'ok':
            # remove submitted items from the list
            self.queue = self.queue[50:]
        elif 'error' in result:
            code = result['code']
            msg = result['error']
            notification(LANGUAGE(32011), msg, time=7000)
            log('ListenBrainz listen returned failed response: %s' % msg,
                SESSION)
            # evaluate error response
            # flush the queue unless it's a temp error on ListenBrainz side
            codes_to_retry = [
                401,  # APIUnauthorized, should be resolved by fixing token
                500,  # APIInternalServerError, hopefully temporary!
                503,  # APIServiceUnavailable, hopefully temporary!
            ]
            if code not in codes_to_retry:
                self.queue = []
        else:
            log('ListenBrainz returned an unknown listen response', SESSION)
            # unknown error. flush the queue
            self.queue = []
        # sync queue to disk
        log('save file to disk', SESSION)
        write_file(self.file, self.queue)

    def _remove_invalid(self, unqualified):
        log('removing unqualified items from the list', SESSION)
        # iterate over the invalid items and remove them from the queue
        for item in unqualified:
            self.queue.remove(item)


class MyPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        log('init player class', SESSION)
        self.action = kwargs['action']
        self.user = kwargs['user']
        self.token = kwargs['token']
        self.songs = kwargs['songs']
        self.videos = kwargs['videos']
        self.radio = kwargs['radio']
        self.Audio = False

    def onPlayBackStarted(self):
        # only do something if we're playing audio and user has enabled it in
        # settings
        if self.user and self.token:
            if (self.isPlayingAudio() and (self.radio or self.songs)) or (
                    self.isPlayingMusicVideo() and self.videos):
                # we need to keep track of this bool for stopped/ended
                # notifications
                self.Audio = True
                log('onPlayBackStarted', SESSION)
                # tags are not available instantly and we don't what to
                # announce right away as the user might be skipping through the
                # songs
                xbmc.sleep(500)
                # don't announce if the user already skipped to the next track
                # or stopped playing audio
                if self.isPlayingAudio() or self.isPlayingMusicVideo():
                    # get tags
                    listen = self._get_listen()
                    # check if we have anything to submit
                    if listen:
                        # announce song
                        self.action(listen)

    def onPlayBackEnded(self):
        # ignore onPlayBackEnded notifications from the video player
        if self.Audio:
            # music playback ended
            self.Audio = False
            log('onPlayBackEnded', SESSION)
            # submit any remaining tracks
            self.action(None)

    def onPlayBackStopped(self):
        # ignore onPlayBackStopped notifications from the video player
        if self.Audio:
            # we stopped playing audio
            self.Audio = False
            log('onPlayBackStopped', SESSION)
            # submit any remaining tracks
            self.action(None)

    def _get_listen(self):
        timestamp = int(round(time.time()))
        tag_overrides = {}
        # get track tags
        if self.isPlayingAudio():
            tags = self.getMusicInfoTag()
        elif self.isPlayingVideo():
            tags = self.getVideoInfoTag()
            tag_overrides['artist_name'] = tags.getArtist()[0]
        else:
            return None  # Not playing music or video

        # get duration from xbmc.Player if the MusicInfoTag duration is invalid
        if int(round(tags.getDuration())) <= 0:
            tag_overrides['duration'] = int(round(self.getTotalTime()))

        log('"tags" set to: {}'.format(dir(tags)), SESSION)
        log('"tag_overrides" set to: {}'.format(tag_overrides), SESSION)
        listen = Listen(tags, timestamp=timestamp, **tag_overrides)
        artist = listen.metadata['artist_name']
        title = listen.metadata['track_name']

        path = self.getPlayingFile()
        if is_local(path):
            userselected = '1'
        else:
            userselected = '0'
        log('song listening enabled: ' + str(self.songs), SESSION)
        log('video listening enabled: ' + str(self.videos), SESSION)
        log('radio listening enabled: ' + str(self.radio), SESSION)
        log('listen metadata: {}'.format(listen.metadata), SESSION)
        log('path: ' + str(path), SESSION)
        log('user selected flag: ' + userselected, SESSION)
        # streaming radio may provide both artistname and songtitle as
        # one label, or we have a file with no tags
        # NOTE - this is against the last.fm scrobbling rules:
        # "Do not attempt to determine a track's meta data from its
        # filename. Please only use meta data from well-structured
        # sources such as ID3 tags."
        if title and not artist:
            try:
                artist = title.split(' - ')[0]
                title = title.split(' - ')[1]
                if artist[2] == '.' and title[-4] == '.':
                    # assume file without tags %N. %A - %T.ext
                    artist = artist[3:].strip()
                    title = title[:-4].strip()
                log('extracted artist: ' + artist, SESSION)
                log('extracted title: ' + title, SESSION)
                listen.metadata['artist_name'] = artist
                listen.metadata['track_name'] = title
            except BaseException:
                log('failed to extract artist from title', SESSION)
                pass
        # make sure we have artist and trackname
        if artist and title:
            # check settings to determine if we should submit this track
            if userselected == '1' and not self.songs:
                # listening to local source, but songs setting is disabled
                log('settings prohibit us from submitting listens for '
                    'local tracks', SESSION)
                return None
            elif userselected == '0' and not self.radio:
                # listening to remote source, but the radio setting is disabled
                log('settings prohibit us from submitting listens for '
                    'online streaming radio', SESSION)
                return None
            elif self.isPlayingMusicVideo() and not self.videos:
                # watching a music video, but the music video setting is
                # disabled
                log('settings prohibit us from submitting listens for '
                    'music videos', SESSION)
                return None
            # previous clauses did not return, so we have either a local
            # play with the songs setting enabled, or a remote play with
            # the radio setting enabled, and therefore can submit listens
            log('listen: %s' % listen.metadata, SESSION)
            return listen
        else:
            log('cannot submit listen for track with no artist and '
                'track information', SESSION)
            return None

    def isPlayingMusicVideo(self):
        return self.isPlayingVideo() \
               and self.getVideoInfoTag().getMediaType() == 'musicvideo'


class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        log('init monitor class', SESSION)
        self.user = kwargs['user']
        self.token = kwargs['token']
        self.server = kwargs['server']
        self.action = kwargs['action']

    def onSettingsChanged(self):
        log('onSettingsChanged', SESSION)
        # sleep before retrieving the new settings
        xbmc.sleep(500)
        # pass the previous user and pass to getsettings, so we can check if
        # they have changed
        self.action(self.user, self.token, self.server)


if (__name__ == "__main__"):
    log('script version %s started' % __version__, SESSION)
    Main()
log('script stopped', SESSION)
