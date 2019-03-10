#!/usr/bin/python

########################

import xbmc
import xbmcgui
import time

from resources.lib.helper import *

########################

class KodiMonitor(xbmc.Monitor):

    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.do_fullscreen_lock = False


    def onNotification(self, sender, method, data):

        if method in ['Player.OnPlay', 'Player.OnStop', 'Player.OnAVChange']:
            log('Kodi_Monitor: sender %s - method: %s  - data: %s' % (sender, method, data))

        if method == 'Player.OnPlay':
            if not self.do_fullscreen_lock:
                self.do_fullscreen()
            if visible('String.StartsWith(Player.Filenameandpath,pvr://)'):
                self.get_channellogo()

        if method == 'Player.OnStop' or method == 'VideoLibrary.OnUpdate' or method == 'AudioLibrary.OnUpdate':
            self.refresh_widgets()

        if method == 'Player.OnAVChange':
            self.get_audiotracks()

        if method == 'Player.OnStop':
            xbmc.sleep(3000)
            if not PLAYER.isPlaying():
                self.do_fullscreen_lock = False
                self.clear_playlist()
                winprop('Player.ChannelLogo', clear=True)


    def refresh_widgets(self):

        timestr = time.strftime('%Y%m%d%H%M%S', time.gmtime())
        log('Refreshing widgets')
        execute('AlarmClock(WidgetRefresh,SetProperty(EmbuaryWidgetUpdate,%s,home),00:04,silent)' % timestr)


    def get_audiotracks(self):

        xbmc.sleep(100)
        winprop('EmbuaryPlayerAudioTracks', clear=True)

        audiotracks = PLAYER.getAvailableAudioStreams()
        if len(audiotracks) > 1:
            winprop('EmbuaryPlayerAudioTracks.bool', True)


    def clear_playlist(self):

        if visible('Skin.HasSetting(EmbuaryHelperClearPlaylist)') and xbmcgui.getCurrentWindowId() not in [12005, 12006, 10028, 10500, 10138]:
            execute('Playlist.Clear')
            log('Playlist cleared')


    def do_fullscreen(self):

        xbmc.sleep(1000)
        if visible('Skin.HasSetting(StartPlayerFullscreen)'):
            for i in range(1,200):
                if xbmcgui.getCurrentWindowId() in [12005, 12006]:
                    self.do_fullscreen_lock = True
                    break
                elif xbmcgui.getCurrentWindowId() not in [12005, 12006, 10028, 10500, 10138]:
                    execute('Dialog.Close(all,true)')
                    execute('action(fullscreen)')
                    self.do_fullscreen_lock = True
                    break
                else:
                    xbmc.sleep(50)

    def get_channellogo(self):

        channel_details = get_channeldetails(xbmc.getInfoLabel('VideoPlayer.ChannelName'))
        try:
            winprop('Player.ChannelLogo', channel_details['icon'])
        except Exception:
            winprop('Player.ChannelLogo', clear=True)

