import time
import requests
import xbmc
import xbmcaddon
import xbmcgui
from collections import namedtuple
from motherearth import STREAM_INFO, NowPlaying


RESTART_INTERVAL = 1.0
RESTART_TIMEOUT = 1.0


Song = namedtuple('Song', 'data cover')


class Player(xbmc.Player):
    """Adds xbmc.Player callbacks and integrates with the API."""

    def __init__(self):
        """Constructor"""
        super().__init__()
        self.last_key = None
        self.last_song = None
        self.stream_url = None
        self.restart_time = 0
        self.now_playing = NowPlaying()

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
        """Reset internal state when not playing ."""
        self.last_key = None
        self.last_song = None
        self.stream_url = None
        self.restart_time = 0
        self.now_playing.set_channel(None)

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
        elif self.stream_url:
            self.now_playing.update()
            self.update_song()

    def update_player(self):
        """Update the Kodi player with song metadata."""
        song = self.last_song
        if song and self.isPlayingAudio():
            info = {
                'artist': song.data['artist'],
                'title': song.data['title'],
                'genre': song.data['genre'],
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
            item.setArt({'fanart': song.cover})
            item.setInfo('music', info)
            self.updateInfoTag(item)


    def update_song(self):
        """Update song metadata, if necessary."""
        last_key = self.last_key
        last_song = self.last_song
        song_key = self.get_song_key()
        if song_key is None:
            return

        if song_key != ('', ''):
      
            song_data = self.now_playing.current
            if song_data:
                self.last_key = song_key
        else:
            song_data = self.now_playing.current
        if song_data is None or last_song and last_song.data == song_data:
            return

        cover = song_data.get('cover')
        
        self.last_song = Song(song_data, cover)
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

if __name__ == '__main__':
    player = Player()
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(0.1):
            break
        try:
            player.update()
        except Exception as e:
            xbmc.log(f'mer_service: {e}', xbmc.LOGERROR)
