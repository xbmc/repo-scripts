import time
import xbmc
from resources.lib import helper
from resources.lib import xbmc_repository
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
    __media = None               # Current media
    __connection = None          # Connection object

    def __init__(self):
        xbmc.Player.__init__(self)
        self.__connection = Connection(Http(config.__BASE_URL__))

    def reset_var(self):
        """ Reset all values to there defaults """
        self.is_playing = False
        self.__current_video = None
        self.__total_time = 0
        self.__watched_time = 0
        self.__is_active = False
        self.__media = None

    def run(self):
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

        # Do we actually play a video
        if xbmc.Player().isPlayingVideo():
            player_id = xbmc_repository.active_player()
            self.__current_video = xbmc_repository.currently_playing(player_id)
            if is_media(self.__current_video):
                if not xbmc.Player().isPlayingVideo():
                    return None

                if is_movie(self.__current_video):
                    self.__media = xbmc_repository.movie_details(
                        self.__current_video['id'])

                elif is_episode(self.__current_video):
                    self.__media = xbmc_repository.get_episode_details(
                        self.__current_video['id'])
                    if self.__media is None:
                        # Did not find current episode
                        return None

                    series_match = xbmc_repository.get_show_details(
                        self.__media['tvshowid'])
                    self.__media['imdbnumber'] = series_match['imdbnumber']
                    self.__media['year'] = series_match['year']

                self.__total_time = xbmc.Player().getTotalTime()
                self.is_playing = True
                self.__is_active = True
                self.send_request('start')
            else:
                self.reset_var()
        return None

    def onPlayBackEnded(self):
        """ Called when the playback is ending """
        helper.debug("onPlayBackEnded")
        self.__watched_time = self.__total_time
        self.onPlayBackStopped()

    def onPlayBackStopped(self):
        """ Called when the user stops the playback """
        helper.debug("onPlayBackStopped")
        if self.__is_active:
            helper.debug("onPlayBackStopped Stopped after: " +
                         str(self.__watched_time))
            if is_media(self.__current_video):
                self.scrobble()
        self.reset_var()

    def onPlayBackPaused(self):
        """ On pause """
        helper.debug("onPlayBackPaused")
        if self.__is_active and self.is_playing:
            self.is_playing = False
            self.update_watched_time()

    def onPlayBackResumed(self):
        """ On resumed """
        helper.debug("onPlayBackResumed")
        if self.__is_active:
            self.is_playing = True

    def update_watched_time(self):
        """ Update the time a user has watch an episode/move """
        self.__watched_time = helper.xbmc_time_to_seconds(
            str(xbmc.getInfoLabel("Player.Time")))

    def watching(self):
        """ This functions is called continuously, see below """
        helper.debug("watching, is_playing: " + str(self.is_playing))
        if self.is_playing and self.__media is not None:
            self.update_watched_time()

    def scrobble(self):
        """ Scrobble a movie / episode """
        helper.debug("scrobble")
        scrobble_min_view_time_option = helper.scrobble_min_view_time()

        if (self.__watched_time / self.__total_time) * 100 >= float(scrobble_min_view_time_option):
            self.send_request('scrobble')
        else:
            self.send_request('stop')

    def send_request(self, event_type):
        helper.debug("send_request")
        if not helper.valid_user_credentials():
            helper.debug("Not valid user credentials")
            return None

        if is_movie(self.__current_video) and helper.scrobble_movies():
            args_dict = self.create_movie_object()
            if event_type == "start":
                self.__connection.start_watching_movie(**args_dict)
            elif event_type == "stop":
                self.__connection.cancel_watching_movie(**args_dict)
            elif event_type == "scrobble":
                self.__connection.scrobble_movie(**args_dict)
        elif is_episode(self.__current_video) and helper.scrobble_episodes():
            args_dict = self.create_episode_object()
            if event_type == "start":
                self.__connection.start_watching_episode(**args_dict)
            elif event_type == "stop":
                self.__connection.cancel_watching_episode(**args_dict)
            elif event_type == "scrobble":
                self.__connection.scrobble_episode(**args_dict)
        else:
            helper.debug("Not a valid episode or movie")
        return None

    def create_episode_object(self):
        return {
            'tvdb_id': self.__media['imdbnumber'],
            'title': self.__media['showtitle'],
            'year': self.__media['year'],
            'season': self.__media['season'],
            'episode': self.__media['episode'],
            'duration': self.__total_time / 60,
            'percent': int(100 * self.__watched_time / self.__total_time),
            'timestamp': int(time.time())
        }

    def create_movie_object(self):
        return {
            'original_title': self.__media['originaltitle'],
            'year': self.__media['year'],
            'themoviedb_id': self.__media['imdbnumber'],
            'duration': self.__total_time / 60,
            'percent': int(100 * self.__watched_time / self.__total_time),
            'timestamp': int(time.time())
        }
