"""
Connection class
Makes all HTTP request to episodehunter.tv
"""

import time
import socket
import json
import xbmc
import xbmcaddon
from httpconn import HTTPConn
import helper


class Connection(object):
    """ Makes all HTTP request to episodehunter.tv """

    def __init__(self):
        self.__settings = xbmcaddon.Addon("script.episodehunter")
        self.__language = self.__settings.getLocalizedString
        self.__name = "EpisodeHunter"
        self.__url = "api.episodehunter.tv"
        self.__connection = None

    def _make_connection(self):
        """ Establish a connection """
        try:
            self.__connection = HTTPConn(self.__url, 80)
        except socket.timeout:
            helper.debug("makeConnection: timeout")
            # Connection timeout
            helper.notification(self.__name, self.__language(32038), 1)
            self.__connection = None

    def make_request(self, request, args={}):
        """ Send message """

        # Must have username as wall as apikey
        if self.__settings.getSetting("username") == "" or self.__settings.getSetting("api_key") == "":
            return None

        # Create an connection
        self._make_connection()
        if self.__connection is None:
            helper.debug("Unable to connect")
            return None

        try:
            args['username'] = self.__settings.getSetting("username")
            args['apikey'] = self.__settings.getSetting("api_key")

            jdata = json.dumps(args)
        except Exception:
            return None

        # Create the request
        try:
            self.__connection.request(request, jdata)
        except socket.error:
            helper.debug("make_request: Socket error, unable to connect")
            # 'Socket error, unable to connect'
            helper.notification(self.__name, self.__language(32045), 1)
            return None

        # And off we go
        try:
            self.__connection.get_response()
        except Exception:
            helper.debug("make_request: Unable to send data")
            # 'Unable to send data'
            helper.notification(self.__name, self.__language(32041), 1)
            return None

        # Wait for the respond, timeout after 15s
        i = 0
        while True:
            if self.__connection.has_result() or xbmc.abortRequested:
                if xbmc.abortRequested:
                    helper.debug("make_request: Dude? Can't get respond if you break the loop")
                    return None
                break

            time.sleep(1)
            i += 1
            if i >= 15:
                helper.debug("make_request: Connection timeout")
                # Connection timeout
                helper.notification(self.__name, self.__language(32038), 1)
                return None

        # Ladies and gentlemen, we have a result
        try:
            response = self.__connection.get_result()
            raw = response.read()
        except Exception:
            helper.debug("Unable to read responce")
            # Unable to read response
            helper.notification(self.__name, self.__language(32042), 1)
            return None
        finally:
            try:
                # The average time for every request is five minutes
                # so we might as well close the connection. (Apache has the connection open for about 3 minutes)
                self.__connection.close()
            except Exception:
                pass

        try:
            data = json.loads(raw)
        except ValueError:
            helper.debug("make_request: Bad JSON responce: " + raw)
            # Bad JSON response from episodehunter.tv
            helper.notification(self.__name, self.__language(32039), 1)
            return None

        return data

    def set_movies_watched(self, movies_seen=[]):
        """ Set a movie as watched """
        return self.make_request('/v2/movie/watched', {'movies': movies_seen})

    def set_shows_watched(self, tvdb_id, title, year, episodes):
        """ Set a several episodes for a TV show as watched """
        return self.make_request('/v2/tv/watched', {'tvdb_id': tvdb_id, 'title': title, 'year': year, 'episodes': episodes})

    def get_watched_movies(self):
        """ Get watched movies from episodehunter.tv """
        responce = self.make_request('/v2/movie/getwatched')
        if responce is None:
            return None
        elif 'status' in responce and 'data' in responce:
            if responce['status'] != 200:
                helper.debug("get_watched_movies: Error: " + str(responce['data']))
                helper.notification(self.__name, self.__language(32018) + ": " + str(responce['data']))  # 'Error'
                return None

        if 'value' in responce:
            return responce['value']

        return None

    def get_watched_shows(self):
        """ Get watched TV shows from episodehunter.tv """
        responce = self.make_request('/v2/tv/getwatched')
        if responce is None:
            return None
        elif 'status' in responce and 'data' in responce:
            if responce['status'] != 200:
                helper.debug("get_watched_shows: Error: " + str(responce['data']))
                helper.notification(self.__name, self.__language(32018) + ": " + str(responce['data']))  # 'Error'
                return None

        if 'value' in responce:
            return responce['value']

        return None

    def watching_movie(self, originaltitle, year, imdb_id, duration, percent):
        """ Set a movie as watching on episodehunter.tv """
        return self.make_request('/v2/movie/watching', {'originaltitle': originaltitle, 'year': year, 'imdb_id': imdb_id, 'duration': duration, 'progress': percent})

    def watching_episode(self, tvdb_id, title, year, season, episode, duration, percent):
        """ Set a episode as watching on episodehunter.tv """
        return self.make_request('/v2/tv/watching', {'tvdb_id': tvdb_id, 'title': title, 'year': year, 'season': season, 'episode': episode, 'duration': duration, 'progress': percent})

    def cancel_watching_movie(self):
        """ Cancel watching a movie"""
        return self.make_request('/v2/movie/cancelwatching', {})

    def cancel_watching_episode(self):
        """ Cancel watching an episode """
        return self.make_request('/v2/tv/cancelwatching', {})

    def scrobble_movie(self, originaltitle, year, imdb_id, duration, percent, timestamp=0):
        """ Scrobble a movie to episodehunter.tv """
        return self.make_request('/v2/movie/scrobble', {'originaltitle': originaltitle, 'year': year, 'imdb_id': imdb_id, 'duration': duration, 'progress': percent, 'time': timestamp})

    def scrobble_episode(self, tvdb_id, title, year, season, episode, duration, percent, timestamp=0):
        """ Scrobble en episode to episodehunter.tv """
        return self.make_request('/v2/tv/scrobble', {'tvdb_id': tvdb_id, 'title': title, 'year': year, 'season': season, 'episode': episode, 'duration': duration, 'progress': percent, 'time': timestamp})
