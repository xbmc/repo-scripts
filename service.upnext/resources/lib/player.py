import xbmc
import resources.lib.utils as utils
from resources.lib.upnext import UpNext
from resources.lib.stillwatching import StillWatching
import sys

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

# service class for playback monitoring
class Player(xbmc.Player):
    # Borg - multiple instances, shared state
    _shared_state = {}

    xbmcplayer = xbmc.Player()
    logLevel = 0
    currenttvshowid = None
    currentepisodeid = None
    playedinarow = 1

    def __init__(self, *args):
        self.__dict__ = self._shared_state
        self.logMsg("Starting playback monitor service", 1)
        self.setupFromSettings()
        xbmc.Player.__init__(self)

    def logMsg(self, msg, lvl=1):
        self.className = self.__class__.__name__
        utils.logMsg("%s %s", (utils.addon_name(), self.className), msg, int(lvl))

    def onPlayBackStarted(self):
        # Will be called when kodi starts playing a file
        self.addon_data = {}
        if utils.settings("developerMode") == "true":
            self.developerPlayPlayback()

    def getNowPlaying(self):
        # Get the active player
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
        result = unicode(result, 'utf-8', errors='ignore')
        self.logMsg("Got active player %s", result, 2)
        result = json.loads(result)

        # Seems to work too fast loop whilst waiting for it to become active
        while not result["result"]:
            result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg("Got active player %s", result, 2)
            result = json.loads(result)

        if 'result' in result and result["result"][0] is not None:
            playerid = result["result"][0]["playerid"]

            # Get details of the playing media
            self.logMsg("Getting details of now  playing media", 1)
            result = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetItem", "params": {"playerid": ' + str(
                    playerid) + ', "properties": ["showtitle", "tvshowid", "episode", "season", "playcount","genre","plotoutline"] } }')
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg("Got details of now playing media %s" , result, 2)

            result = json.loads(result)
            return result


    def showtitle_to_id(self, title):
        query = {
            "jsonrpc": "2.0",
            "method": "VideoLibrary.GetTVShows",
            "params": {
                "properties": ["title"]
            },
            "id": "libTvShows"
        }
        try:
            json_result = json.loads(xbmc.executeJSONRPC(json.dumps(query, encoding='utf-8')))
            if 'result' in json_result and 'tvshows' in json_result['result']:
                json_result = json_result['result']['tvshows']
                for tvshow in json_result:
                    if tvshow['label'] == title:
                        return tvshow['tvshowid']
            return '-1'
        except Exception:
            return '-1'

    def get_episode_id(self, showid, showseason, showepisode):
        showseason = int(showseason)
        showepisode = int(showepisode)
        episodeid = 0
        query = {
            "jsonrpc": "2.0",
            "method": "VideoLibrary.GetEpisodes",
            "params": {
                "properties": ["season", "episode"],
                "tvshowid": int(showid)
            },
            "id": "1"
        }
        try:
            json_result = json.loads(xbmc.executeJSONRPC(json.dumps(query, encoding='utf-8')))
            if 'result' in json_result and 'episodes' in json_result['result']:
                json_result = json_result['result']['episodes']
                for episode in json_result:
                    if episode['season'] == showseason and episode['episode'] == showepisode:
                        if 'episodeid' in episode:
                            episodeid = episode['episodeid']
            return episodeid
        except Exception:
            return episodeid

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
        self.logMsg("Find next episode found next episode in position: %s", str(position), 1)
        try:
            episode = result["result"]["episodes"][position]
        except:
            # no next episode found
            episode = None

        return episode

    def handle_kodi_lookup_of_episode(self, tvshowid, currentFile, includeWatched):
        result = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": %d, '
            '"properties": [ "title", "playcount", "season", "episode", "showtitle", "plot", '
            '"file", "rating", "resume", "tvshowid", "art", "firstaired", "runtime", "writer", '
            '"dateadded", "lastplayed" , "streamdetails"], "sort": {"method": "episode"}}, "id": 1}'
            % tvshowid)

        if result:
            result = unicode(result, 'utf-8', errors='ignore')
            result = json.loads(result)
            self.logMsg("Got details of next up episode %s", str(result), 2)
            xbmc.sleep(100)

            # Find the next unwatched and the newest added episodes
            if "result" in result and "episodes" in result["result"]:
                episode = self.findNextEpisode(result, currentFile, includeWatched)
                return episode

    def handle_kodi_lookup_of_current_episode(self, tvshowid):
        result = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": %d, '
            '"properties": [ "title", "playcount", "season", "episode", "showtitle", "plot", '
            '"file", "rating", "resume", "tvshowid", "art", "firstaired", "runtime", "writer", '
            '"dateadded", "lastplayed" , "streamdetails"], "sort": {"method": "episode"}}, "id": 1}'
            % tvshowid)
        self.logMsg("Find current episode called", 1)
        position = 0
        if result:
            result = unicode(result, 'utf-8', errors='ignore')
            result = json.loads(result)
            xbmc.sleep(100)

            # Find the next unwatched and the newest added episodes
            if "result" in result and "episodes" in result["result"]:
                for episode in result["result"]["episodes"]:
                    # find position of current episode
                    if self.currentepisodeid == episode["episodeid"]:
                        # found a match so get out of here
                        break
                    position += 1

                # now return the episode
                self.logMsg("Find current episode found episode in position: %s", str(position), 1)
                try:
                    episode = result["result"]["episodes"][position]
                except:
                    # no next episode found
                    episode = None

                return episode

    def handle_addon_lookup_of_next_episode(self):
        if self.addon_data:
            self.logMsg("handle_addon_lookup_of_next_episode returning data %s ", str(self.addon_data["next_episode"]), 2)
            return self.addon_data["next_episode"]


    def handle_addon_lookup_of_current_episode(self):
        if self.addon_data:
            self.logMsg("handle_addon_lookup_of_current episode returning data %s ", str(self.addon_data["current_episode"]), 2)
            return self.addon_data["current_episode"]

    def addon_data_received(self, data):
        self.logMsg("addon_data_received called with data %s ", str(data), 2)
        self.addon_data = data

    def notification_time(self):
        return self.addon_data.get('notification_time') or utils.settings('autoPlaySeasonTime')

    def handle_now_playing_result(self, result):
        if 'result' in result:
            itemtype = result["result"]["item"]["type"]
            self.currentepisodenumber = result["result"]["item"]["episode"]
            self.currentseasonid = result["result"]["item"]["season"]
            self.currentshowtitle = result["result"]["item"]["showtitle"].encode('utf-8')
            self.currentshowtitle = utils.unicodetoascii( self.currentshowtitle)
            self.tvshowid = result["result"]["item"]["tvshowid"]
            if itemtype == "episode":
                # Try to get tvshowid by showtitle from kodidb if tvshowid is -1 like in strm streams which are added to kodi db
                if int(self.tvshowid) == -1:
                    self.tvshowid = self.showtitle_to_id(title=self.currentshowtitle)
                    self.logMsg("Fetched missing tvshowid %s", str( self.tvshowid), 2)

                # Get current episodeid
                currentepisodeid = self.get_episode_id(showid=str(self.tvshowid), showseason=self.currentseasonid, showepisode=self.currentepisodenumber)

            else:
                # wtf am i doing here error.. ####
                self.logMsg("Error: cannot determine if episode", 1)
                return False
        else:
            # wtf am i doing here error.. ####
            self.logMsg("Error: no result returned from check on now playing...exiting", 1)
            return False

        self.currentepisodeid = currentepisodeid
        if self.currenttvshowid != self.tvshowid:
            self.currenttvshowid = self.tvshowid
            self.playedinarow = 1

        return True

    def setupFromSettings(self):
        self.playMode = utils.settings("autoPlayMode")
        self.shortplayMode = utils.settings("shortPlayMode")
        self.shortplayNotification = utils.settings("shortPlayNotification")
        self.shortplayLength = int(utils.settings("shortPlayLength")) * 60
        self.includeWatched = utils.settings("includeWatched") == "true"

    def calculateProgressSteps(self, period):
        self.logMsg("calculateProgressSteps notification time %s", period, 2)
        part1 = (100.0 / int(period))
        self.logMsg("calculateProgressSteps 100 / notification time %s", part1, 2)
        part2 = (100.0 / int(period))/10
        self.logMsg("calculateProgressSteps (100 / notification time) / 10 %s", part2, 2)
        return (100.0 / int(period))/10

    def autoPlayPlayback(self):
        currentFile = xbmc.Player().getPlayingFile()
        if not self.addon_data:
            # Get the active player
            result = self.getNowPlaying()
            if not self.handle_now_playing_result(result):
                self.logMsg("Error: no result returned from check on now playing...exiting", 1)
                return
            # get the next episode from kodi
            episode = self.handle_kodi_lookup_of_episode(self.tvshowid, currentFile, self.includeWatched)
        else:
            episode = self.handle_addon_lookup_of_next_episode()
            current_episode = self.handle_addon_lookup_of_current_episode()
            self.currentepisodeid = current_episode["episodeid"]
            if self.currenttvshowid != current_episode["tvshowid"]:
                self.currenttvshowid = current_episode["tvshowid"]
                self.playedinarow = 1

        if episode is None:
            # no episode get out of here
            self.logMsg("Error: no episode could be found to play next...exiting", 1)
            return
        self.logMsg("episode details %s", str(episode), 2)
        episodeid = episode["episodeid"]
        noplaycount = episode["playcount"] is None or episode["playcount"] == 0
        includePlaycount = True if self.includeWatched else noplaycount
        if includePlaycount and self.currentepisodeid != episodeid:
            # we have a next up episode choose mode
            if utils.settings("simpleMode") == "0":
                nextUpPage = UpNext("script-upnext-upnext-simple.xml",
                                    utils.addon_path(), "default", "1080i")
                stillWatchingPage = StillWatching(
                    "script-upnext-stillwatching-simple.xml",
                    utils.addon_path(), "default", "1080i")
            else:
                nextUpPage = UpNext("script-upnext-upnext.xml",
                                    utils.addon_path(), "default", "1080i")
                stillWatchingPage = StillWatching(
                    "script-upnext-stillwatching.xml",
                    utils.addon_path(), "default", "1080i")

            playTime = xbmc.Player().getTime()
            totalTime = xbmc.Player().getTotalTime()
            progressStepSize = self.calculateProgressSteps(totalTime - playTime)
            nextUpPage.setItem(episode)
            nextUpPage.setProgressStepSize(progressStepSize)
            stillWatchingPage.setItem(episode)
            stillWatchingPage.setProgressStepSize(progressStepSize)
            playedinarownumber = utils.settings("playedInARow")
            self.logMsg("played in a row settings %s", str(playedinarownumber), 2)
            self.logMsg("played in a row %s", str(self.playedinarow), 2)
            showingnextuppage = False
            showingstillwatchingpage = False
            hideforshortvideos = (self.shortplayNotification == "false") and (self.shortplayLength >= totalTime) and (self.shortplayMode == "true")
            if int(self.playedinarow) <= int(playedinarownumber) and not hideforshortvideos:
                self.logMsg(
                    "showing next up page as played in a row is %s", str(self.playedinarow), 2)
                nextUpPage.show()
                utils.window('service.upnext.dialog', 'true')
                showingnextuppage = True
            elif not hideforshortvideos:
                self.logMsg(
                    "showing still watching page as played in a row %s", str(self.playedinarow), 2)
                stillWatchingPage.show()
                utils.window('service.upnext.dialog', 'true')
                showingstillwatchingpage = True

            while xbmc.Player().isPlaying() and (
                    totalTime - playTime > 1) and not nextUpPage.isCancel() and not nextUpPage.isWatchNow() and not stillWatchingPage.isStillWatching() and not stillWatchingPage.isCancel():
                xbmc.sleep(100)
                try:
                    playTime = xbmc.Player().getTime()
                    totalTime = xbmc.Player().getTotalTime()
                    if showingnextuppage:
                        nextUpPage.updateProgressControl()
                    elif showingstillwatchingpage:
                        stillWatchingPage.updateProgressControl()
                except:
                    pass
            if self.shortplayLength >= totalTime and self.shortplayMode == "true":
                #play short video and don't add to playcount
                self.playedinarow += 0
                self.logMsg("Continuing short video autoplay - %s")
                if nextUpPage.isWatchNow() or stillWatchingPage.isStillWatching():
                    self.playedinarow = 1
                shouldPlayDefault = not nextUpPage.isCancel()
            else:
                if showingnextuppage:
                    nextUpPage.close()
                    utils.window('service.upnext.dialog', clear=True)
                    shouldPlayDefault = not nextUpPage.isCancel()
                    shouldPlayNonDefault = nextUpPage.isWatchNow()
                elif showingstillwatchingpage:
                    stillWatchingPage.close()
                    utils.window('service.upnext.dialog', clear=True)
                    shouldPlayDefault = stillWatchingPage.isStillWatching()
                    shouldPlayNonDefault = stillWatchingPage.isStillWatching()

                if nextUpPage.isWatchNow() or stillWatchingPage.isStillWatching():
                    self.playedinarow = 1
                else:
                    self.playedinarow += 1

            if (shouldPlayDefault and self.playMode == "0") or (shouldPlayNonDefault and self.playMode == "1"):
                self.logMsg("playing media episode id %s", str(episodeid), 2)
                # Signal to trakt previous episode watched
                utils.event("NEXTUPWATCHEDSIGNAL", {'episodeid': self.currentepisodeid})

                # Play media
                if not self.addon_data:
                    xbmc.executeJSONRPC(
                        '{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", '
                        '"params": { "item": {"episodeid": ' + str(episode["episodeid"]) + '} } }')
                else:
                    self.logMsg("sending data to addon to play:  %s ", str(self.addon_data['play_info']), 2)
                    utils.event(self.addon_data['id'], self.addon_data['play_info'], "upnextprovider")
        else:
            self.logMsg("Decided not to show the popup. includeplaycount is %s episodeid is %s currentepisodeid is %s ", str(includePlaycount), str(episodeid), str(self.currentepisodeid), 1)


    def developerPlayPlayback(self):
        episode = utils.loadTestData()
        nextUpPageSimple = UpNext("script-upnext-upnext-simple.xml",
                                  utils.addon_path(), "default", "1080i")
        stillWatchingPageSimple = StillWatching(
            "script-upnext-stillwatching-simple.xml",
            utils.addon_path(), "default", "1080i")
        nextUpPage = UpNext("script-upnext-upnext.xml",
                            utils.addon_path(), "default", "1080i")
        stillWatchingPage = StillWatching(
            "script-upnext-stillwatching.xml",
            utils.addon_path(), "default", "1080i")
        nextUpPage.setItem(episode)
        nextUpPageSimple.setItem(episode)
        stillWatchingPage.setItem(episode)
        stillWatchingPageSimple.setItem(episode)
        notification_time = utils.settings("autoPlaySeasonTime")
        progressStepSize = self.calculateProgressSteps(notification_time)
        self.logMsg("progressStepSize %s", str(progressStepSize), 2)
        nextUpPage.setProgressStepSize(progressStepSize)
        nextUpPageSimple.setProgressStepSize(progressStepSize)
        stillWatchingPage.setProgressStepSize(progressStepSize)
        stillWatchingPageSimple.setProgressStepSize(progressStepSize)
        if utils.settings("windowMode") == "0":
            nextUpPage.show()
        elif utils.settings("windowMode") == "1":
            nextUpPageSimple.show()
        elif utils.settings("windowMode") == "2":
            stillWatchingPage.show()
        elif utils.settings("windowMode") == "3":
            stillWatchingPageSimple.show()
        utils.window('service.upnext.dialog', 'true')

        while xbmc.Player().isPlaying() and not nextUpPage.isCancel() and not nextUpPage.isWatchNow() and not stillWatchingPage.isStillWatching() and not stillWatchingPage.isCancel():
            xbmc.sleep(100)
            nextUpPage.updateProgressControl()
            nextUpPageSimple.updateProgressControl()
            stillWatchingPage.updateProgressControl()
            stillWatchingPageSimple.updateProgressControl()

        if utils.settings("windowMode") == "0":
            nextUpPage.close()
        elif utils.settings("windowMode") == "1":
            nextUpPageSimple.close()
        elif utils.settings("windowMode") == "2":
            stillWatchingPage.close()
        elif utils.settings("windowMode") == "3":
            stillWatchingPageSimple.close()
        utils.window('service.upnext.dialog', clear=True)