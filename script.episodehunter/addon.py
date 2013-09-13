import time
import json

try:
    import simplejson as json
except ImportError:
    import json

from helper import *
from xbmc_helper import *
from connection import Connection
from database import Database


class EHPlayer(xbmc.Player):

    def __init__(self):
        xbmc.Player.__init__(self)
        self.resetVar()                             # Only to get the settings variable
        path = self.settings.getAddonInfo('path')
        self.db = Database(path + "/sqlite.db")
        self.connection = Connection()

    def resetVar(self):
        self.current_video = None       # The current video object
        self.total_time = 0             # Total time of the movie/tv-show
        self.watched_time = 0           # Total watched time
        self.is_playing = False         # Is xbmc playing a video right now? (play)
        self.is_active = False          # True if pause || play
        self.valid_user = True          # Is the settings OK?
        self.movie_IMDB = ''            # IMDB_ID for movies
        self.offline = False            # Is we offline?
        self.scrobbleMovie = True       # Should we scrobble movies?
        self.scrobbleEpisode = True     # Should we scrobble tv-shows?
        self.media = None               # Current media

        # Reload settings
        self.settings = xbmcaddon.Addon("script.episodehunter")
        self.language = self.settings.getLocalizedString
        self.name = "EpisodeHunter"

        offlineOption = self.settings.getSetting("offline")
        scrobbleMovieOption = self.settings.getSetting("scrobble_movie")
        scrobbleEpisodeOption = self.settings.getSetting("scrobble_episode")

        if offlineOption == 'true':
            self.offline = True
        if scrobbleMovieOption == 'false':
            self.scrobbleMovie = False
        if scrobbleEpisodeOption == 'false':
            self.scrobbleEpisode = False

    # This function is only running once (every time when a user starts a movie/tv-show)
    def onPlayBackStarted(self):
        Debug("onPlayBackStarted")
        self.resetVar()                 # Reset all variables
        self.isUserOK(silent=False)     # Check if we have the user-data we need.

        if xbmc.Player().isPlayingVideo():                                          # Do we actually play a video
            playerID = getActivePlayersFromXBMC()
            self.current_video = getCurrentlyplayFromXBMC(playerID)
            if self.current_video is not None:
                if 'type' in self.current_video and 'id' in self.current_video:

                    if not xbmc.Player().isPlayingVideo():
                        Debug("What? Not playing anymore")
                        return None

                    if self.current_video['type'] == 'movie':                       # If it's a movie; try to find IMDB id
                        #self.movie_IMDB = xbmc.Player().getVideoInfoTag().getIMDBNumber()
                        self.media = getMovieDetailsFromXbmc(self.current_video['id'], ['year', 'imdbnumber', 'originaltitle'])

                    elif self.current_video['type'] == 'episode':
                        match = getEpisodeDetailsFromXbmc(self.current_video['id'], ['tvshowid', 'showtitle', 'season', 'episode'])
                        if match is None:
                            Debug("onPlayBackStarted: Did not find current episode")
                            return
                        self.media = match
                        show_match = getShowDetailsFromXbmc(match['tvshowid'], ['imdbnumber', 'year'])
                        if show_match is None:
                            Debug("onPlayBackStarted: Did not find imdbnumber")
                        self.media['imdbnumber'] = show_match['imdbnumber']
                        self.media['year'] = show_match['year']

                    self.total_time = xbmc.Player().getTotalTime()                  # Get total time of media
                    self.is_playing = True                                          # Yes, we are playing media
                    self.is_active = True                                           # Yes, the media is in focus
                    Debug("self.total_time: " + str(self.total_time))
            else:
                self.resetVar()

    def onPlayBackEnded(self):
        Debug("onPlayBackEnded")
        self.onPlayBackStopped()    # Playback end, playback stop.. Big difference.. NOT..

    def onPlayBackStopped(self):
        Debug("onPlayBackStopped")
        if self.is_active:
            Debug("onPlayBackStopped Stopped after: " + str(self.watched_time))
            if self.current_video is None:  # If the current_video is None, something is wrong
                self.resetVar()
                return None

            if 'type' in self.current_video and 'id' in self.current_video:
                self.scrobble()

            self.resetVar()

    def onPlayBackPaused(self):
        Debug("onPlayBackPaused")
        if self.is_active and self.is_playing:      # Are we realy playing?
            self.is_playing = False                 # Okay, then, lets pause
            self.updateWatched_time()               # Udate the playing time
            if self.watched_time > 0:
                Debug("onPlayBackPaused Paused after: " + str(self.watched_time))

    def onPlayBackResumed(self):
        Debug("onPlayBackResumed")
        self.isUserOK(silent=True)                  # Have the user update his user setting while pausing?
        if self.is_active:
            Debug("onPlayBackResumed self.watched_time: " + str(self.watched_time))
            self.is_playing = True

    def updateWatched_time(self):
        self.watched_time = to_seconds(str(xbmc.getInfoLabel("Player.Time")))

    def watching(self):
        Debug("watching, is_playing: " + str(self.is_playing))
        if self.is_playing and self.media is not None:

            self.updateWatched_time()

            responce = None

            if self.current_video['type'] == 'movie' and self.scrobbleMovie and self.valid_user and not self.offline:
                try:
                    responce = self.connection.watchingMovie(
                        self.media['originaltitle'],
                        self.media['year'],
                        self.media['imdbnumber'],
                        self.total_time / 60,
                        int(100 * self.watched_time / self.total_time))
                except Exception:
                    Debug("watching: Error movie transmit")

            elif self.current_video['type'] == 'episode' and self.scrobbleEpisode and self.valid_user and not self.offline:
                try:
                    responce = self.connection.watchingEpisode(
                        self.media['imdbnumber'],
                        self.media['showtitle'],
                        self.media['year'],
                        self.media['season'],
                        self.media['episode'],
                        self.total_time / 60,
                        int(100 * self.watched_time / self.total_time))
                except Exception:
                    Debug("watching: Error episode transmit")

            if responce is not None:
                Debug("watching: Watch responce: " + str(responce))
                if 'status' in responce:
                    if responce['status'] == 403:
                        self.valid_user = False
                    if responce['status'] != 200:
                        # If the user settings are wrong, this message is only shown when a user start playing media
                        notification(self.name, self.language(32018) + ": " + str(responce['data']))  # 'Error:'
            else:
                Debug("watching: responce is None :(")

    def stoppedWatching(self):
        Debug("stoppedWatching")

        responce = None

        if self.current_video['type'] == 'movie' and self.scrobbleMovie and self.valid_user and not self.offline:
            responce = self.connection.cancelWatchingMovie()
        elif self.current_video['type'] == 'episode' and self.scrobbleEpisode and self.valid_user and not self.offline:
            responce = self.connection.cancelWatchingEpisode()

        if responce is not None:
            Debug("stoppedWatching Cancel watch responce: " + str(responce))
        else:
            Debug("watching: responce is None :(")

    def scrobble(self):
        Debug("scrobble")

        scrobbleMinViewTimeOption = self.settings.getSetting("scrobble_min_view_time")
        Debug("Scrobble self.watched_time: " + str(self.watched_time) + " self.total_time: " + str(self.total_time))

        if (self.watched_time / self.total_time) * 100 >= float(scrobbleMinViewTimeOption):

            responce = None

            if self.current_video['type'] == 'movie' and self.scrobbleMovie:
                try:
                    arg = {}
                    arg['method'] = 'scrobbleMovie'
                    arg['parameter'] = {'originaltitle': self.media['originaltitle'],
                                        'year': self.media['year'],
                                        'imdb_id': self.media['imdbnumber'],
                                        'duration': self.total_time / 60,
                                        'percent': int(100 * self.watched_time / self.total_time),
                                        'time': int(time.time())}

                    if self.offline or not self.valid_user:
                        self.db.write(arg)
                        return None

                    responce = self.connection.scrobbleMovie(**arg['parameter'])

                except Exception:
                    Debug("scrobble: Something went wrong (movie)")

            elif self.current_video['type'] == 'episode' and self.scrobbleEpisode:
                try:
                    arg = {}
                    arg['method'] = 'scrobbleEpisode'
                    arg['parameter'] = {'tvdb_id': self.media['imdbnumber'],
                                        'title': self.media['showtitle'],
                                        'year': self.media['year'],
                                        'season': self.media['season'],
                                        'episode': self.media['episode'],
                                        'duration': self.total_time / 60,
                                        'percent': int(100 * self.watched_time / self.total_time),
                                        'time': int(time.time())}

                    if self.offline or not self.valid_user:
                        self.db.write(arg)
                        return None

                    responce = self.connection.scrobbleEpisode(**arg['parameter'])

                except Exception:
                    Debug("scrobble: Something went wrong (episode)")

            if responce is None or ('status' in responce and responce['status'] != 200):
                self.db.write(arg)
                return None
            else:
                Debug("Scrobble responce: " + str(responce))

        elif not self.offline and self.valid_user:
            self.stoppedWatching()

    def checkForOldData(self):
        Debug("checkForOldData")

        success = {}

        if not self.offline:
            rows = self.db.getAll()

            if rows is None or not rows:
                Debug("checkForOldData: No rows")
                return None

            try:
                for row in rows:

                    try:
                        data = json.loads(row[1])
                    except Exception:
                        Debug("checkForOldData: unable to convert string to json: " + str(row[1]))
                        continue

                    try:
                        Debug('Make the call')
                        responce = getattr(self.connection, data['method'])(**data['parameter'])
                        if responce is None or ('status' in responce and responce['status'] != 200):
                            Debug("checkForOldData: Unable to get responce. m: " + str(data['method']) + " p: " + str(data['parameter']))
                            break
                        else:
                            Debug("success")
                            success[row[0]] = 1
                    except Exception:
                        Debug("Unable to call funcation: " + str(data))

            except Exception:
                Debug("checkForOldData: Unable to loop")
                print(traceback.format_exc())

            success = success.keys()
            if len(success) > 0:
                Debug("Remove id: " + str(success))
                self.db.removeRows(success)

    def isUserOK(self, silent):
        if not isSettingsOkey(daemon=True, silent=silent):  # Check if we have the user-data we need.
            self.valid_user = False
        else:
            self.valid_user = True

player = EHPlayer()


player.checkForOldData()
Debug("OK, lets do this")
i = 0
while(not xbmc.abortRequested):
    xbmc.sleep(1000)
    if player.is_playing:
        i += 1
        if i >= 300:
            player.watching()
            i = 0

Debug("The END")
