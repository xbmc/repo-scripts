import time
import json
import xbmc
from resources.exceptions import SettingsExceptions, ConnectionExceptions
from resources.lib import helper
from resources.lib import xbmc_repository
from resources.lib import user
from resources.lib.gui import dialog
from resources.lib.database import Database
from resources.lib.connection.connection import Connection
from resources.lib.connection.http import Http
from resources import config


def is_movie(media):
    return 'type' in media and media['type'] == 'movie'


def is_episode(media):
    return 'type' in media and media['type'] == 'episode'


def is_media(media):
    return media is not None and 'type' in media and 'id' in media


class EHPlayer(xbmc.Player):

    is_playing = False           # Is XBMC playing a video right now?
    __current_video = None       # The current video object
    __total_time = 0             # Total time of the movie/TV-show
    __watched_time = 0           # Total watched time
    __is_active = False          # True if pause || playing
    __valid_user = True          # Is the settings OK?
    __offline = False            # Are we offline?
    __media = None               # Current media
    __db = None                  # Database object
    __connection = None          # Connection object

    def __init__(self):
        xbmc.Player.__init__(self)
        db_path = helper.get_addon_resource_path('/offline.db')
        self.__db = Database(db_path)
        self.__connection = Connection(Http(config.__BASE_URL__))

    def reset_var(self):
        """ Reset all values to there defaults """
        self.is_playing = False
        self.__current_video = None
        self.__total_time = 0
        self.__watched_time = 0
        self.__is_active = False
        self.__valid_user = True
        self.__offline = False
        self.__media = None

    def run(self):
        self.sync_offline_data()
        monitor = xbmc.Monitor()

        while not monitor.abortRequested():
            if monitor.waitForAbort(300):
                break
            if self.is_playing:
                self.watching()

    def onPlayBackStarted(self):
        """
        Will be called when xbmc starts playing a file.
        """
        helper.debug("onPlayBackStarted")
        self.reset_var()
        self.check_user()  # Check if we have the user-data we need

        # Do we actually play a video
        if xbmc.Player().isPlayingVideo():
            player_id = xbmc_repository.active_player()
            self.__current_video = xbmc_repository.currently_playing(player_id)
            if is_media(self.__current_video):
                if not xbmc.Player().isPlayingVideo():
                    return None

                if is_movie(self.__current_video):
                    self.__media = xbmc_repository.movie_details(self.__current_video['id'])

                elif is_episode(self.__current_video):
                    self.__media = xbmc_repository.get_episode_details(self.__current_video['id'])
                    if self.__media is None:
                        # Did not find current episode
                        return

                    series_match = xbmc_repository.get_show_details(self.__media['tvshowid'])
                    self.__media['imdbnumber'] = series_match['imdbnumber']
                    self.__media['year'] = series_match['year']

                self.__total_time = xbmc.Player().getTotalTime()
                self.is_playing = True
                self.__is_active = True
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
            if not is_media(self.__current_video):
                self.reset_var()
                return None
            self.scrobble()
            self.reset_var()

    def onPlayBackPaused(self):
        """ On pause """
        helper.debug("onPlayBackPaused")
        if self.__is_active and self.is_playing:  # Are we really playing?
            self.is_playing = False               # Okay then, lets pause
            self.update_watched_time()            # Update the playing time

    def onPlayBackResumed(self):
        """ On resumed """
        helper.debug("onPlayBackResumed")
        # Have the user update his user setting while pausing?
        self.check_user()
        if self.__is_active:
            self.is_playing = True

    def update_watched_time(self):
        """ Update the time a user has watch an episode/move """
        self.__watched_time = helper.xbmc_time_to_seconds(str(xbmc.getInfoLabel("Player.Time")))

    def watching(self):
        """ This functions is called continuously, see below """
        helper.debug("watching, is_playing: " + str(self.is_playing))
        if self.is_playing and self.__media is not None:

            self.update_watched_time()

            if not self.__valid_user or self.__offline:
                return None

            if is_movie(self.__current_video) and user.scrobble_movies():
                self.communicate_with_eh(
                    self.__connection.watching_movie,
                    originaltitle=self.__media['originaltitle'],
                    year=self.__media['year'],
                    imdb_id=self.__media['imdbnumber'],
                    duration=self.__total_time / 60,
                    percent=int(100 * self.__watched_time / self.__total_time)
                )
            elif is_episode(self.__current_video) and user.scrobble_episodes():
                self.communicate_with_eh(
                    self.__connection.watching_episode,
                    tvdb_id=self.__media['imdbnumber'],
                    title=self.__media['showtitle'],
                    year=self.__media['year'],
                    season=self.__media['season'],
                    episode=self.__media['episode'],
                    duration=self.__total_time / 60,
                    percent=int(100 * self.__watched_time / self.__total_time)
                )

    def stop_watching(self):
        """ Tell episodehunter.tv that we have stop watching """
        helper.debug("stoppedWatching")

        if self.__valid_user and not self.__offline:
            if is_movie(self.__current_video) and user.scrobble_movies():
                self.communicate_with_eh(self.__connection.cancel_watching_movie)
            elif is_episode(self.__current_video) and user.scrobble_episodes():
                self.communicate_with_eh(self.__connection.cancel_watching_episode)

    def scrobble(self):
        """ Scrobble a movie / episode """
        helper.debug("scrobble")

        scrobble_min_view_time_option = user.scrobble_min_view_time()

        if (self.__watched_time / self.__total_time) * 100 >= float(scrobble_min_view_time_option):
            if is_movie(self.__current_video) and user.scrobble_movies():
                self.communicate_with_eh(
                    self.__connection.scrobble_movie,
                    originaltitle=self.__media['originaltitle'],
                    year=self.__media['year'],
                    imdb_id=self.__media['imdbnumber'],
                    duration=self.__total_time / 60,
                    percent=int(100 * self.__watched_time / self.__total_time),
                    timestamp=int(time.time())
                )
            elif is_episode(self.__current_video) and user.scrobble_episodes():
                self.communicate_with_eh(
                    self.__connection.scrobble_episode,
                    tvdb_id=self.__media['imdbnumber'],
                    title=self.__media['showtitle'],
                    year=self.__media['year'],
                    season=self.__media['season'],
                    episode=self.__media['episode'],
                    duration=self.__total_time / 60,
                    percent=int(100 * self.__watched_time / self.__total_time),
                    timestamp=int(time.time())
                )
        else:
            self.stop_watching()

    def communicate_with_eh(self, method, *args, **kargs):
        if self.__offline:
            self.save_method_call_in_db(method, **kargs)
            return

        try:
            method(*args, **kargs)
        except SettingsExceptions as error:
            self.__valid_user = False
            dialog.create_notification(error.value)
        except ConnectionExceptions as error:
            self.__offline = True
            dialog.create_notification(error.value)
            self.save_method_call_in_db(method, **kargs)

    def save_method_call_in_db(self, method, **kargs):
        methods_to_save = ['scrobble_movie', 'scrobble_episode']
        if method.__name__ in methods_to_save:
            self.__db.write({
                'method': method.__name__,
                'parameter': kargs
            })

    def sync_offline_data(self):
        """ Check the database for old offline data """
        helper.debug("sync_offline_data")

        if user.offline():
            return

        success = []
        rows = self.__db.get_all()

        if rows is None or not rows:
            return None

        for row in rows:
            data = json.loads(row[1])

            try:
                getattr(self.__connection, data['method'])(**data['parameter'])
            except SettingsExceptions as error:
                self.__valid_user = False
                dialog.create_notification(error.value)
                break
            except ConnectionExceptions:
                success.append(row[0])

        if len(success) > 0:
            self.__db.remove_rows(success)

    def check_user(self):
        """ Check if we have all the user-settings that we need """
        if not helper.is_settings_okey(daemon=True, silent=False):
            self.__valid_user = False
        else:
            self.__valid_user = True
