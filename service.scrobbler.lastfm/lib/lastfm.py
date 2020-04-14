from lib.helpers import *
from lib.utils import *

SESSION = 'scrobbler'


class Main():
    def __init__(self):
        # get addon settings
        self._get_settings()
        # initialize variables
        self._init_vars()
        # read scrobble cache from file
        log('read from file from disk', SESSION)
        data = read_file(self.file)
        if data:
            self.queue = data
        # start daemon
        self.monitor.waitForAbort()
        # clear skin properties
        clear_prop('LastFM.CanLove')

    def _get_settings(self, puser=False, ppwd=False):
        log('get settings', SESSION)
        # if available, pass the old user and pwd to readsettings
        settings = read_settings(SESSION, puser, ppwd)
        user = settings['user']
        pwd = settings['pwd']
        songs = settings['songs']
        videos = settings['videos']
        radio = settings['radio']
        self.sesskey = settings['sesskey']
        # init the player class (re-init when settings have changed)
        self.player = MyPlayer(action=self._lastfm_submit, user=user, pwd=pwd, songs=songs, videos=videos, radio=radio, sesskey=self.sesskey)
        # init the monitor class (re-init when settings have changed)
        self.monitor = MyMonitor(action=self._get_settings, user=user, pwd=pwd)

    def _init_vars(self):
        # init vars
        self.queue = []
        self.file = 'lastfm.xml'

    def _lastfm_submit(self, tags):
        tstamp = int(time.time())
        # check if there's something in our queue for submission
        log('submission queue %s' % str(self.queue), SESSION)
        if self.queue:
            self._lastfm_scrobble(tstamp)
        # check if there's something to announce (playback ended/stopped will call us with None)
        if tags:
            # nowplaying announce
            self._lastfm_nowplaying(tags)
            # add track to the submission queue
            self.queue.extend([tags])
            # save queue to disk
            log('save file to disk', SESSION)
            write_file(self.file, self.queue)

    def _lastfm_nowplaying(self, tags):
        # update now playing status on last.fm
        log('nowplaying', SESSION)
        # collect post data
        data = {}
        data['method'] = 'track.updateNowPlaying'
        data['album'] = tags.get('album','')
        data['artist'] = tags.get('artist','')
        data['albumArtist'] = tags.get('albumartist','')
        data['duration'] = tags.get('duration','')
        data['mbid'] = tags.get('mbid','')
        data['track'] = tags.get('title','')
        data['trackNumber'] = tags.get('track','')
        data['sk'] = self.sesskey
        # connect to last.fm
        result = lastfm.post(data, SESSION)
        if not result:
            return
        # parse response
        if 'nowplaying' in result:
            return
        elif 'error' in result:
            code = result['error']
            msg = result['message'] 
            xbmc.executebuiltin('Notification(%s,%s,%i)' % (LANGUAGE(32011), msg, 7000))
            log('Last.fm nowplaying returned failed response: %s' % msg, SESSION)
            # evaluate error response
            if code == 9:
                # inavlid session key response, drop the key
                log('drop session key', SESSION)
                drop_sesskey()
            return
        else:
            log('Last.fm returned an unknown nowplaying response', SESSION)
            return

    def _lastfm_scrobble(self, tstamp):
        # scrobble track
        log('scrobbling', SESSION)
        # check the backlog
        if len(self.queue) > 250:
            # something is wrong, reset the queue
            self.queue = []
            log('error: queue exceeded 250 items', SESSION)
            return
        # we are allowed to submit max 50 tracks in one go
        submitlist = self.queue[:50]
        unqualified = []
        count = 0
        # collect post data
        data = {}
        for item in submitlist:
            # only submit items that are at least 30 secs long and have been played at least half or at least 4 minutes
            if (int(item.get('duration')) > 30) and ((tstamp - item.get('timestamp') > int(int(item.get('duration'))/2)) or (tstamp - int(item.get('timestamp')) > 240)):
                data['album[%d]' % count] = item.get('album','')
                data['artist[%d]' % count] = item.get('artist','')
                data['albumArtist[%d]' % count] = item.get('albumartist','')
                data['duration[%d]' % count] = item.get('duration','')
                data['mbid[%d]' % count] = item.get('mbid','')
                data['streamid[%d]' % count] = item.get('streamid','')
                data['timestamp[%d]' % count] = str(item.get('timestamp',''))
                data['track[%d]' % count] = item.get('title','')
                data['trackNumber[%d]' % count] = item.get('track','')
                data['user[%d]' % count] = item.get('userselected','')
            else:
                # item does not qualify for a scrobble
                unqualified.append(item)
            count += 1
        # remove tracks from the queue that don't qualify
        self._remove_invalid(unqualified)
        # check if we have any valid tracks to submit
        if not data:
            # sync queue to disk
            log('save file to disk', SESSION)
            write_file(self.file, self.queue)
            return
        data['method'] = 'track.scrobble'
        data['sk'] = self.sesskey
        # connect to last.fm
        result = lastfm.post(data, SESSION)
        # in case we don't get a response
        if not result:
            # sync queue to disk
            log('save file to disk', SESSION)
            write_file(self.file, self.queue)
            return
        # parse response
        if 'scrobbles' in result:
            # remove submitted items from the list
            self.queue = self.queue[50:]
        elif 'error' in result:
            code = result['error']
            msg = result['message'] 
            xbmc.executebuiltin('Notification(%s,%s,%i)' % (LANGUAGE(32011), msg, 7000))
            log('Last.fm scrobble returned failed response: %s' % msg, SESSION)
            # evaluate error response
            if code == 9:
                # inavlid session key response, drop the key
                log('drop session key', SESSION)               
                drop_sesskey()
            # flush the queue unless it's a temp error on last.fm side
            elif not (code == 11 or code == 16):
                self.queue = []
        else:
            log('Last.fm returned an unknown scrobble response', SESSION)
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
        self.pwd = kwargs['pwd']
        self.sesskey = kwargs['sesskey']
        self.songs = kwargs['songs']
        self.videos = kwargs['videos']
        self.radio = kwargs['radio']
        self.Audio = False

    def onAVStarted(self):
        # only do something if we're playing audio and user has enabled it in settings
        if self.sesskey and self.user and self.pwd:
            if (self.isPlayingAudio() and (self.radio or self.songs)) or (self.isPlayingMusicVideo() and self.videos):
                # we need to keep track of this bool for stopped/ended notifications
                self.Audio = True
                log('onPlayBackStarted', SESSION)
                # tags are not available instantly and we don't what to announce right away as the user might be skipping through the songs
                xbmc.sleep(500)
                # don't announce if the user already skipped to the next track or stopped playing audio
                if self.isPlayingAudio() or self.isPlayingMusicVideo():
                    # get tags
                    tags = self._get_tags()
                    # check if we have anything to submit
                    if tags:
                        # announce song
                         self.action(tags)

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

    def _get_tags(self):
        # get track tags
        if self.isPlayingAudio():
            tags = self.getMusicInfoTag()
            artist = tags.getArtist()
            albumartist = tags.getAlbumArtist()
        elif self.isPlayingVideo():
            tags = self.getVideoInfoTag()
            artist = tags.getArtist()[0]
            albumartist = ""  # not available for music videos.

        album = tags.getAlbum()
        title = tags.getTitle()
        duration = str(tags.getDuration())
        # get duration from xbmc.Player if the MusicInfoTag duration is invalid
        if int(duration) <= 0:
            duration = str(int(self.getTotalTime()))
        track = str(tags.getTrack())
        mbid = '' # musicbrainz id is not yet available
        streamid = '' # deprecated
        path = self.getPlayingFile()
        timestamp = int(time.time())
        if is_local(path):
            userselected = '1'
        else:
            userselected = '0'
        log('song scrobbling enabled: ' + str(self.songs), SESSION)
        log('video scrobbling enabled: ' + str(self.videos), SESSION)
        log('radio scrobbling enabled: ' + str(self.radio), SESSION)
        log('artist: ' + artist, SESSION)
        log('title: ' + title, SESSION)
        log('path: ' + path, SESSION)
        log('user selected flag: ' + userselected, SESSION)
        # streaming radio may provide both artistname and songtitle as one label, or we have a file with no tags
        # NOTE - this is against the last.fm scrobbling rules:
        # "Do not attempt to determine a track's meta data from its filename. Please only use meta data from well-structured sources such as ID3 tags."
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
            except:
                log('failed to extract artist from title', SESSION)
                pass
        # make sure we have artist and trackname
        if artist and title:
            # check settings to determine if we should submit this track
            if userselected == '1' and not self.songs:
                # listening to local source, but songs setting is disabled
                log('settings prohibit us from scrobbling local tracks', SESSION)
                return None
            elif userselected == '0' and not self.radio:
                # listening to remote source, but the radio setting is disabled
                log('settings prohibit us from scrobbling online streaming radio', SESSION)
                return None
            elif self.isPlayingMusicVideo() and not self.videos:
                # watching a music video, but the music video setting is disabled
                log('settings prohibit us from scrobbling music videos', SESSION)
                return None
            # previous clauses did not return, so we have either a local play with the songs setting enabled, or a remote play with the radio setting enabled,
            # and therefore can scrobble
            tracktags = dict(artist=artist, album=album, albumartist=albumartist, title=title, duration=duration, track=track, mbid=mbid, path=path, timestamp=timestamp, streamid=streamid, user=userselected)
            log('tracktags: %s' % tracktags, SESSION)
            return tracktags
        else:
            log('cannot scrobble track with no artist and track information', SESSION)
            return None

    def isPlayingMusicVideo(self):
        return self.isPlayingVideo() and self.getVideoInfoTag().getMediaType() == 'musicvideo'

class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        log('init monitor class', SESSION)
        self.user = kwargs['user']
        self.pwd = kwargs['pwd']
        self.action = kwargs['action']

    def onSettingsChanged(self):
        log('onSettingsChanged', SESSION)
        # sleep before retrieving the new settings
        xbmc.sleep(500)
        # pass the previous user and pass to getsettings, so we can check if they have changed
        self.action(self.user,self.pwd)
