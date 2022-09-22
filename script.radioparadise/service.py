import time
import traceback

import requests
import xbmc
import xbmcaddon
import xbmcgui

from radioparadise import SLIDESHOW_URL, STREAM_INFO, NowPlaying, build_key


DEVELOPMENT = False

EXPIRATION_DELAY = 30

RESTART_DELAY = 1.0
RESTART_TIMEOUT = 1.0


class Song():
    """Current song information."""

    def __init__(self, key, data, fanart, start_time):
        self.key = key
        self.data = data
        self.fanart = fanart
        self.cover = data['cover']
        self.start_time = start_time
        self.duration = int(data['duration']) / 1000

    def __str__(self):
        artist = self.data.get('artist', 'Unknown Artist')
        title = self.data.get('title', 'Unknown Title')
        return f'{artist} - {title}'

    def changed(self, key):
        """Return True if the key indicates a song change."""
        return key is not None and key != self.key

    def expired(self):
        """Return True if this Song should be considered overdue."""
        expiration = self.start_time + self.duration + EXPIRATION_DELAY
        return time.time() > expiration


class Player(xbmc.Player):
    """Adds xbmc.Player callbacks and integrates with the RP API."""

    def __init__(self):
        """Constructor"""
        super().__init__()
        self.song = None
        self.stream_url = None
        self.restart_time = 0
        self.now_playing = NowPlaying()
        self.slideshow = Slideshow()

    def get_song_key(self):
        """Return a key for the current song, or None."""
        result = None
        if self.isPlayingAudio():
            try:
                info = self.getMusicInfoTag()
                artist_title = (info.getArtist(), info.getTitle())
                if artist_title != ('', ''):
                    result = build_key(artist_title)
            except Exception:
                pass
        return result

    def reset(self):
        """Reset internal state when not playing RP."""
        self.song = None
        self.stream_url = None
        self.restart_time = 0
        self.now_playing.set_channel(None)
        self.slideshow.set_slides(None)

    def restart(self):
        """Restart playback, if necessary."""
        now = time.time()
        if not self.restart_time or now < self.restart_time:
            return
        try:
            res = requests.head(self.stream_url, timeout=RESTART_TIMEOUT)
            do_restart = res.status_code == 200
        except Exception:
            do_restart = False
        if do_restart:
            self.restart_time = 0
            self.play(self.stream_url)
        else:
            self.restart_time = now + RESTART_DELAY

    def update(self):
        """Perform updates."""
        if self.restart_time:
            self.restart()
        elif self.stream_url:
            self.now_playing.update()
            self.update_slideshow()
            self.update_song()

    def update_player(self):
        """Update the Kodi player with song metadata."""
        song = self.song
        if song and self.isPlayingAudio():
            info = {
                'artist': song.data['artist'],
                'title': song.data['title'],
                'genre': '',
            }
            if 'album' in song.data:
                info['album'] = song.data['album']
            if 'rating' in song.data:
                rating = float(song.data['rating'])
                info['rating'] = rating
                info['userrating'] = int(round(rating))
            if 'year' in song.data:
                info['year'] = int(song.data['year'])
            item = xbmcgui.ListItem()
            item.setPath(self.getPlayingFile())
            item.setArt({'thumb': song.cover})
            item.setArt({'fanart': song.fanart})
            item.setInfo('music', info)
            self.updateInfoTag(item)

    def update_slideshow(self):
        """Update the slideshow, if necessary."""
        song = self.song
        next_slide = self.slideshow.next_slide()
        if song and next_slide:
            song.fanart = next_slide
            self.update_player()

    def update_song(self):
        """Update song metadata, if necessary."""
        song_key = self.get_song_key()
        song = self.song
        if song_key is None:
            return
        if song and not (song.changed(song_key) or song.expired()):
            return

        start_time = None
        song_data = None
        if song and song.changed(song_key):
            start_time = time.time()
            song_data = self.now_playing.get_song_data(song_key)
        elif song and song.expired():
            start_time = song.start_time + song.duration
            song_data = self.now_playing.current
            log('Song expired.', xbmc.LOGWARNING)
        elif song is None:
            song_data = self.now_playing.current
        # API metadata may not be available yet
        if song_data is None:
            return

        song_key = build_key((song_data['artist'], song_data['title']))
        if start_time is None:
            start_time = int(song_data['sched_time'])

        addon = xbmcaddon.Addon()
        slideshow = addon.getSetting('slideshow')
        if slideshow == 'rp':
            slides = song_data.get('slideshow', '').split(',')
            slides = [SLIDESHOW_URL.format(s) for s in slides if s]
            delay = addon.getSettingInt('slide_duration')
            self.slideshow.set_slides(slides, delay)
            fanart = self.slideshow.next_slide()
        else:
            self.slideshow.set_slides(None)
            fanart = None
        self.song = Song(song_key, song_data, fanart, start_time)
        log(f'Song: {self.song}')
        self.update_player()

    def onAVStarted(self):
        if self.isPlaying() and self.getPlayingFile() in STREAM_INFO:
            url = self.getPlayingFile()
            info = STREAM_INFO[url]
            # Kodi switches to fullscreen for FLAC, but not AAC
            if url == info['url_aac']:
                xbmc.executebuiltin('Action(FullScreen)')
        else:
            self.reset()

    def onPlayBackEnded(self):
        if self.stream_url:
            self.restart_time = time.time()
        else:
            self.reset()

    def onPlayBackError(self):
        self.reset()

    def onPlayBackStarted(self):
        if self.isPlaying() and self.getPlayingFile() in STREAM_INFO:
            url = self.getPlayingFile()
            self.stream_url = url
            self.restart_time = 0
            info = STREAM_INFO[url]
            self.now_playing.set_channel(info['channel'])
        else:
            self.reset()

    def onPlayBackStopped(self):
        self.reset()


class Slideshow():
    """Provides timed slide URLs."""

    def __init__(self):
        self.set_slides(None)

    def set_slides(self, slides, delay=10):
        """Set slides and delay, or None."""
        if slides:
            self.slides = slides
            self.delay = delay
            self.index = 0
            self.time = 0
        else:
            self.slides = None

    def next_slide(self):
        """Return the next slide URL, or None."""
        result = None
        now = time.time()
        if self.slides and self.time + self.delay < now:
            result = self.slides[self.index]
            self.index = (self.index + 1) % len(self.slides)
            self.time = now
        return result


def log(message, level=None):
    """Write to the Kodi log."""
    if level is not None:
        xbmc.log(f'rp_service: {message}', level)
    elif DEVELOPMENT:
        xbmc.log(f'rp_service: {message}', xbmc.LOGINFO)
    else:
        xbmc.log(f'rp_service: {message}', xbmc.LOGDEBUG)


if __name__ == '__main__':
    log('Service started.')
    player = Player()
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(0.1):
            break
        try:
            player.update()
        except Exception as e:
            if DEVELOPMENT:
                lines = traceback.format_exception(e)
                for line in lines:
                    log(line, xbmc.LOGERROR)
            else:
                log(repr(e), xbmc.LOGERROR)
    log('Service exiting.')
