from collections import namedtuple
import time

import requests
import xbmc
import xbmcaddon
import xbmcgui

from radioparadise import SLIDESHOW_URL, STREAM_INFO, NowPlaying


RESTART_INTERVAL = 1.0
RESTART_TIMEOUT = 1.0


Song = namedtuple('Song', 'key data cover fanart')


class Player(xbmc.Player):
    """Adds xbmc.Player callbacks and integrates with the RP API."""

    def __init__(self):
        """Constructor"""
        super().__init__()
        self.last_key = None
        self.last_song = None
        self.stream_url = None
        self.restart_time = 0
        self.now_playing = NowPlaying()
        self.slideshow = Slideshow()

    def get_song_key(self):
        """Return (artist, title) for the current song, or None."""
        result = None
        if self.isPlayingAudio():
            try:
                info = self.getMusicInfoTag()
                result = (info.getArtist(), info.getTitle())
            except Exception:
                pass
        return result

    def reset(self):
        """Reset internal state when not playing RP."""
        self.last_key = None
        self.last_song = None
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
            self.restart_time = now + RESTART_INTERVAL

    def update(self):
        """Perform updates."""
        if self.restart_time:
            self.restart()
        else:
            self.now_playing.update()
            self.update_slideshow()
            self.update_song()

    def update_player(self):
        """Update the Kodi player with song metadata."""
        song = self.last_song
        if song and self.isPlayingAudio():
            info = {
                'artist': song.key[0],
                'title': song.key[1],
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
        next_slide = self.slideshow.next_slide()
        if next_slide and self.last_song:
            self.last_song = self.last_song._replace(fanart=next_slide)
            self.update_player()

    def update_song(self):
        """Update song metadata, if necessary."""
        song_key = self.get_song_key()
        if song_key is None or song_key == self.last_key:
            self.last_key = song_key
            return

        xbmc.log(f'rp_service: song_key {song_key}', xbmc.LOGDEBUG)
        song_data = self.now_playing.get_song_data(song_key)
        if song_data is None:
            return

        cover = song_data.get('cover')
        xbmc.log(f'rp_service: cover {cover}', xbmc.LOGDEBUG)

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

        self.last_key = song_key
        self.last_song = Song(song_key, song_data, cover, fanart)
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


if __name__ == '__main__':
    player = Player()
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(0.1):
            break
        try:
            player.update()
        except Exception as e:
            xbmc.log(f'rp_service: {e}', xbmc.LOGERROR)
