import json

import xbmcaddon
import xbmc
import xbmcgui
import Utils as utils
import AddonSignals
import library
from ClientInformation import ClientInformation
from NextUpInfo import NextUpInfo
from StillWatchingInfo import StillWatchingInfo
from UnwatchedInfo import UnwatchedInfo
from PostPlayInfo import PostPlayInfo

LIBRARY = library.LibraryFunctions()
# service class for playback monitoring
class Player(xbmc.Player):
    # Borg - multiple instances, shared state
    _shared_state = {}

    xbmcplayer = xbmc.Player()
    clientInfo = ClientInformation()

    addonName = clientInfo.getAddonName()
    addonId = clientInfo.getAddonId()
    addon = xbmcaddon.Addon(id=addonId)

    logLevel = 0
    currenttvshowid = None
    currentepisodeid = None
    playedinarow = 1
    fields_base = '"dateadded", "file", "lastplayed","plot", "title", "art", "playcount",'
    fields_file = fields_base + '"streamdetails", "director", "resume", "runtime",'
    fields_tvshows = fields_base + '"sorttitle", "mpaa", "premiered", "year", "episode", "watchedepisodes", "votes", "rating", "studio", "season", "genre", "episodeguide", "tag", "originaltitle", "imdbnumber"'
    fields_episodes = fields_file + '"cast", "productioncode", "rating", "votes", "episode", "showtitle", "tvshowid", "season", "firstaired", "writer", "originaltitle"'
    postplaywindow = None

    def __init__(self, *args):
        self.__dict__ = self._shared_state
        self.logMsg("Starting playback monitor service", 1)

    def logMsg(self, msg, lvl=1):
        self.className = self.__class__.__name__
        utils.logMsg("%s %s" % (self.addonName, self.className), msg, int(lvl))

    def json_query(self, query, ret):
        try:
            xbmc_request = json.dumps(query)
            result = xbmc.executeJSONRPC(xbmc_request)
            result = unicode(result, 'utf-8', errors='ignore')
            if ret:
                return json.loads(result)['result']

            else:
                return json.loads(result)
        except:
            xbmc_request = json.dumps(query)
            result = xbmc.executeJSONRPC(xbmc_request)
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg(json.loads(result), 1)
            return json.loads(result)

    def onPlayBackStarted(self):
        # Will be called when xbmc starts playing a file
        self.postplaywindow = None
        WINDOW = xbmcgui.Window(10000)
        WINDOW.clearProperty("NextUpNotification.NowPlaying.DBID")
        WINDOW.clearProperty("NextUpNotification.NowPlaying.Type")

        # Get the active player
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
        result = unicode(result, 'utf-8', errors='ignore')
        self.logMsg("Got active player " + result, 2)
        result = json.loads(result)

        # Seems to work too fast loop whilst waiting for it to become active
        while not result["result"]:
            result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg("Got active player " + result, 2)
            result = json.loads(result)

        if 'result' in result and result["result"][0] is not None:
            playerid = result["result"][0]["playerid"]

            # Get details of the playing media
            self.logMsg("Getting details of now  playing media", 1)
            result = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetItem", "params": {"playerid": ' + str(
                    playerid) + ', "properties": ["showtitle", "tvshowid", "episode", "season", "playcount","genre"] } }')
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg("Got details of now playing media" + result, 2)

            result = json.loads(result)
            if 'result' in result:
                itemtype = result["result"]["item"]["type"]
                if itemtype == "episode":
                    WINDOW.setProperty("NextUpNotification.NowPlaying.Type", itemtype)
                    tvshowid = result["result"]["item"]["tvshowid"]
                    WINDOW.setProperty("NextUpNotification.NowPlaying.DBID", str(tvshowid))
                elif itemtype == "movie":
                    WINDOW.setProperty("NextUpNotification.NowPlaying.Type", itemtype)
                    id = result["result"]["item"]["id"]
                    WINDOW.setProperty("NextUpNotification.NowPlaying.DBID", str(id))


    def onPlayBackEnded(self):
        self.logMsg("playback ended ", 2)
        if self.postplaywindow is not None:
           self.showPostPlay()

    def iStream_fix(self, show_npid, showtitle, episode_np, season_np):

        # streams from iStream dont provide the showid and epid for above
        # they come through as tvshowid = -1, but it has episode no and season no and show name
        # need to insert work around here to get showid from showname, and get epid from season and episode no's
        # then need to ignore prevcheck
        self.logMsg('fixing strm, data follows...')
        self.logMsg('show_npid = ' + str(show_npid))
        self.logMsg('showtitle = ' + str(showtitle))
        self.logMsg('episode_np = ' + str(episode_np))
        self.logMsg('season_np = ' + str(season_np))

        show_request_all = {"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title"]},
                            "id": "1"}
        eps_query = {"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {
            "properties": ["season", "episode", "runtime", "resume", "playcount", "tvshowid", "lastplayed", "file"],
            "tvshowid": "1"}, "id": "1"}

        ep_npid = " "

        redo = True
        count = 0
        while redo and count < 2:  # this ensures the section of code only runs twice at most [ only runs once fine ?
            redo = False
            count += 1
            if show_npid == -1 and showtitle and episode_np and season_np:
                tmp_shows = self.json_query(show_request_all, True)
                self.logMsg('tmp_shows = ' + str(tmp_shows))
                if 'tvshows' in tmp_shows:
                    for x in tmp_shows['tvshows']:
                        if x['label'] == showtitle:
                            show_npid = x['tvshowid']
                            eps_query['params']['tvshowid'] = show_npid
                            tmp_eps = self.json_query(eps_query, True)
                            self.logMsg('tmp eps = ' + str(tmp_eps))
                            if 'episodes' in tmp_eps:
                                for y in tmp_eps['episodes']:
                                    if (y['season']) == season_np and (y['episode']) == episode_np:
                                        ep_npid = y['episodeid']
                                        self.logMsg('playing epid stream = ' + str(ep_npid))

        return show_npid, ep_npid

    def findNextEpisode(self, result, currentFile, includeWatched):
        self.logMsg("Find next episode called", 1)
        position = 0
        for episode in result["result"]["episodes"]:
            # find position of current episode
            if self.currentepisodeid == episode["episodeid"]:
                # found a match so add 1 for the next and get out of here
                position += 1
                break
            position += 1
        # check if it may be a multi-part episode
        while result["result"]["episodes"][position]["file"] == currentFile:
            position += 1
        # skip already watched episodes?
        while not includeWatched and result["result"]["episodes"][position]["playcount"] > 1:
            position += 1

        # now return the episode
        self.logMsg("Find next episode found next episode in position: " + str(position), 1)
        try:
            episode = result["result"]["episodes"][position]
        except:
            # no next episode found
            episode = None

        return episode

    def findCurrentEpisode(self, result, currentFile):
        self.logMsg("Find current episode called", 1)
        position = 0
        for episode in result["result"]["episodes"]:
            # find position of current episode
            if self.currentepisodeid == episode["episodeid"]:
                # found a match so get out of here
                break
            position += 1

        # now return the episode
        self.logMsg("Find current episode found episode in position: " + str(position), 1)
        try:
            episode = result["result"]["episodes"][position]
        except:
            # no next episode found
            episode = None

        return episode

    def displayRandomUnwatched(self):
        currentFile = xbmc.Player().getPlayingFile()

        # Get the active player
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
        result = unicode(result, 'utf-8', errors='ignore')
        self.logMsg("Got active player " + result, 2)
        result = json.loads(result)

        # Seems to work too fast loop whilst waiting for it to become active
        while not result["result"]:
            result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg("Got active player " + result, 2)
            result = json.loads(result)

        if 'result' in result and result["result"][0] is not None:
            playerid = result["result"][0]["playerid"]

            # Get details of the playing media
            self.logMsg("Getting details of playing media", 1)
            result = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetItem", "params": {"playerid": ' + str(
                    playerid) + ', "properties": ["showtitle", "tvshowid", "episode", "season", "playcount","genre"] } }')
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg("Got details of playing media" + result, 2)

            result = json.loads(result)
            if 'result' in result:
                itemtype = result["result"]["item"]["type"]
                if itemtype == "episode":
                    # playing an episode so find a random unwatched show from the same genre
                    genres = result["result"]["item"]["genre"]
                    if genres:
                        genretitle = genres[0]
                        self.logMsg("Looking up tvshow for genre " + genretitle, 2)
                        tvshow = utils.getJSON('VideoLibrary.GetTVShows', '{ "sort": { "order": "descending", "method": "random" }, "filter": {"and": [{"operator":"is", "field":"genre", "value":"%s"}, {"operator":"is", "field":"playcount", "value":"0"}]}, "properties": [ %s ],"limits":{"end":1} }' % (genretitle, self.fields_tvshows))
                    if not tvshow:
                        self.logMsg("Looking up tvshow without genre", 2)
                        tvshow = utils.getJSON('VideoLibrary.GetTVShows', '{ "sort": { "order": "descending", "method": "random" }, "filter": {"and": [{"operator":"is", "field":"playcount", "value":"0"}]}, "properties": [ %s ],"limits":{"end":1} }' % self.fields_tvshows)
                    self.logMsg("Got tvshow" + str(tvshow), 2)
                    tvshowid = tvshow[0]["tvshowid"]
                    episode = utils.getJSON('VideoLibrary.GetEpisodes', '{ "tvshowid": %d, "sort": {"method":"episode"}, "filter": {"and": [ {"field": "playcount", "operator": "lessthan", "value":"1"}, {"field": "season", "operator": "greaterthan", "value": "0"} ]}, "properties": [ %s ], "limits":{"end":1}}' % (tvshowid, self.fields_episodes))

                    if episode:
                        self.logMsg("Got details of next up episode %s" % str(episode), 2)
                        addonSettings = xbmcaddon.Addon(id='service.nextup.notification')
                        unwatchedPage = UnwatchedInfo("script-nextup-notification-UnwatchedInfo.xml",
                                                      addonSettings.getAddonInfo('path'), "default", "1080i")
                        unwatchedPage.setItem(episode[0])
                        self.logMsg("Calling display unwatched", 2)
                        unwatchedPage.show()
                        monitor = xbmc.Monitor()
                        monitor.waitForAbort(10)
                        self.logMsg("Calling close unwatched", 2)
                        unwatchedPage.close()
                        del monitor

    def strm_query(self, result):
        try:
            self.logMsg('strm_query start')
            Myitemtype = result["result"]["item"]["type"]
            if Myitemtype == "episode":
                return True
            Myepisodenumber = result["result"]["item"]["episode"]
            Myseasonid = result["result"]["item"]["season"]
            Mytvshowid = result["result"]["item"]["tvshowid"]
            Myshowtitle = result["result"]["item"]["showtitle"]
            self.logMsg('strm_query end')

            if Mytvshowid == -1:
                return True

            else:
                return False
        except:
            self.logMsg('strm_query except')
            return False

    def postPlayPlayback(self):
        currentFile = xbmc.Player().getPlayingFile()

        # Get the active player
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
        result = unicode(result, 'utf-8', errors='ignore')
        self.logMsg("Got active player " + result, 2)
        result = json.loads(result)

        # Seems to work too fast loop whilst waiting for it to become active
        while not result["result"]:
            result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg("Got active player " + result, 2)
            result = json.loads(result)

        if 'result' in result and result["result"][0] is not None:
            playerid = result["result"][0]["playerid"]

            # Get details of the playing media
            self.logMsg("Getting details of playing media", 1)
            result = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetItem", "params": {"playerid": ' + str(
                    playerid) + ', "properties": ["showtitle", "tvshowid", "episode", "season", "playcount"] } }')
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg("Got details of playing media" + result, 2)

            result = json.loads(result)
            if 'result' in result:
                itemtype = result["result"]["item"]["type"]

            if self.strm_query(result):
                addonSettings = xbmcaddon.Addon(id='service.nextup.notification')
                playMode = addonSettings.getSetting("autoPlayMode")
                currentepisodenumber = result["result"]["item"]["episode"]
                currentseasonid = result["result"]["item"]["season"]
                currentshowtitle = result["result"]["item"]["showtitle"]
                tvshowid = result["result"]["item"]["tvshowid"]
                shortplayMode = addonSettings.getSetting("shortPlayMode")
                shortplayNotification= addonSettings.getSetting("shortPlayNotification")
                shortplayLength = int(addonSettings.getSetting("shortPlayLength")) * 60


                if (itemtype == "episode"):
                    # Get the next up episode
                    currentepisodeid = result["result"]["item"]["id"]
                elif tvshowid == -1:
                    # I am a STRM ###
                    tvshowid, episodeid = self.iStream_fix(tvshowid, currentshowtitle, currentepisodenumber, currentseasonid)
                    currentepisodeid = episodeid
            else:
                # wtf am i doing here error.. ####
                self.logMsg("Error: cannot determine if episode", 1)
                return

            self.currentepisodeid = currentepisodeid
            self.logMsg("Getting details of next up episode for tvshow id: " + str(tvshowid), 1)
            if self.currenttvshowid != tvshowid:
                self.currenttvshowid = tvshowid
                self.playedinarow = 1

            result = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": %d, '
                '"properties": [ "title", "playcount", "season", "episode", "showtitle", "plot", '
                '"file", "rating", "resume", "tvshowid", "art", "firstaired", "runtime", "writer", '
                '"dateadded", "lastplayed" , "streamdetails"], "sort": {"method": "episode"}}, "id": 1}'
                % tvshowid)

            if result:
                result = unicode(result, 'utf-8', errors='ignore')
                result = json.loads(result)
                self.logMsg("Got details of next up episode %s" % str(result), 2)
                xbmc.sleep(100)

                # Find the next unwatched and the newest added episodes
                if "result" in result and "episodes" in result["result"]:
                    includeWatched = addonSettings.getSetting("includeWatched") == "true"
                    episode = self.findNextEpisode(result, currentFile, includeWatched)
                    current_episode = self.findCurrentEpisode(result,currentFile)
                    self.logMsg("episode details %s" % str(episode), 2)
                    episodeid = episode["episodeid"]

                    if current_episode:
                        # we have something to show
                        postPlayPage = PostPlayInfo("script-nextup-notification-PostPlayInfo.xml",
                                                addonSettings.getAddonInfo('path'), "default", "1080i")
                        postPlayPage.setItem(episode)
                        postPlayPage.setPreviousItem(current_episode)
                        upnextitems = self.parse_tvshows_recommended(6)
                        postPlayPage.setUpNextList(upnextitems)
                        playedinarownumber = addonSettings.getSetting("playedInARow")
                        playTime = xbmc.Player().getTime()
                        totalTime =  xbmc.Player().getTotalTime()
                        self.logMsg("played in a row settings %s" % str(playedinarownumber), 2)
                        self.logMsg("played in a row %s" % str(self.playedinarow), 2)
                        if int(self.playedinarow) <= int(playedinarownumber):
                            if (shortplayNotification == "false") and (shortplayLength >= totalTime) and (shortplayMode == "true"):
                                self.logMsg("hiding notification for short videos")
                            else:
                                postPlayPage.setStillWatching(False)
                        else:
                            if (shortplayNotification == "false") and (shortplayLength >= totalTime) and (shortplayMode == "true"):
                                self.logMsg("hiding notification for short videos")
                            else:
                                postPlayPage.setStillWatching(True)
                        while xbmc.Player().isPlaying() and (
                                        totalTime - playTime > 8):
                            xbmc.sleep(100)
                            try:
                                playTime = xbmc.Player().getTime()
                                totalTime = xbmc.Player().getTotalTime()
                            except:
                                pass

                        self.postplaywindow = postPlayPage

    def showPostPlay(self):
        self.logMsg("showing postplay window")
        p = self.postplaywindow.doModal()
        autoplayed = xbmcgui.Window(10000).getProperty("NextUpNotification.AutoPlayed")
        self.logMsg("showing postplay window completed autoplayed? "+str(autoplayed))
        if autoplayed:
            self.playedinarow += 1
        else:
            self.playedinarow = 1
        del p

    def parse_tvshows_recommended(self,limit):
        items = []
        prefix = "recommended-episodes"
        json_query = LIBRARY._fetch_recommended_episodes()

        if json_query:
            # First unplayed episode of recent played tvshows
            self.logMsg("getting next up tvshows " + json_query, 2)
            json_query = json.loads(json_query)
            if "result" in json_query and 'tvshows' in json_query['result']:
                count = -1
                for item in json_query['result']['tvshows']:
                    if xbmc.abortRequested:
                        break
                    if count == -1:
                        count += 1
                        continue
                    json_query2 = xbmcgui.Window(10000).getProperty(prefix + "-data-" + str(item['tvshowid']))
                    if json_query2:
                        self.logMsg("getting next up episodes " + json_query2, 2)
                        json_query2 = json.loads(json_query2)
                        if "result" in json_query2 and json_query2['result'] is not None and 'episodes' in json_query2['result']:
                            for item2 in json_query2['result']['episodes']:
                                episode = "%.2d" % float(item2['episode'])
                                season = "%.2d" % float(item2['season'])
                                episodeno = "s%se%s" % (season, episode)
                                break
                            plot = item2['plot']
                            episodeid = str(item2['episodeid'])
                            if len(item['studio']) > 0:
                                studio = item['studio'][0]
                            else:
                                studio = ""
                            if "director" in item2:
                                director = " / ".join(item2['director'])
                            if "writer" in item2:
                                writer = " / ".join(item2['writer'])

                            liz = xbmcgui.ListItem(item2['title'])
                            liz.setPath(item2['file'])
                            liz.setProperty('IsPlayable', 'true')
                            liz.setInfo(type="Video", infoLabels={"Title": item2['title'],
                                                                  "Episode": item2['episode'],
                                                                  "Season": item2['season'],
                                                                  "Studio": studio,
                                                                  "Premiered": item2['firstaired'],
                                                                  "Plot": plot,
                                                                  "TVshowTitle": item2['showtitle'],
                                                                  "Rating": str(float(item2['rating'])),
                                                                  "MPAA": item['mpaa'],
                                                                  "Playcount": item2['playcount'],
                                                                  "Director": director,
                                                                  "Writer": writer,
                                                                  "mediatype": "episode"})
                            liz.setProperty("episodeid",episodeid)
                            liz.setProperty("episodeno", episodeno)
                            liz.setProperty("resumetime", str(item2['resume']['position']))
                            liz.setProperty("totaltime", str(item2['resume']['total']))
                            liz.setProperty("type",'episode')
                            liz.setProperty("fanart_image", item2['art'].get('tvshow.fanart', ''))
                            liz.setProperty("dbid", str(item2['episodeid']))
                            liz.setArt(item2['art'])
                            liz.setThumbnailImage(item2['art'].get('thumb', ''))
                            liz.setIconImage('DefaultTVShows.png')
                            hasVideo = False
                            for key, value in item2['streamdetails'].iteritems():
                                for stream in value:
                                    if 'video' in key:
                                        hasVideo = True
                                    liz.addStreamInfo(key, stream)

                            # if duration wasnt in the streaminfo try adding the scraped one
                            if not hasVideo:
                                stream = {'duration': item2['runtime']}
                                liz.addStreamInfo("video", stream)

                            items.append(liz)

                            count += 1
                            if count == limit:
                                break
                    if count == limit:
                        break
            del json_query
        self.logMsg("getting next up episodes completed ", 2)
        return items

    def autoPlayPlayback(self):
        currentFile = xbmc.Player().getPlayingFile()

        # Get the active player
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
        result = unicode(result, 'utf-8', errors='ignore')
        self.logMsg("Got active player " + result, 2)
        result = json.loads(result)

        # Seems to work too fast loop whilst waiting for it to become active
        while not result["result"]:
            result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg("Got active player " + result, 2)
            result = json.loads(result)

        if 'result' in result and result["result"][0] is not None:
            playerid = result["result"][0]["playerid"]

            # Get details of the playing media
            self.logMsg("Getting details of playing media", 1)
            result = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetItem", "params": {"playerid": ' + str(
                    playerid) + ', "properties": ["showtitle", "tvshowid", "episode", "season", "playcount"] } }')
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg("Got details of playing media" + result, 2)

            result = json.loads(result)
            if 'result' in result:
                itemtype = result["result"]["item"]["type"]

            if self.strm_query(result):
                addonSettings = xbmcaddon.Addon(id='service.nextup.notification')
                playMode = addonSettings.getSetting("autoPlayMode")
                currentepisodenumber = result["result"]["item"]["episode"]
                currentseasonid = result["result"]["item"]["season"]
                currentshowtitle = result["result"]["item"]["showtitle"]
                tvshowid = result["result"]["item"]["tvshowid"]
                shortplayMode = addonSettings.getSetting("shortPlayMode")
                shortplayNotification= addonSettings.getSetting("shortPlayNotification")
                shortplayLength = int(addonSettings.getSetting("shortPlayLength")) * 60


                if (itemtype == "episode"):
                    # Get the next up episode
                    currentepisodeid = result["result"]["item"]["id"]
                elif tvshowid == -1:
                    # I am a STRM ###
                    tvshowid, episodeid = self.iStream_fix(tvshowid, currentshowtitle, currentepisodenumber, currentseasonid)
                    currentepisodeid = episodeid
            else:
                # wtf am i doing here error.. ####
                self.logMsg("Error: cannot determine if episode", 1)
                return

            self.currentepisodeid = currentepisodeid
            self.logMsg("Getting details of next up episode for tvshow id: " + str(tvshowid), 1)
            if self.currenttvshowid != tvshowid:
                self.currenttvshowid = tvshowid
                self.playedinarow = 1

            result = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": %d, '
                '"properties": [ "title", "playcount", "season", "episode", "showtitle", "plot", '
                '"file", "rating", "resume", "tvshowid", "art", "firstaired", "runtime", "writer", '
                '"dateadded", "lastplayed" , "streamdetails"], "sort": {"method": "episode"}}, "id": 1}'
                % tvshowid)

            if result:
                result = unicode(result, 'utf-8', errors='ignore')
                result = json.loads(result)
                self.logMsg("Got details of next up episode %s" % str(result), 2)
                xbmc.sleep(100)

                # Find the next unwatched and the newest added episodes
                if "result" in result and "episodes" in result["result"]:
                    includeWatched = addonSettings.getSetting("includeWatched") == "true"
                    episode = self.findNextEpisode(result, currentFile, includeWatched)

                    if episode is None:
                        # no episode get out of here
                        return
                    self.logMsg("episode details %s" % str(episode), 2)
                    episodeid = episode["episodeid"]

                    if includeWatched:
                        includePlaycount = True
                    else:
                        includePlaycount = episode["playcount"] == 0
                    if includePlaycount and currentepisodeid != episodeid:
                        # we have a next up episode
                        nextUpPage = NextUpInfo("script-nextup-notification-NextUpInfo.xml",
                                                addonSettings.getAddonInfo('path'), "default", "1080i")
                        nextUpPage.setItem(episode)
                        stillWatchingPage = StillWatchingInfo(
                            "script-nextup-notification-StillWatchingInfo.xml",
                            addonSettings.getAddonInfo('path'), "default", "1080i")
                        stillWatchingPage.setItem(episode)
                        playedinarownumber = addonSettings.getSetting("playedInARow")
                        playTime = xbmc.Player().getTime()
                        totalTime =  xbmc.Player().getTotalTime()
                        self.logMsg("played in a row settings %s" % str(playedinarownumber), 2)
                        self.logMsg("played in a row %s" % str(self.playedinarow), 2)

                        if int(self.playedinarow) <= int(playedinarownumber):
                            self.logMsg(
                                "showing next up page as played in a row is %s" % str(self.playedinarow), 2)
                            if (shortplayNotification == "false") and (shortplayLength >= totalTime) and (shortplayMode == "true"):
                                self.logMsg("hiding notification for short videos")
                            else:
                                nextUpPage.show()
                        else:
                            self.logMsg(
                                "showing still watching page as played in a row %s" % str(self.playedinarow), 2)
                            if (shortplayNotification == "false") and (shortplayLength >= totalTime) and (shortplayMode == "true"):
                                self.logMsg("hiding notification for short videos")
                            else:
                                stillWatchingPage.show()
                        while xbmc.Player().isPlaying() and (
                                        totalTime - playTime > 1) and not nextUpPage.isCancel() and not nextUpPage.isWatchNow() and not stillWatchingPage.isStillWatching() and not stillWatchingPage.isCancel():
                            xbmc.sleep(100)
                            try:
                                playTime = xbmc.Player().getTime()
                                totalTime = xbmc.Player().getTotalTime()
                            except:
                                pass
                        if shortplayLength >= totalTime and shortplayMode == "true":
                            #play short video and don't add to playcount
                            self.playedinarow += 0
                            self.logMsg("Continuing short video autoplay - %s")
                            if nextUpPage.isWatchNow() or stillWatchingPage.isStillWatching():
                                self.playedinarow = 1
                            shouldPlayDefault = not nextUpPage.isCancel()
                        else:
                            if int(self.playedinarow) <= int(playedinarownumber):
                                nextUpPage.close()
                                shouldPlayDefault = not nextUpPage.isCancel()
                                shouldPlayNonDefault = nextUpPage.isWatchNow()
                            else:
                                stillWatchingPage.close()
                                shouldPlayDefault = stillWatchingPage.isStillWatching()
                                shouldPlayNonDefault = stillWatchingPage.isStillWatching()

                            if nextUpPage.isWatchNow() or stillWatchingPage.isStillWatching():
                                self.playedinarow = 1
                            else:
                                self.playedinarow += 1

                        if (shouldPlayDefault and playMode == "0") or (shouldPlayNonDefault and playMode == "1"):
                            self.logMsg("playing media episode id %s" % str(episodeid), 2)
                            # Signal to trakt previous episode watched
                            AddonSignals.sendSignal("NEXTUPWATCHEDSIGNAL", {'episodeid': self.currentepisodeid})

                            # Play media
                            xbmc.executeJSONRPC(
                                '{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", '
                                '"params": { "item": {"episodeid": ' + str(episode["episodeid"]) + '} } }')
