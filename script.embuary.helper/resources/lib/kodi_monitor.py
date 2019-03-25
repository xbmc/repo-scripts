#!/usr/bin/python

########################

import xbmc
import xbmcgui
import time
import json

from resources.lib.helper import *

########################

class KodiMonitor(xbmc.Monitor):

    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.do_fullscreen_lock = False


    def onNotification(self, sender, method, data):

        if method in ['Player.OnPlay', 'Player.OnStop', 'Player.OnAVChange', 'Playlist.OnAdd', 'VideoLibrary.OnUpdate', 'AudioLibrary.OnUpdate']:
            log('Kodi_Monitor: sender %s - method: %s  - data: %s' % (sender, method, data))
            self.data = json.loads(data)

        if method == 'Player.OnPlay':
            if not self.do_fullscreen_lock:
                self.do_fullscreen()

            if visible('String.StartsWith(Player.Filenameandpath,pvr://) + !VideoPlayer.Content(livetv)'):
                self.get_channellogo()

            if PLAYER.isPlayingAudio() and visible('!String.IsEmpty(MusicPlayer.DBID)'):
                self.get_songartworks()


        if method == 'Player.OnStop' or method == 'VideoLibrary.OnUpdate' or method == 'AudioLibrary.OnUpdate':
            self.refresh_widgets()

        if method == 'Player.OnAVChange':
            self.get_audiotracks()

        if method == 'Player.OnStop':
            xbmc.sleep(3000)
            if not PLAYER.isPlaying() and xbmcgui.getCurrentWindowId() not in [12005, 12006, 10028, 10500, 10138, 10160]:
                winprop('Player.ChannelLogo', clear=True)
                self.do_fullscreen_lock = False

        if method == 'Playlist.OnAdd':
            self.clear_playlists()


    def refresh_widgets(self):

        timestr = time.strftime('%Y%m%d%H%M%S', time.gmtime())
        log('Refreshing widgets')
        execute('AlarmClock(WidgetRefresh,SetProperty(EmbuaryWidgetUpdate,%s,home),00:04,silent)' % timestr)


    def clear_playlists(self):

        if self.data['position'] == 0 and visible('Skin.HasSetting(ClearPlaylist)'):

                if self.data['playlistid'] == 0:
                    VIDEOPLAYLIST.clear()
                    log('Music playlist has been filled. Clear existing video playlist')

                elif self.data['playlistid'] == 1:
                    MUSICPLAYLIST.clear()
                    log('Video playlist has been filled. Clear existing music playlist')


    def get_audiotracks(self):

        xbmc.sleep(100)
        log('Playback changed. Look for available audio streams.')

        audiotracks = PLAYER.getAvailableAudioStreams()
        if len(audiotracks) > 1:
            winprop('EmbuaryPlayerAudioTracks.bool', True)
        else:
            winprop('EmbuaryPlayerAudioTracks', clear=True)


    def do_fullscreen(self):

        xbmc.sleep(1000)
        if visible('Skin.HasSetting(StartPlayerFullscreen)'):

            for i in range(1,200):

                if xbmcgui.getCurrentWindowId() in [12005, 12006]:
                    self.do_fullscreen_lock = True
                    break

                elif xbmcgui.getCurrentWindowId() not in [12005, 12006, 10028, 10500, 10138, 10160]:
                    execute('Dialog.Close(all,true)')
                    execute('action(fullscreen)')
                    self.do_fullscreen_lock = True
                    log('Playback started. Force switch to fullscreen.')
                    break

                else:
                    xbmc.sleep(50)


    def get_channellogo(self):

        log('Recording playback detected. Calling DB for channel logo.')

        channel_details = get_channeldetails(xbmc.getInfoLabel('VideoPlayer.ChannelName'))
        try:
            winprop('Player.ChannelLogo', channel_details['icon'])

        except Exception:
            winprop('Player.ChannelLogo', clear=True)


    def get_songartworks(self):

        log('Music playback detected. Fetching song artworks from database')

        try:
            songdetails = json_call('AudioLibrary.GetSongDetails',
                                properties=['art', 'albumid'],
                                params={'songid': int(xbmc.getInfoLabel('MusicPlayer.DBID'))},
                                )

            songdetails = songdetails['result']['songdetails']

            winprop('MusicPlayer.Cover', songdetails['art'].get('thumb', ''))
            winprop('MusicPlayer.Fanart', songdetails['art'].get('fanart', ''))
            winprop('MusicPlayer.Clearlogo', songdetails['art'].get('clearlogo', ''))

        except Exception:
            winprop('MusicPlayer.Cover', clear=True)
            winprop('MusicPlayer.Fanart', clear=True)
            winprop('MusicPlayer.Clearlogo', clear=True)

        try:
            albumdetails = json_call('AudioLibrary.GetAlbumDetails',
                                properties=['art'],
                                params={'albumid': int(songdetails['albumid'])},
                                )

            albumdetails = albumdetails['result']['albumdetails']

            winprop('MusicPlayer.DiscArt', albumdetails['art'].get('discart', ''))

        except Exception:
            winprop('MusicPlayer.DiscArt', clear=True)

