#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.service
    kodi_monitor.py
    monitor all kodi events
'''

from utils import log_msg, json, prepare_win_props, log_exception
from metadatautils import process_method_on_list, extend_dict, get_clean_image
import xbmc


class KodiMonitor(xbmc.Monitor):
    '''Monitor all events in Kodi'''
    all_window_props = []
    monitoring_stream = False
    infopanelshown = False
    bgtasks = 0

    def __init__(self, **kwargs):
        xbmc.Monitor.__init__(self)
        self.metadatautils = kwargs.get("metadatautils")
        self.win = kwargs.get("win")
        self.enable_animatedart = xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableAnimatedPosters)") == 1

    def onNotification(self, sender, method, data):
        '''builtin function for the xbmc.Monitor class'''
        try:
            log_msg("Kodi_Monitor: sender %s - method: %s  - data: %s" % (sender, method, data))
            data = json.loads(data.decode('utf-8'))
            mediatype = ""
            dbid = 0
            transaction = False
            if data and isinstance(data, dict):
                if data.get("item"):
                    mediatype = data["item"].get("type", "")
                    dbid = data["item"].get("id", 0)
                elif data.get("type"):
                    mediatype = data["type"]
                    dbid = data.get("id", 0)
                if data.get("transaction"):
                    transaction = True

            if method == "System.OnQuit":
                self.win.setProperty("SkinHelperShutdownRequested", "shutdown")

            if method == "VideoLibrary.OnUpdate":
                self.process_db_update(mediatype, dbid, transaction)

            if method == "AudioLibrary.OnUpdate":
                self.process_db_update(mediatype, dbid, transaction)

            if method == "Player.OnStop":
                self.monitoring_stream = False
                self.infopanelshown = False
                self.win.clearProperty("Skinhelper.PlayerPlaying")
                self.win.clearProperty("TrailerPlaying")
                self.reset_win_props()

            if method == "Player.OnPlay":
                if not self.monitoring_stream:
                    self.reset_win_props()
                if self.wait_for_player():
                    if xbmc.getCondVisibility("Player.HasAudio"):
                        if xbmc.getCondVisibility("Player.IsInternetStream"):
                            self.monitor_radiostream()
                        else:
                            self.set_music_properties()
                    elif xbmc.getCondVisibility("VideoPlayer.Content(livetv)"):
                        self.monitor_livetv()
                    else:
                        self.set_video_properties(mediatype, dbid)
                        self.show_info_panel()
        except Exception as exc:
            log_exception(__name__, exc)

    def process_db_update(self, media_type, dbid, transaction=False):
        '''precache/refresh items when a kodi db item gets updated/added'''

        self.bgtasks += 1

        # item specific actions
        if dbid and media_type == "movie" and transaction and self.enable_animatedart:
            movie = self.metadatautils.kodidb.movie(dbid)
            imdb_id = movie["imdbnumber"]
            if not imdb_id and "uniqueid" in movie:
                for value in movie["uniqueid"]:
                    if value.startswith("tt"):
                        imdb_id = value
            if imdb_id and self.bgtasks < 2:
                self.metadatautils.get_animated_artwork(imdb_id)

        if dbid and media_type in ["movie", "episode", "musicvideo"]:
            self.metadatautils.get_streamdetails(dbid, media_type, ignore_cache=True)
            if transaction and self.bgtasks < 2:
                self.artwork_downloader(media_type, dbid)

        # for music content we only flush the cache
        if dbid and (not transaction or self.bgtasks < 2):
            if media_type == "song":
                song = self.metadatautils.kodidb.song(dbid)
                if song:
                    self.metadatautils.get_music_artwork(
                        song["artist"][0], song["album"], song["title"], str(
                            song["disc"]), ignore_cache=True, flush_cache=True)
            elif media_type == "album":
                album = self.metadatautils.kodidb.album(dbid)
                if album:
                    self.metadatautils.get_music_artwork(
                        album["artist"][0],
                        album["title"],
                        ignore_cache=True, flush_cache=True)
            elif media_type == "artist":
                artist = self.metadatautils.kodidb.artist(dbid)
                if artist:
                    self.metadatautils.get_music_artwork(artist["artist"], ignore_cache=True, flush_cache=True)

        # remove task
        self.bgtasks -= 1

    def reset_win_props(self):
        '''reset all window props set by the script...'''
        process_method_on_list(self.win.clearProperty, self.all_window_props)
        self.all_window_props = []

    def set_win_prop(self, prop_tuple):
        '''set window property from key/value tuple'''
        if prop_tuple[1] and not prop_tuple[0] in self.all_window_props:
            self.all_window_props.append(prop_tuple[0])
            self.win.setProperty(prop_tuple[0], prop_tuple[1])

    @staticmethod
    def wait_for_player():
        '''wait for player untill it's actually playing content'''
        count = 0
        while not xbmc.getCondVisibility("Player.HasVideo | Player.HasAudio"):
            xbmc.sleep(100)
            if count == 50:
                return False
            count += 1
        return True

    def show_info_panel(self):
        '''feature to auto show the OSD infopanel for X seconds'''
        try:
            sec_to_display = int(xbmc.getInfoLabel("Skin.String(SkinHelper.ShowInfoAtPlaybackStart)"))
        except Exception:
            return

        if sec_to_display > 0 and not self.infopanelshown:
            retries = 0
            log_msg("Show OSD Infopanel - number of seconds: %s" % sec_to_display)
            self.infopanelshown = True
            if self.win.getProperty("VideoScreensaverRunning") != "true":
                while retries != 50 and xbmc.getCondVisibility("!Player.ShowInfo"):
                    xbmc.sleep(100)
                    if xbmc.getCondVisibility("!Player.ShowInfo + Window.IsActive(fullscreenvideo)"):
                        xbmc.executebuiltin('Action(info)')
                    retries += 1
                # close info again after given amount of time
                xbmc.Monitor().waitForAbort(sec_to_display)
                if xbmc.getCondVisibility("Player.ShowInfo + Window.IsActive(fullscreenvideo)"):
                    xbmc.executebuiltin('Action(info)')

    def set_video_properties(self, mediatype, li_dbid):
        '''sets the window props for a playing video item'''
        if not mediatype:
            mediatype = self.get_mediatype()
        details = self.get_player_infolabels()
        li_title = details["title"]
        li_year = details["year"]
        li_imdb = details["imdbnumber"]
        li_showtitle = details["tvshowtitle"]
        details = {"art": {}}

        # video content
        if mediatype in ["movie", "episode", "musicvideo"]:

            # get imdb_id
            li_imdb, li_tvdb = self.metadatautils.get_imdbtvdb_id(li_title, mediatype, li_year, li_imdb, li_showtitle)

            # generic video properties (studio, streamdetails, omdb, top250)
            details = extend_dict(details, self.metadatautils.get_omdb_info(li_imdb))
            if li_dbid:
                details = extend_dict(details, self.metadatautils.get_streamdetails(li_dbid, mediatype))
            details = extend_dict(details, self.metadatautils.get_top250_rating(li_imdb))

            # tvshows-only properties (tvdb)
            if mediatype == "episode":
                details = extend_dict(details, self.metadatautils.get_tvdb_details(li_imdb, li_tvdb))

            # movies-only properties (tmdb, animated art)
            if mediatype == "movie":
                details = extend_dict(details, self.metadatautils.get_tmdb_details(li_imdb))
                if li_imdb and xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableAnimatedPosters)"):
                    details = extend_dict(details, self.metadatautils.get_animated_artwork(li_imdb))

            # extended art
            if xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableExtendedArt)"):
                tmdbid = details.get("tmdb_id", "")
                details = extend_dict(details, self.metadatautils.get_extended_artwork(
                    li_imdb, li_tvdb, tmdbid, mediatype))

        if li_title == xbmc.getInfoLabel("Player.Title").decode('utf-8'):
            all_props = prepare_win_props(details, u"SkinHelper.Player.")
            process_method_on_list(self.set_win_prop, all_props)

    def set_music_properties(self):
        '''sets the window props for a playing song'''
        li_title = xbmc.getInfoLabel("MusicPlayer.Title").decode('utf-8')
        li_title_org = li_title
        li_artist = xbmc.getInfoLabel("MusicPlayer.Artist").decode('utf-8')
        li_album = xbmc.getInfoLabel("MusicPlayer.Album").decode('utf-8')
        li_disc = xbmc.getInfoLabel("MusicPlayer.DiscNumber").decode('utf-8')
        li_plot = xbmc.getInfoLabel("MusicPlayer.Comment").decode('utf-8')

        # fix for internet streams
        if not li_artist and xbmc.getCondVisibility("Player.IsInternetStream"):
            for splitchar in [" - ", "-", ":", ";"]:
                if splitchar in li_title:
                    li_artist = li_title.split(splitchar)[0].strip()
                    li_title = li_title.split(splitchar)[1].strip()
                    break

        if xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableMusicArt)") and li_artist and(
                li_title or li_album):
            result = self.metadatautils.get_music_artwork(li_artist, li_album, li_title, li_disc)
            if result.get("extendedplot") and li_plot:
                li_plot = li_plot.replace('\n', ' ').replace('\r', '').rstrip()
                result["extendedplot"] = "%s -- %s" % (result["extendedplot"], li_plot)
            all_props = prepare_win_props(result, u"SkinHelper.Player.")
            if li_title_org == xbmc.getInfoLabel("MusicPlayer.Title").decode('utf-8'):
                process_method_on_list(self.set_win_prop, all_props)

    def artwork_downloader(self, media_type, dbid):
        '''trigger artwork scan with artwork downloader if enabled'''
        if xbmc.getCondVisibility(
                "System.HasAddon(script.artwork.downloader) + Skin.HasSetting(EnableArtworkDownloader)"):
            if media_type == "episode":
                media_type = "tvshow"
                dbid = self.metadatautils.kodidb.episode(dbid)["tvshowid"]
            xbmc.executebuiltin(
                "RunScript(script.artwork.downloader,silent=true,mediatype=%s,dbid=%s)" % (media_type, dbid))

    def monitor_radiostream(self):
        '''
            for radiostreams we are not notified when the track changes
            so we have to monitor that ourself
        '''
        if self.monitoring_stream:
            # another monitoring already in progress...
            return
        last_title = ""
        while not self.abortRequested() and xbmc.getCondVisibility("Player.HasAudio"):
            self.monitoring_stream = True
            cur_title = xbmc.getInfoLabel("MusicPlayer.Title").decode('utf-8')
            if cur_title != last_title:
                last_title = cur_title
                self.reset_win_props()
                self.set_music_properties()
            self.waitForAbort(2)
        self.monitoring_stream = False

    def monitor_livetv(self):
        '''
            for livetv we are not notified when the program changes
            so we have to monitor that ourself
        '''
        if self.monitoring_stream:
            # another monitoring already in progress...
            return
        last_title = ""
        while not self.abortRequested() and xbmc.getCondVisibility("Player.HasVideo"):
            self.monitoring_stream = True
            li_title = xbmc.getInfoLabel("Player.Title").decode('utf-8')
            if li_title and li_title != last_title:
                all_props = []
                last_title = li_title
                self.reset_win_props()
                li_channel = xbmc.getInfoLabel("VideoPlayer.ChannelName").decode('utf-8')
                # pvr artwork
                if xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnablePVRThumbs)"):
                    li_genre = xbmc.getInfoLabel("VideoPlayer.Genre").decode('utf-8')
                    pvrart = self.metadatautils.get_pvr_artwork(li_title, li_channel, li_genre)
                    all_props = prepare_win_props(pvrart, u"SkinHelper.Player.")
                # pvr channellogo
                all_props.append(("SkinHelper.Player.ChannelLogo", self.metadatautils.get_channellogo(li_channel)))
                if last_title == li_title:
                    process_method_on_list(self.set_win_prop, all_props)
            self.waitForAbort(2)
        self.monitoring_stream = False

    @staticmethod
    def get_mediatype():
        '''get current content type'''
        if xbmc.getCondVisibility("VideoPlayer.Content(movies)"):
            mediatype = "movie"
        elif xbmc.getCondVisibility("VideoPlayer.Content(episodes) | !IsEmpty(VideoPlayer.TvShowTitle)"):
            mediatype = "episode"
        elif xbmc.getInfoLabel("VideoPlayer.Content(musicvideos) | !IsEmpty(VideoPlayer.Artist)"):
            mediatype = "musicvideo"
        else:
            mediatype = "file"
        return mediatype

    @staticmethod
    def get_player_infolabels():
        '''collect basic infolabels for the current item in the videoplayer'''
        details = {"art": {}}
        # normal properties
        props = ["title", "filenameandpath", "year", "genre", "duration", "plot", "plotoutline",
                 "studio", "tvshowtitle", "premiered", "director", "writer", "season", "episode",
                 "artist", "album", "rating", "albumartist", "discnumber",
                 "firstaired", "mpaa", "tagline", "rating", "imdbnumber"
                 ]
        for prop in props:
            propvalue = xbmc.getInfoLabel('VideoPlayer.%s' % prop).decode('utf-8')
            details[prop] = propvalue
        # art properties
        props = ["fanart", "poster", "clearlogo", "clearart", "landscape",
                 "characterart", "thumb", "banner", "discart", "tvshow.landscape",
                 "tvshow.clearlogo", "tvshow.poster", "tvshow.fanart", "tvshow.banner"
                 ]
        for prop in props:
            propvalue = xbmc.getInfoLabel('Player.Art(%s)' % prop).decode('utf-8')
            if propvalue:
                prop = prop.replace("tvshow.", "")
                propvalue = get_clean_image(propvalue)
                details["art"][prop] = propvalue
        return details
