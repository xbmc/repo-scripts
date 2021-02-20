import xbmc

from .listitembuilder import build_video_listitem
from . import quickjson
from .pykodi import get_busydialog, log

LOAD_NEW = 3
KEEP_PREVIOUS = 4

def get_player(source, showbusydialog):
    result = RollingPlaylistPlayer()
    result.source = source
    result.showbusydialog = showbusydialog
    return result

class RollingPlaylistPlayer(xbmc.Player):
    def __init__(self):
        super(RollingPlaylistPlayer, self).__init__()
        self.playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.playlist.clear()
        self._source = None
        self.source_exhausted = True
        self.showbusydialog = None

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, source):
        self._source = source
        if source:
            self.source_exhausted = False

    def run(self):
        if self.showbusydialog:
            busy = get_busydialog()
            busy.create()
        extended = self.extend_playlist()
        if self.showbusydialog: busy.close()
        if extended:
            self.play(self.playlist)
            if LOAD_NEW - 1 > 0:
                self.extend_playlist(LOAD_NEW - 1)
        while xbmc.getCondVisibility('Player.HasMedia'):
            if self.source_exhausted:
                break
            xbmc.sleep(2000)

        log("I'm done")

    def add_to_playlist(self, item):
        self.playlist.add(item.get('file'), build_video_listitem(item))

    def extend_playlist(self, count=1):
        if self.source_exhausted:
            return False
        addedcount = 0
        for _ in range(0, count):
            try:
                self.add_to_playlist(next(self._source))
                addedcount += 1
            except StopIteration:
                self.source_exhausted = True
                log("Source has been exhausted")
                break

        return True if addedcount else False

    def onPlayBackStarted(self):
        self.extend_playlist()
        if self.playlist.getposition() > KEEP_PREVIOUS:
            quickjson.remove_from_playlist(0)
