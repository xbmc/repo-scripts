"""
Background process
"""

import time
import json
import xbmc
import xbmcaddon
from resources.lib import helper
from resources.lib import xbmc_helper
from resources.lib.database import Database
from resources.lib.connection import Connection


class EHPlayer(xbmc.Player):

    is_playing = False           # Is XBMC playing a video right now?
    __current_video = None       # The current video object
    __total_time = 0             # Total time of the movie/TV-show
    __watched_time = 0           # Total watched time
    __is_active = False          # True if pause || playing
    __valid_user = True          # Is the settings OK?
    __offline = False            # Are we offline?
    __scrobble_movie = True      # Should we scrobble movies?
    __scrobble_episode = True    # Should we scrobble TV-shows?
    __media = None               # Current media
    __db = None                  # Database object
    __connection = None          # Connection object
    __settings = None            # User settings object
    __language = None
    __name = "EpisodeHunter"

    def __init__(self):
        xbmc.Player.__init__(self)
        self.reset_var() # Only to get the settings variable
        db_path = xbmc.translatePath(self.__settings.getAddonInfo('profile') + "/offline.db")
        self.__db = Database(db_path)
        self.__connection = Connection()

    def reset_var(self):
        """ Reset all values to there default """
        self.is_playing = False
        self.__current_video = None
        self.__total_time = 0
        self.__watched_time = 0
        self.__is_active = False
        self.__valid_user = True
        self.__offline = False
        self.__scrobble_movie = True
        self.__scrobble_episode = True
        self.__media = None

        # Reload settings
        self.__settings = xbmcaddon.Addon("script.episodehunter")
        self.__language = self.__settings.getLocalizedString

        offline_option = self.__settings.getSetting("offline")
        scrobble_movie_option = self.__settings.getSetting("scrobble_movie")
        scrobble_episode_option = self.__settings.getSetting("scrobble_episode")

        if offline_option == 'true':
            self.__offline = True
        if scrobble_movie_option == 'false':
            self.__scrobble_movie = False
        if scrobble_episode_option == 'false':
            self.__scrobble_episode = False

    def onPlayBackStarted(self):
        """
        This function is only running once
        (every time when a user starts a movie/TV-show)
        """
        helper.debug("onPlayBackStarted")
        self.reset_var()              # Reset all variables
        self.check_user(silent=False) # Check if we have the user-data we need

        # Do we actually play a video
        if xbmc.Player().isPlayingVideo():
            player_id = xbmc_helper.get_active_players_from_xbmc()
            self.__current_video = xbmc_helper.get_currently_playing_from_xbmc(player_id)
            if self.__current_video is not None:
                if 'type' in self.__current_video and 'id' in self.__current_video:

                    if not xbmc.Player().isPlayingVideo():
                        helper.debug("What? Not playing anymore")
                        return None

                    # If it's a movie; try to find IMDB id
                    if self.__current_video['type'] == 'movie':
                        # self.movie_IMDB = xbmc.xbmc.Player().getVideoInfoTag().getIMDBNumber()
                        self.__media = xbmc_helper.get_movie_details_from_xbmc(self.__current_video['id'], ['year', 'imdbnumber', 'originaltitle'])

                    elif self.__current_video['type'] == 'episode':
                        match = xbmc_helper.get_episode_details_from_xbmc(self.__current_video['id'], ['tvshowid', 'showtitle', 'season', 'episode'])
                        if match is None:
                            # Did not find current episode
                            return
                        self.__media = match
                        show_match = xbmc_helper.get_show_details_from_xbmc(match['tvshowid'], ['imdbnumber', 'year'])
                        self.__media['imdbnumber'] = show_match['imdbnumber']
                        self.__media['year'] = show_match['year']

                    self.__total_time = xbmc.Player().getTotalTime() # Get total time of media
                    self.is_playing = True                           # Yes, we are playing media
                    self.__is_active = True                          # Yes, the media is in focus
            else:
                self.reset_var()

    def onPlayBackEnded(self):
        """ Called when the playback is ending """
        helper.debug("onPlayBackEnded")
        self.__watched_time = self.__total_time
        self.onPlayBackStopped()

    def onPlayBackStopped(self):
        """ Called when the user stops the playback """
        helper.debug("onPlayBackStopped")
        if self.__is_active:
            helper.debug("onPlayBackStopped Stopped after: " + str(self.__watched_time))
            if self.__current_video is None:  # If the current_video is None, something is wrong
                self.reset_var()
                return None

            if 'type' in self.__current_video and 'id' in self.__current_video:
                self.scrobble()

            self.reset_var()

    def onPlayBackPaused(self):
        """ On pause """
        helper.debug("onPlayBackPaused")
        if self.__is_active and self.is_playing: # Are we really playing?
            self.is_playing = False              # Okay then, lets pause
            self.update_watched_time()           # Update the playing time

    def onPlayBackResumed(self):
        """ On resumed """
        helper.debug("onPlayBackResumed")
        # Have the user update his user setting while pausing?
        self.check_user(silent=True)
        if self.__is_active:
            self.is_playing = True

    def update_watched_time(self):
        """ Update the time a user has watch an episode/move """
        self.__watched_time = helper.to_seconds(str(xbmc.getInfoLabel("Player.Time")))

    def watching(self):
        """ This functions is called continuously, see below """
        helper.debug("watching, is_playing: " + str(self.is_playing))
        if self.is_playing and self.__media is not None:

            self.update_watched_time()

            responce = None

            if self.__current_video['type'] == 'movie' and self.__scrobble_movie and self.__valid_user and not self.__offline:
                try:
                    responce = self.__connection.watching_movie(
                        self.__media['originaltitle'],
                        self.__media['year'],
                        self.__media['imdbnumber'],
                        self.__total_time / 60,
                        int(100 * self.__watched_time / self.__total_time))
                except Exception:
                    helper.debug("watching: Error movie transmit")

            elif self.__current_video['type'] == 'episode' and self.__scrobble_episode and self.__valid_user and not self.__offline:
                try:
                    responce = self.__connection.watching_episode(
                        self.__media['imdbnumber'],
                        self.__media['showtitle'],
                        self.__media['year'],
                        self.__media['season'],
                        self.__media['episode'],
                        self.__total_time / 60,
                        int(100 * self.__watched_time / self.__total_time))
                except Exception:
                    helper.debug("watching: Error episode transmit")

            if responce is not None:
                helper.debug("watching: Watch response: " + str(responce))
                if 'status' in responce:
                    if responce['status'] == 403:
                        self.__valid_user = False
                    if responce['status'] != 200:
                        # If the user settings are wrong, this message is only shown when a user start playing media
                        helper.notification(self.__name, self.__language(32018) + ": " + str(responce['data']))  # 'Error:'
            else:
                helper.debug("watching: responce is None :(")

    def stop_watching(self):
        """ Tell episodehunter.tv that we have stop watching """
        helper.debug("stoppedWatching")

        if self.__valid_user and not self.__offline:
            if self.__current_video['type'] == 'movie' and self.__scrobble_movie:
                self.__connection.cancel_watching_movie()
            elif self.__current_video['type'] == 'episode' and self.__scrobble_episode:
                self.__connection.cancel_watching_episode()

    def scrobble(self):
        """ Scrobble a movie / episode """
        helper.debug("scrobble")

        scrobble_min_view_time_option = self.__settings.getSetting("scrobble_min_view_time")

        if (self.__watched_time / self.__total_time) * 100 >= float(scrobble_min_view_time_option):
            responce = None
            if self.__current_video['type'] == 'movie' and self.__scrobble_movie:
                try:
                    arg = {}
                    arg['method'] = 'scrobble_movie'
                    arg['parameter'] = {'originaltitle': self.__media['originaltitle'],
                                        'year': self.__media['year'],
                                        'imdb_id': self.__media['imdbnumber'],
                                        'duration': self.__total_time / 60,
                                        'percent': int(100 * self.__watched_time / self.__total_time),
                                        'timestamp': int(time.time())}

                    if self.__offline or not self.__valid_user:
                        self.__db.write(arg)
                        return None

                    responce = self.__connection.scrobble_movie(**arg['parameter'])

                except Exception:
                    helper.debug("scrobble: Something went wrong (movie)")

            elif self.__current_video['type'] == 'episode' and self.__scrobble_episode:
                try:
                    arg = {}
                    arg['method'] = 'scrobble_episode'
                    arg['parameter'] = {'tvdb_id': self.__media['imdbnumber'],
                                        'title': self.__media['showtitle'],
                                        'year': self.__media['year'],
                                        'season': self.__media['season'],
                                        'episode': self.__media['episode'],
                                        'duration': self.__total_time / 60,
                                        'percent': int(100 * self.__watched_time / self.__total_time),
                                        'timestamp': int(time.time())}

                    if self.__offline or not self.__valid_user:
                        self.__db.write(arg)
                        return None

                    responce = self.__connection.scrobble_episode(**arg['parameter'])

                except Exception, e:
                    print e
                    helper.debug("scrobble: Something went wrong (episode)")

            if responce is None or ('status' in responce and responce['status'] != 200):
                self.__db.write(arg)
                return None
            else:
                helper.debug("Scrobble responce: " + str(responce))

        else:
            self.stop_watching()

    def check_for_old_data(self):
        """ Check the database for old offline data """
        helper.debug("check_for_old_data")

        success = []

        if not self.__offline:
            rows = self.__db.get_all()

            if rows is None or not rows:
                helper.debug("check_for_old_data: No rows")
                return None

            try:
                for row in rows:
                    try:
                        data = json.loads(row[1])
                    except Exception:
                        helper.debug("check_for_old_data: unable to convert string to json: " + str(row[1]))
                        continue

                    try:
                        helper.debug('Make the call')
                        responce = getattr(self.__connection, data['method'])(**data['parameter'])
                        if responce is None or ('status' in responce and responce['status'] != 200):
                            helper.debug("check_for_old_data: Unable to get responce. m: " + str(data['method']) + " p: " + str(data['parameter']))
                            break
                        else:
                            success.append(row[0])
                    except Exception:
                        helper.debug("Unable to call function: " + str(data))
                        success.append(row[0])

            except Exception:
                helper.debug("check_for_old_data: Unable to loop")

            if len(success) > 0:
                helper.debug("Remove id: " + str(success))
                self.__db.remove_rows(success)

    def check_user(self, silent):
        """ Check if the user settings is correct """
        # Check if we have the user-data we need.
        if not helper.is_settings_okey(daemon=True, silent=silent):
            self.__valid_user = False
        else:
            self.__valid_user = True


player = EHPlayer()

player.check_for_old_data()
i = 0
while not xbmc.abortRequested:
    xbmc.sleep(1000)
    if player.is_playing:
        i += 1
        if i >= 300:
            player.watching()
            i = 0
