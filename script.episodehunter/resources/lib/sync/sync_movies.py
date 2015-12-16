from resources.lib.sync import Sync
from resources.lib import helper
from resources.lib.gui import dialog
from resources.lib import xbmc_repository
from resources.factory.movie_factory import movie_factory
from resources.exceptions import ConnectionExceptions, UserAbortExceptions, SettingsExceptions


class Movies(Sync):
    """
    Sync class
    Two-way sync between xbmc and EH
    """

    def __init__(self, connection, xbmc=xbmc_repository):
        super(Movies, self).__init__(connection)
        self.eh_watched_movies = None
        self.total_sync_movies = 0
        self.xbmc = xbmc

    def sync(self):
        helper.debug("Start syncing movies")
        self.create_progress(helper.language(32051))  # "Comparing XBMC database with episodehunter.tv"
        try:
            self._sync()
        except UserAbortExceptions:
            dialog.create_ok(helper.language(32022))  # "Progress Aborted"
        except ConnectionExceptions as error:
            self.create_error_dialog(error.value)
        except SettingsExceptions as error:
            self.create_error_dialog(error.value)
        except SystemExit:
            pass

        helper.debug("The synchronize is complete")
        self.quit()

    def _sync(self):
        self.get_movies_from_eh()
        self.sync_upstream()
        self.sync_downstream()

        if self.total_sync_movies == 0:
            dialog.create_ok(helper.language(32050)) # "Your library is up to date. Nothing to sync"
        else:
            dialog.create_ok(helper.language(32054).format(self.total_sync_movies)) # "{0} movies has been synchronized"


    def sync_upstream(self):
        num = self.xbmc.number_watched_movies()
        if num <= 0:
            return

        for j, movies in enumerate(self.xbmc.watched_movies(50)):
            approved_movies = []
            for i, movie in enumerate(movies):
                percent = int(100*((i+(j*50)+1.0)/num))
                self.check_if_canceled()
                self.progress_update(percent, helper.language(32043), movie['title']) # "Syncing upstream"
                if not self.movie_set_as_seen_on_eh(movie['imdbnumber']):
                    self.total_sync_movies = self.total_sync_movies + 1
                    approved_movies.append(movie_factory(movie))
            self.connection.set_movies_watched(approved_movies)


    def sync_downstream(self):
        num = self.xbmc.number_unwatched_movies()
        if num <= 0:
            return

        for j, movies in enumerate(self.xbmc.unwatched_movies(50)):
            approved_movies = []
            for i, movie in enumerate(movies):
                percent = int(100*((i+(j*50)+1.0)/num))
                self.check_if_canceled()
                self.progress_update(percent, helper.language(32052), movie['title']) # "Syncing downstream"
                if self.movie_set_as_seen_on_eh(movie['imdbnumber']):
                    self.total_sync_movies = self.total_sync_movies + 1
                    approved_movies.append(movie['movieid'])
            self.xbmc.set_movies_as_watched(approved_movies)


    def movie_set_as_seen_on_eh(self, imdb):
        for movie in self.eh_watched_movies:
            if imdb == movie['imdb_id']:
                return True
        return False

    def get_movies_from_eh(self):
        self.eh_watched_movies = self.connection.get_watched_movies()
