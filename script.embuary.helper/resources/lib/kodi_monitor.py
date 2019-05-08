#!/usr/bin/python

########################

import xbmc
import xbmcgui
import json

from resources.lib.helper import *

########################

class KodiMonitor(xbmc.Monitor):

    def __init__(self):
        self.do_fullscreen_lock = False
        self.has_PVR_prop = False


    def onNotification(self, sender, method, data):

        if method in ['Player.OnPlay', 'Player.OnStop', 'Player.OnAVChange', 'Playlist.OnAdd', 'VideoLibrary.OnUpdate', 'AudioLibrary.OnUpdate']:
            log('Kodi_Monitor: sender %s - method: %s  - data: %s' % (sender, method, data))
            self.data = json.loads(data)

        if method == 'Player.OnPlay':
            if not self.do_fullscreen_lock:
                self.do_fullscreen()

            if visible('String.StartsWith(Player.Filenameandpath,pvr://)'):
                self.get_channellogo()

            if PLAYER.isPlayingAudio() and visible('!String.IsEmpty(MusicPlayer.DBID) + [String.IsEmpty(Player.Art(thumb)) | String.IsEmpty(Player.Art(album.discart))]'):
                self.get_songartworks()

        if method == 'VideoLibrary.OnUpdate' or method == 'AudioLibrary.OnUpdate':
            reload_widgets()

        if method == 'Player.OnAVChange':
            self.get_audiotracks()

        if method == 'Player.OnStop':
            xbmc.sleep(3000)
            if not PLAYER.isPlaying() and xbmcgui.getCurrentWindowId() not in [12005, 12006, 10028, 10500, 10138, 10160]:
                self.do_fullscreen_lock = False

                if self.has_PVR_prop:
                    winprop('Player.ChannelLogo', clear=True)

        if method == 'Playlist.OnAdd':
            self.clear_playlists()


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
        log('Look for available audio streams.')

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
            self.has_PVR_prop = True

        except Exception:
            winprop('Player.ChannelLogo', clear=True)
            self.has_PVR_prop = False


    def get_songartworks(self):

        log('Music playback with no artworks detected. Trying to fetch them from the database.')

        try:
            songdetails = json_call('AudioLibrary.GetSongDetails',
                                properties=['art', 'albumid'],
                                params={'songid': int(xbmc.getInfoLabel('MusicPlayer.DBID'))},
                                )

            songdetails = songdetails['result']['songdetails']
            fanart = songdetails['art'].get('fanart', '')
            thumb = songdetails['art'].get('thumb', '')
            clearlogo = songdetails['art'].get('clearlogo', '')

        except Exception:
            return

        try:
            albumdetails = json_call('AudioLibrary.GetAlbumDetails',
                                properties=['art'],
                                params={'albumid': int(songdetails['albumid'])},
                                )

            albumdetails = albumdetails['result']['albumdetails']
            discart = albumdetails['art'].get('discart', '')

        except Exception:
            pass

        item = xbmcgui.ListItem()
        item.setPath(xbmc.Player().getPlayingFile())
        item.setArt({'thumb': thumb, 'fanart': fanart, 'clearlogo': clearlogo, 'discart': discart, 'album.discart': discart})
        xbmc.Player().updateInfoTag(item)
