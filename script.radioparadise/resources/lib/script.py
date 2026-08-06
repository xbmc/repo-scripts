import sys

import xbmc
import xbmcaddon
import xbmcgui

from .radioparadise import Channels


class Window(xbmcgui.WindowXML):
    def onInit(self) -> None:
        xbmc.executebuiltin('Container.SetViewMode(100)')
        listitems: list[str | xbmcgui.ListItem] = []
        for channel in Channels().list():
            item = xbmcgui.ListItem(channel.title)
            item.setProperty('channel_id', str(channel.channel_id))
            listitems.append(item)
        self.clearList()
        self.addItems(listitems)
        xbmc.sleep(100)
        self.setFocusId(self.getCurrentContainerId())

    def onClick(self, controlId: int) -> None:
        if controlId == 100:
            item = self.getListItem(self.getCurrentListPosition())
            channel_id = int(item.getProperty('channel_id'))
            play_channel(channel_id)
            self.close()


def play_channel(channel_id: int) -> None:
    """Play the channel, unless it's already playing."""
    channel = Channels().by_id(channel_id)
    if channel is None:
        return

    settings = xbmcaddon.Addon().getSettings()
    audio_format = settings.getString('audio_format')
    if audio_format == 'flac':
        url = channel.url_flac
    else:
        url = channel.url_aac
    player = xbmc.Player()
    if not player.isPlayingAudio() or player.getPlayingFile() != url:
        player.stop()
        player.play(url)


def run_script() -> None:
    addon = xbmcaddon.Addon()
    if len(sys.argv) == 2:
        auto_play = int(sys.argv[1])
    else:
        auto_play = addon.getSettings().getInt('auto_play')
    if auto_play == -1:
        visible = xbmc.getCondVisibility('Control.IsVisible(100)')
        if not visible:
            addon_path = addon.getAddonInfo('path')
            window = Window('script-radioparadise.xml', addon_path)
            window.doModal()
            del window
    else:
        play_channel(auto_play)
