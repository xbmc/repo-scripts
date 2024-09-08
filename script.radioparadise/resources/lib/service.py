import time
import traceback

import requests
import xbmc
import xbmcaddon
import xbmcgui

from .radioparadise import STREAM_INFO, NowPlaying, build_key


DEVELOPMENT = False

EXPIRATION_DELAY = 10

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

    def expired(self):
        """Return True if this Song should be considered overdue."""
        if self.start_time:
            expiration = self.start_time + self.duration + EXPIRATION_DELAY
            return time.time() > expiration
        else:
            return False


class Player(xbmc.Player):
    """Adds xbmc.Player callbacks and integrates with the RP API."""

    def __init__(self):
        """Constructor"""
        super().__init__()
        self.song = None
        self.stream_url = None
        self.restart_time = 0
        self.tracked_key = None
        self.tracked_time = 0
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
        self.tracked_key = None
        self.tracked_time = 0
        self.now_playing.set_channel(None)
        self.slideshow.set_slides(None)

    def restart(self):
        """Restart playback, if necessary."""
        if not self.restart_time or time.time() < self.restart_time:
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
            self.restart_time = time.time() + RESTART_DELAY

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
            item = self.getPlayingItem()
            tag = item.getMusicInfoTag()
            tag.setArtist(song.data['artist'])
            tag.setTitle(song.data['title'])
            tag.setGenres([])
            tag.setAlbum(song.data.get('album', ''))
            rating = song.data.get('listener_rating', 0)
            tag.setRating(rating)
            tag.setUserRating(int(round(rating)))
            tag.setYear(int(song.data.get('year', 0)))
            item.setArt({'thumb': song.cover})
            item.setArt({'fanart': song.fanart})
            self.updateInfoTag(item)

    def clear_player(self):
        """Clear most of the Kodi player's song information."""
        if self.isPlayingAudio():
            info = self.getMusicInfoTag()
            item = self.getPlayingItem()
            tag = item.getMusicInfoTag()
            tag.setArtist(info.getArtist())
            tag.setTitle(info.getTitle())
            tag.setGenres([])
            tag.setAlbum('')
            tag.setRating(0)
            tag.setUserRating(0)
            tag.setYear(0)
            item.setArt({'thumb': None})
            item.setArt({'fanart': None})
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
        player_key = self.get_song_key()
        song = self.song
        if player_key is None:
            return
        if song and not (song.key != player_key or song.expired()):
            return

        # Keep track of the local song start time
        if self.tracked_key != player_key:
            if self.tracked_key is not None:
                self.tracked_time = time.time()
            self.tracked_key = player_key

        start_time = None
        song_data = None
        # Try to match API metadata on song changes
        if song is None:
            start_time = 0
            song_data = self.now_playing.get_song_data(player_key)
        elif song.key != player_key and not song.expired():
            start_time = self.tracked_time
            song_data = self.now_playing.get_song_data(player_key)
        # Show "next" song if the song change was missed
        elif song.expired():
            start_time = song.start_time + song.duration
            song_data = self.now_playing.get_next_song(player_key)
            # Without API metadata, show the stream metadata
            if song_data is None and song.start_time:
                song.start_time = 0
                self.slideshow.set_slides(None)
                self.clear_player()
        # API metadata may not be available yet
        if song_data is None:
            return

        addon = xbmcaddon.Addon()
        slideshow = addon.getSetting('slideshow')
        if slideshow == 'rp':
            slides = song_data.get('slide_urls')
            delay = addon.getSettingInt('slide_duration')
            self.slideshow.set_slides(slides, delay)
            fanart = self.slideshow.next_slide()
        else:
            self.slideshow.set_slides(None)
            fanart = None

        song_key = build_key((song_data['artist'], song_data['title']))
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


def run_service():
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
                log(traceback.format_exc(), xbmc.LOGERROR)
            else:
                log(repr(e), xbmc.LOGERROR)
    log('Service exiting.')
