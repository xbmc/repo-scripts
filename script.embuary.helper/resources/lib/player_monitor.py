#!/usr/bin/python

########################

import xbmc
import xbmcgui
import json
import datetime

from resources.lib.helper import *
from resources.lib.json_map import *
from resources.lib.image import *

########################

class PlayerMonitor(xbmc.Monitor):
    def __init__(self):
        log('Service: Player monitor started', force=True)
        self.pvr_playback = False

    def onNotification(self, sender, method, data):
        if method in ['Player.OnPlay', 'Player.OnStop', 'Player.OnAVChange', 'Playlist.OnAdd', 'Playlist.OnRemove', 'VideoLibrary.OnUpdate', 'AudioLibrary.OnUpdate']:
            self.data = json.loads(data)

        ''' Clear music or video playlist based on player content.
        '''
        if method == 'Playlist.OnAdd':
            self.clear_playlists()

        ''' Get stuff when playback starts.
        '''
        if method == 'Player.OnPlay':
            xbmc.stopSFX()
            self.pvr_playback = condition('String.StartsWith(Player.Filenameandpath,pvr://)')

            self.get_art_info()

            if condition('Skin.HasSetting(BlurPlayerIcon)'):
                self.blur_player_icon()

            if self.pvr_playback:
                self.get_channellogo()

            if PLAYER.isPlayingVideo() and not self.pvr_playback:
                self.get_videoinfo()

        ''' Check if multiple audio tracks are available and refetch
            artwork info for PVR playback.
        '''
        if method == 'Player.OnAVChange':
            self.get_audiotracks()

            if self.pvr_playback:
                self.get_art_info()

        ''' Playback stopped. Clean up.
        '''
        if method == 'Player.OnStop':
            while not self.abortRequested(): # workaround for unwanted behaviours on slow systems
                self.waitForAbort(3)
                break

            if not PLAYER.isPlaying() and xbmcgui.getCurrentWindowId() not in [12005, 12006, 10028, 10500, 10138, 10160]:
                self.pvr_playback = False
                self.get_channellogo(clear=True)
                self.get_audiotracks(clear=True)
                self.get_videoinfo(clear=True)
                self.get_art_info(clear=True)

                ''' Kodi doesn't reset shuffle to false automatically. To prevent issues with Emby for Kodi we have to
                    set shuffle to false for the next video playback if it was enabled by the script before.
                '''
                if winprop('script.shuffle.bool'):
                    winprop('script.shuffle', clear=True)

                    json_call('Player.SetShuffle',
                              params={'playerid': 1, 'shuffle': False}
                              )

    def clear_playlists(self):
        if self.data['position'] == 0 and condition('Skin.HasSetting(ClearPlaylist)'):
                if self.data['playlistid'] == 0:
                    VIDEOPLAYLIST.clear()
                    log('Music playlist has been filled. Clear existing video playlist')

                elif self.data['playlistid'] == 1:
                    MUSICPLAYLIST.clear()
                    log('Video playlist has been filled. Clear existing music playlist')

    def get_audiotracks(self,clear=False):
        xbmc.sleep(100)
        audiotracks = PLAYER.getAvailableAudioStreams()
        if len(audiotracks) > 1 and not clear:
            winprop('EmbuaryPlayerAudioTracks.bool', True)
        else:
            winprop('EmbuaryPlayerAudioTracks', clear=True)

    def get_channellogo(self,clear=False):
        try:
            if clear:
                raise Exception

            channel_details = get_channeldetails(xbmc.getInfoLabel('VideoPlayer.ChannelName'))
            winprop('Player.ChannelLogo', channel_details['icon'])

        except Exception:
            winprop('Player.ChannelLogo', clear=True)

    def get_videoinfo(self,clear=False):
        dbid = xbmc.getInfoLabel('VideoPlayer.DBID')

        for i in range(1,50):
            winprop('VideoPlayer.AudioCodec.%d' % i, clear=True)
            winprop('VideoPlayer.AudioChannels.%d' % i, clear=True)
            winprop('VideoPlayer.AudioLanguage.%d' % i, clear=True)
            winprop('VideoPlayer.SubtitleLanguage.%d' % i, clear=True)

        if clear or not dbid:
            return

        if condition('VideoPlayer.Content(movies)'):
            method = 'VideoLibrary.GetMovieDetails'
            mediatype = 'movieid'
            details = 'moviedetails'
        elif condition('VideoPlayer.Content(episodes)'):
            method = 'VideoLibrary.GetEpisodeDetails'
            mediatype = 'episodeid'
            details = 'episodedetails'
        else:
            return

        json_query = json_call(method,
                            properties=['streamdetails'],
                            params={mediatype: int(dbid)}
                            )

        try:
            results_audio = json_query['result'][details]['streamdetails']['audio']

            i = 1
            for track in results_audio:
                winprop('VideoPlayer.AudioCodec.%d' % i, track['codec'])
                winprop('VideoPlayer.AudioChannels.%d' % i, str(track['channels']))
                winprop('VideoPlayer.AudioLanguage.%d' % i, track['language'])
                i += 1

        except Exception:
            pass

        try:
            results_subtitle = json_query['result'][details]['streamdetails']['subtitle']

            i = 1
            for subtitle in results_subtitle:
                winprop('VideoPlayer.SubtitleLanguage.%d' % i, subtitle['language'])
                i += 1

        except Exception:
            return

    def get_art_info(self,clear=False):
        for art in ['Player.Icon', 'Player.Art(poster)', 'Player.Art(tvshow.poster)', 'Pvr.EPGEventIcon']:
            image = xbmc.getInfoLabel(art)

            if not clear and image:
                width,height,ar = image_info(image)
                winprop(art + '.width',str(width))
                winprop(art + '.height',str(height))
                winprop(art + '.ar',str(ar))
            else:
                winprop(art + '.width',clear=True)
                winprop(art + '.height',clear=True)
                winprop(art + '.ar',clear=True)

    def blur_player_icon(self):
        ImageBlur(prop='playericon',
                  file=xbmc.getInfoLabel('Player.Icon'),
                  radius=5
                  )