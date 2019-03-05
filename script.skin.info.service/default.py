import sys
import xbmc
import xbmcgui
import xbmcaddon
from Utils import *

ADDON = xbmcaddon.Addon()
ADDON_VERSION = ADDON.getAddonInfo('version')
WND = xbmcgui.Window(12003)  # Video info dialog
HOME = xbmcgui.Window(10000)  # Home Window


class Daemon:

    def __init__(self):
        log("version %s started" % ADDON_VERSION)
        self._init_vars()
        self.run_backend()

    def _init_vars(self):
        self.id = None
        self.type = False
        self.Artist_mbid = None

    def run_backend(self):
        self._stop = False
        self.previousitem = ""
        log("starting backend")
        while (not self._stop) and (not xbmc.abortRequested):
            if xbmc.getCondVisibility("Container.Content(movies) | Container.Content(sets) | Container.Content(artists) | Container.Content(albums) | Container.Content(episodes) | Container.Content(musicvideos)"):
                self.selecteditem = xbmc.getInfoLabel("ListItem.DBID")
                if (self.selecteditem != self.previousitem):
                    self.previousitem = self.selecteditem
                    if (self.selecteditem is not ""):
                        if xbmc.getCondVisibility("Container.Content(artists)"):
                            self._set_artist_details(self.selecteditem)
                        elif xbmc.getCondVisibility("Container.Content(albums)"):
                            self._set_album_details(self.selecteditem)
                        elif xbmc.getCondVisibility("ListItem.IsCollection | String.IsEqual(ListItem.DBTYPE,set)"):
                            self._set_movieset_details(self.selecteditem)
                        elif xbmc.getCondVisibility("Container.Content(movies)"):
                            self._set_movie_details(self.selecteditem)
                        elif xbmc.getCondVisibility("Container.Content(episodes)"):
                            self._set_episode_details(self.selecteditem)
                        elif xbmc.getCondVisibility("Container.Content(musicvideos)"):
                            self._set_musicvideo_details(self.selecteditem)
                        else:
                            clear_properties()
                    else:
                        clear_properties()
            elif xbmc.getCondVisibility("Container.Content(seasons) + !Window.IsActive(movieinformation)"):
                HOME.setProperty("SeasonPoster", xbmc.getInfoLabel("ListItem.Icon"))
                HOME.setProperty("SeasonID", xbmc.getInfoLabel("ListItem.DBID"))
                HOME.setProperty("SeasonNumber", xbmc.getInfoLabel("ListItem.Season"))
            elif xbmc.getCondVisibility("Window.IsActive(videos) + [Container.Content(directors) | Container.Content(actors) | Container.Content(genres) | Container.Content(years) | Container.Content(studios) | Container.Content(countries) | Container.Content(tags)]"):
                self.selecteditem = xbmc.getInfoLabel("ListItem.Label")
                if (self.selecteditem != self.previousitem):
                    clear_properties()
                    self.previousitem = self.selecteditem
                    if (self.selecteditem != "") and xbmc.getCondVisibility("!ListItem.IsParentFolder"):
                        self.setMovieDetailsforCategory()
            elif xbmc.getCondVisibility("Container.Content(years) | Container.Content(genres)"):
                self.selecteditem = xbmc.getInfoLabel("ListItem.Label")
                if (self.selecteditem != self.previousitem):
                    clear_properties()
                    self.previousitem = self.selecteditem
                    if (self.selecteditem != "") and xbmc.getCondVisibility("!ListItem.IsParentFolder"):
                        self.setMusicDetailsforCategory()
            elif xbmc.getCondVisibility('Window.IsActive(screensaver)'):
                xbmc.sleep(1000)
            else:
                self.previousitem = ""
                self.selecteditem = ""
                clear_properties()
                xbmc.sleep(500)
            if xbmc.getCondVisibility("String.IsEmpty(Window(home).Property(skininfos_daemon_running))"):
                clear_properties()
                self._stop = True
            xbmc.sleep(100)

    def _set_song_details(self, dbid):  # unused, needs fixing
        json_response = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideos", "params": {"properties": ["artist", "file"], "sort": { "method": "artist" } }, "id": 1}')
        clear_properties()
        if ("result" in json_response) and ('musicvideos' in json_response['result']):
            set_movie_properties(json_query)

    def _set_artist_details(self, dbid):
        json_response = Get_JSON_response('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"properties": ["title", "year", "albumlabel", "playcount", "thumbnail"], "sort": { "method": "label" }, "filter": {"artistid": %s} }, "id": 1}' % dbid)
        clear_properties()
        if ("result" in json_response) and ('albums' in json_response['result']):
            set_artist_properties(json_response)

    def _set_movie_details(self, dbid):
        json_response = Get_JSON_response('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["streamdetails","set","setid","cast"], "movieid":%s }, "id": 1}' % dbid)
        clear_properties()
        if ("result" in json_response) and ('moviedetails' in json_response['result']):
            self._set_properties(json_response['result']['moviedetails'])

    def _set_episode_details(self, dbid):
        json_response = Get_JSON_response('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": {"properties": ["streamdetails","tvshowid","season"], "episodeid":%s }, "id": 1}' % dbid)
        clear_properties()
        if ('result' in json_response) and ('episodedetails' in json_response['result']):
            self._set_properties(json_response['result']['episodedetails'])
            seasonnumber = json_response['result']['episodedetails']['season']
            tvshowid = json_response['result']['episodedetails']['tvshowid']
            json_response = Get_JSON_response('{"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasons", "params": {"properties": ["thumbnail"], "tvshowid":%s }, "id": 1}' % tvshowid)
            for season in json_response["result"]["seasons"]:
                if season["label"].split(" ")[-1] == str(seasonnumber):
                    HOME.setProperty('SkinInfo.SeasonPoster', season["thumbnail"])

    def _set_musicvideo_details(self, dbid):
        json_response = Get_JSON_response('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideoDetails", "params": {"properties": ["streamdetails"], "musicvideoid":%s }, "id": 1}' % dbid)
        clear_properties()
        if ("result" in json_response) and ('musicvideodetails' in json_response['result']):
            self._set_properties(json_response['result']['musicvideodetails'])

    def _set_album_details(self, dbid):
        json_response = Get_JSON_response('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"properties": ["title", "track", "duration", "file", "lastplayed", "disc"], "sort": { "method": "label" }, "filter": {"albumid": %s} }, "id": 1}' % dbid)
        clear_properties()
        if ("result" in json_response) and ('songs' in json_response['result']):
            set_album_properties(json_response)

    def _set_movieset_details(self, dbid):
        json_response = Get_JSON_response('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieSetDetails", "params": {"setid": %s, "properties": [ "thumbnail" ], "movies": { "properties":  [ "rating", "art", "file", "year", "director", "writer","genre" , "thumbnail", "runtime", "studio", "plotoutline", "plot", "country", "streamdetails"], "sort": { "order": "ascending",  "method": "year" }} },"id": 1 }' % dbid)
        clear_properties()
        if ("result" in json_response) and ('setdetails' in json_response['result']):
            set_movie_properties(json_response)

    def setMovieDetailsforCategory(self):
        if xbmc.getCondVisibility("!ListItem.IsParentFolder"):
            count = 1
            path = xbmc.getInfoLabel("ListItem.FolderPath")
            json_response = Get_JSON_response('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "video", "properties": ["art"]}, "id": 1}' % (path))
            if ("result" in json_response) and ("files" in json_response["result"]):
                for movie in json_response["result"]["files"]:
                    HOME.setProperty('SkinInfo.Detail.Movie.%i.Path' % (count), movie["file"])
                    HOME.setProperty('SkinInfo.Detail.Movie.%i.Art(fanart)' % (count), movie["art"].get('fanart', ''))
                    HOME.setProperty('SkinInfo.Detail.Movie.%i.Art(poster)' % (count), movie["art"].get('poster', ''))
                    count += 1
                    if count > 19:
                        break

    def setMusicDetailsforCategory(self):
        if xbmc.getCondVisibility("!ListItem.IsParentFolder"):
            count = 1
            path = xbmc.getInfoLabel("ListItem.FolderPath")
            json_response = Get_JSON_response('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "music", "properties": ["fanart", "thumbnail"]}, "id": 1}' % (path))
            if ("result" in json_response) and ("files" in json_response["result"]):
                for artist in json_response["result"]["files"]:
                    if "id" in artist:
                        HOME.setProperty('SkinInfo.Detail.Music.%i.DBID' % (count), str(artist["id"]))
                        HOME.setProperty('SkinInfo.Detail.Music.%i.Art(fanart)' % (count), artist["fanart"])
                        HOME.setProperty('SkinInfo.Detail.Music.%i.Art(thumb)' % (count), artist["thumbnail"])
                        count += 1
                        if count > 19:
                            break

    def _set_properties(self, results):
        # Set language properties
        count = 1
        audio = results['streamdetails']['audio']
        subtitles = results['streamdetails']['subtitle']
        subs = []
        streams = []
        # Clear properties before setting new ones
        clear_properties()
        for item in audio:
            if str(item['language']) not in streams:
                streams.append(str(item['language']))
                WND.setProperty('SkinInfo.AudioLanguage.%d' % count, item['language'])
                WND.setProperty('SkinInfo.AudioCodec.%d' % count, item['codec'])
                WND.setProperty('SkinInfo.AudioChannels.%d' % count, str(item['channels']))
                count += 1
        count = 1
        for item in subtitles:
            if str(item['language']) not in subtitles:
                subs.append(str(item['language']))
                WND.setProperty('SkinInfo.SubtitleLanguage.%d' % count, item['language'])
                count += 1
        WND.setProperty('SkinInfo.SubtitleLanguage', " / ".join(subs))
        WND.setProperty('SkinInfo.AudioLanguage', " / ".join(streams))
        WND.setProperty('SkinInfo.SubtitleLanguage.Count', str(len(subs)))
        WND.setProperty('SkinInfo.AudioLanguage.Count', str(len(streams)))

try:
    params = dict(arg.split("=") for arg in sys.argv[1].split("&"))
except:
    params = {}
if xbmc.getCondVisibility("String.IsEmpty(Window(home).Property(skininfos_daemon_running))"):
    xbmc.executebuiltin('SetProperty(skininfos_daemon_running,True,home)')
    log("starting daemon")
    Daemon()
else:
    log("Daemon already active")
log('finished')
