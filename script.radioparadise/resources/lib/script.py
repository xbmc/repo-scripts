import sys

import xbmc
import xbmcaddon
import xbmcgui

from .radioparadise import STREAMS


class Window(xbmcgui.WindowXML):
    def onInit(self):
        xbmc.executebuiltin('Container.SetViewMode(100)')
        listitems = []
        for s in STREAMS:
            item = xbmcgui.ListItem(s['title'])
            item.setProperty('channel', str(s['channel']))
            listitems.append(item)
        self.clearList()
        self.addItems(listitems)
        xbmc.sleep(100)
        self.setFocusId(self.getCurrentContainerId())

    def onClick(self, controlId):
        if controlId == 100:
            item = self.getListItem(self.getCurrentListPosition())
            channel = int(item.getProperty('channel'))
            play_channel(channel)
            self.close()


def play_channel(channel_number):
    """Play the channel, unless it's already playing."""
    stream = STREAMS[channel_number]
    addon = xbmcaddon.Addon()
    audio_format = addon.getSetting('audio_format')
    if audio_format == 'flac':
        url = stream['url_flac']
    else:
        url = stream['url_aac']
    player = xbmc.Player()
    if not player.isPlayingAudio() or player.getPlayingFile() != url:
        player.stop()
        player.play(url)


def run_script():
    addon = xbmcaddon.Addon()
    if len(sys.argv) == 2:
        auto_play = int(sys.argv[1])
    else:
        auto_play = addon.getSettingInt('auto_play')
    if auto_play == -1:
        addon_path = addon.getAddonInfo('path')
        window = Window('script-radioparadise.xml', addon_path)
        window.doModal()
        del window
    else:
        play_channel(auto_play)
