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
        self.fullscreen_lock = False
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
                self.get_nextitem()

            if not self.fullscreen_lock:
                self.do_fullscreen()

        ''' Playlist changed. Fetch nextitem again.
        '''
        if method in ['Playlist.OnAdd', 'Playlist.OnRemove'] and PLAYER.isPlayingVideo() and not self.pvr_playback:
            self.get_nextitem()

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
                self.fullscreen_lock = False
                self.pvr_playback = False
                self.get_nextitem(clear=True)
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

    def do_fullscreen(self):
        xbmc.sleep(1000)
        if condition('Skin.HasSetting(StartPlayerFullscreen)'):

            for i in range(1,200):
                if xbmcgui.getCurrentWindowId() in [12005, 12006]:
                    execute('Dialog.Close(all,true)')
                    self.fullscreen_lock = True
                    log('Playback started. Force closing all dialogs.')
                    break

                elif xbmcgui.getCurrentWindowId() not in [12005, 12006, 10028, 10500, 10138, 10160]:
                    execute('Dialog.Close(all,true)')
                    execute('action(fullscreen)')
                    self.fullscreen_lock = True
                    log('Playback started. Force switch to fullscreen.')
                    break

                else:
                    xbmc.sleep(50)

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

    def get_nextitem(self,clear=False):
        try:
            if clear:
                raise Exception

            position = int(VIDEOPLAYLIST.getposition())

            json_query = json_call('Playlist.GetItems',
                                    properties=JSON_MAP['playlist_properties'],
                                    limits={"start": position+1, "end": position+2},
                                    params={'playlistid': 1}
                                    )

            nextitem = json_query['result']['items'][0]

            arts = nextitem['art']
            for art in arts:
                if art in ['clearlogo', 'logo', 'tvshow.clearlogo', 'tvshow.logo', 'landscape', 'tvshow.landscape', 'poster', 'tvshow.poster', 'clearart', 'tvshow.clearart', 'banner', 'tvshow.banner']:
                    winprop('VideoPlayer.Next.Art(%s)' % art, arts[art])

            try:
                runtime = int(nextitem.get('runtime'))
                minutes = runtime / 60
                winprop('VideoPlayer.Next.Duration(m)', str(round(minutes)))
                winprop('VideoPlayer.Next.Duration', str(datetime.timedelta(seconds=runtime)))
                winprop('VideoPlayer.Next.Duration(s)', str(runtime))

            except Exception:
                winprop('VideoPlayer.Next.Duration', clear=True)
                winprop('VideoPlayer.Next.Duration(m)', clear=True)
                winprop('VideoPlayer.Next.Duration(s)', clear=True)

            winprop('VideoPlayer.Next.Title', nextitem.get('title',''))
            winprop('VideoPlayer.Next.TVShowTitle', nextitem.get('showtitle',''))
            winprop('VideoPlayer.Next.Genre', get_joined_items(nextitem.get('genre','')))
            winprop('VideoPlayer.Next.Plot', nextitem.get('plot',''))
            winprop('VideoPlayer.Next.Tagline', nextitem.get('tagline',''))
            winprop('VideoPlayer.Next.Season', str(nextitem.get('season','')))
            winprop('VideoPlayer.Next.Episode', str(nextitem.get('episode','')))
            winprop('VideoPlayer.Next.Year', str(nextitem.get('year','')))
            winprop('VideoPlayer.Next.Rating', str(float(nextitem.get('rating','0'))))
            winprop('VideoPlayer.Next.UserRating', str(float(nextitem.get('userrating','0'))))
            winprop('VideoPlayer.Next.DBID', str(nextitem.get('id','')))
            winprop('VideoPlayer.Next.DBType', nextitem.get('type',''))
            winprop('VideoPlayer.Next.Art(fanart)', nextitem.get('fanart',''))
            winprop('VideoPlayer.Next.Art(thumb)', nextitem.get('thumbnail',''))

        except Exception:
            for art in ['fanart', 'thumb', 'clearlogo', 'logo', 'tvshow.clearlogo', 'tvshow.logo', 'landscape', 'tvshow.landscape', 'poster', 'tvshow.poster', 'clearart', 'tvshow.clearart', 'banner', 'tvshow.banner']:
                winprop('VideoPlayer.Next.Art(%s)' % art, clear=True)

            for info in ['Duration','Duration(m)','Duration(s)','Title','TVShowTitle','Genre','Plot','Tagline','Season','Episode','Year','Rating','UserRating','DBID','DBType']:
                winprop('VideoPlayer.Next.%s' % info, clear=True)

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