import json

import xbmcaddon
import xbmc
import xbmcgui
import Utils as utils
from ClientInformation import ClientInformation
from NextUpInfo import NextUpInfo
from StillWatchingInfo import StillWatchingInfo
from UnwatchedInfo import UnwatchedInfo


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


    def onPlayBackStarted( self ):
        # Will be called when xbmc starts playing a file
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
                    WINDOW.setProperty("NextUpNotification.NowPlaying.Type",itemtype)
                    tvshowid = result["result"]["item"]["tvshowid"]
                    WINDOW.setProperty("NextUpNotification.NowPlaying.DBID",str(tvshowid))
                elif itemtype == "movie":
                    WINDOW.setProperty("NextUpNotification.NowPlaying.Type",itemtype)
                    id = result["result"]["item"]["id"]
                    WINDOW.setProperty("NextUpNotification.NowPlaying.DBID",str(id))

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
                        tvshow = utils.getJSON('VideoLibrary.GetTVShows', '{ "sort": { "order": "descending", "method": "random" }, "filter": {"and": [{"operator":"is", "field":"genre", "value":"%s"}, {"operator":"is", "field":"playcount", "value":"0"}]}, "properties": [ %s ],"limits":{"end":1} }' %(genretitle,self.fields_tvshows))
                    if not tvshow:
                        self.logMsg("Looking up tvshow without genre", 2)
                        tvshow = utils.getJSON('VideoLibrary.GetTVShows', '{ "sort": { "order": "descending", "method": "random" }, "filter": {"and": [{"operator":"is", "field":"playcount", "value":"0"}]}, "properties": [ %s ],"limits":{"end":1} }' %self.fields_tvshows)
                    self.logMsg("Got tvshow" + str(tvshow), 2)
                    tvshowid = tvshow[0]["tvshowid"]
                    episode = utils.getJSON('VideoLibrary.GetEpisodes', '{ "tvshowid": %d, "sort": {"method":"episode"}, "filter": {"and": [ {"field": "playcount", "operator": "lessthan", "value":"1"}, {"field": "season", "operator": "greaterthan", "value": "0"} ]}, "properties": [ %s ], "limits":{"end":1}}' %(tvshowid, self.fields_episodes))

                    if episode:
                        self.logMsg("Got details of next up episode %s" % str(episode), 2)
                        addonSettings = xbmcaddon.Addon(id='service.nextup.notification')
                        unwatchedPage = UnwatchedInfo("script-nextup-notification-UnwatchedInfo.xml",
                                                    addonSettings.getAddonInfo('path'), "default", "1080i")
                        unwatchedPage.setItem(episode[0])
                        self.logMsg("Calling display unwatched", 2)
                        unwatchedPage.show()
                        xbmc.sleep(10000)
                        self.logMsg("Calling close unwatched", 2)
                        unwatchedPage.close()

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
                if itemtype == "episode":
                    # Get the next up episode
                    addonSettings = xbmcaddon.Addon(id='service.nextup.notification')
                    playMode = addonSettings.getSetting("autoPlayMode")
                    currentepisodenumber = result["result"]["item"]["episode"]
                    currentseasonid = result["result"]["item"]["season"]
                    currentshowtitle = result["result"]["item"]["showtitle"]
                    tvshowid = result["result"]["item"]["tvshowid"]

                    # I am a STRM ###
                    if tvshowid == -1:
                        tvshowid, episodeid = self.iStream_fix(tvshowid, currentshowtitle, currentepisodenumber,
                                                               currentseasonid)
                        currentepisodeid = episodeid
                    else:
                        currentepisodeid = result["result"]["item"]["id"]

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
                                self.logMsg("played in a row settings %s" % str(playedinarownumber), 2)
                                self.logMsg("played in a row %s" % str(self.playedinarow), 2)
                                if int(self.playedinarow) <= int(playedinarownumber):
                                    self.logMsg(
                                        "showing next up page as played in a row is %s" % str(self.playedinarow), 2)
                                    nextUpPage.show()
                                else:
                                    self.logMsg(
                                        "showing still watching page as played in a row %s" % str(self.playedinarow), 2)
                                    stillWatchingPage.show()
                                playTime = xbmc.Player().getTime()
                                totalTime = xbmc.Player().getTotalTime()
                                while xbmc.Player().isPlaying() and (
                                                totalTime - playTime > 1) and not nextUpPage.isCancel() and not nextUpPage.isWatchNow() and not stillWatchingPage.isStillWatching() and not stillWatchingPage.isCancel():
                                    xbmc.sleep(100)
                                    try:
                                        playTime = xbmc.Player().getTime()
                                        totalTime = xbmc.Player().getTotalTime()
                                    except:
                                        pass

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
                                if (shouldPlayDefault and playMode == "0") or (
                                        shouldPlayNonDefault and playMode == "1"):
                                    self.logMsg("playing media episode id %s" % str(episodeid), 2)
                                    # Play media
                                    xbmc.executeJSONRPC(
                                        '{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", '
                                        '"params": { "item": {"episodeid": ' + str(episode["episodeid"]) + '} } }')
