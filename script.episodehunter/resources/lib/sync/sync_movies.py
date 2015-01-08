from resources.lib.sync import Sync
from resources.lib import helper
from resources.model import movie_model
from resources.lib.gui import dialog
from resources.lib import xbmc_helper
from resources.exceptions import ConnectionExceptions, UserAbortExceptions, SettingsExceptions


class Movies(Sync):
    """
    Sync class
    Two-way sync between xbmc and EH
    """

    def __init__(self, connection):
        super(Movies, self).__init__(connection)
        self.progress = None
        self.upstream_sync = []
        self.downstream_sync = []
        self.eh_watched_movies = None
        self.xbmc_movies = None

    def sync(self):
        self.create_progress(helper.language(32051))  # "Comparing XBMC database with episodehunter.tv"
        try:
            self.get_movies()
            self.get_movies_to_sync_upstream()
            self.get_movies_to_sync_downstream()
            self._sync()
        except UserAbortExceptions:
            dialog.create_ok(helper.language(32022))  # "Progress Aborted"
        except ConnectionExceptions as error:
            self.create_error_dialog(helper.language(32018), error.value)  # "Error"
        except SettingsExceptions as error:
            self.create_error_dialog(helper.language(32018), error.value)  # "Error"
        except SystemExit:
            pass
        except Exception as error:
            self.create_error_dialog(helper.language(32018), str(error))  # "Error"

        self.quit()

    def _sync(self):
        num_sync_upstream = len(self.upstream_sync)
        num_sync_downstream = len(self.downstream_sync)

        if num_sync_upstream > 0 and self.ask_user_yes_or_no(str(num_sync_upstream) + " " + helper.language(32023)):  # 'Movies will be added as watched on EpisodeHunter'
            self.progress_update(50, helper.language(32044))  # "Uploading movies to EpisodeHunter"
            self.connection.set_movies_watched(self.upstream_sync)

        if num_sync_downstream > 0 and self.ask_user_yes_or_no(str(num_sync_downstream) + " " + helper.language(32047)):  # 'Movies will be marked as watched in xbmc'
            self.progress_update(75, helper.language(32048))  # "Setting movies as seen in xbmc"
            xbmc_helper.set_movies_as_watched(self.downstream_sync)

        if num_sync_upstream == 0 and num_sync_downstream == 0:
            dialog.create_ok(helper.language(32050))

    def get_movies_to_sync_upstream(self):
        num_movies = len(self.xbmc_movies)
        self.upstream_sync = []
        for i, m in enumerate(self.xbmc_movies):
            assert isinstance(m, movie_model.Movie)
            self.progress.update(50 / num_movies * i)
            if self.is_canceled():
                break
            if m.plays <= 0:
                continue
            if self.movie_set_as_seen_on_eh(m.imdb_id):
                continue
            self.upstream_sync.append(m)

    def get_movies_to_sync_downstream(self):
        num_movies = len(self.xbmc_movies)
        self.downstream_sync = []
        for i, m in enumerate(self.xbmc_movies):
            assert isinstance(m, movie_model.Movie)
            self.progress.update(50 / num_movies * i + 50)
            if self.is_canceled():
                break
            if m.plays > 0:
                continue
            if not self.movie_set_as_seen_on_eh(m.imdb_id):
                continue
            self.downstream_sync.append(m)

    def movie_set_as_seen_on_eh(self, imdb):
        """
        Check if a movie has been set as watched on EH
        :rtype : bool
        """
        for movie in self.eh_watched_movies:
            if imdb == movie['imdb_id']:
                return True
        return False

    def get_movies(self):
        self.eh_watched_movies = self.connection.get_watched_movies()
        xbmc_movies = xbmc_helper.get_movies_from_xbmc()
        self.xbmc_movies = [movie_model.create_from_xbmc(m) for m in xbmc_movies if movie_criteria(m)]


def movie_criteria(movie):
    """
    Determine if a movie meets the criteria
    :rtype : bool
    """
    if 'imdbnumber' not in movie:
        helper.debug("Skipping a movie - no IMDb ID was found")
        return False

    if 'title' not in movie and 'originaltitle' not in movie:
        helper.debug("Skipping a movie - title not found")
        return False

    try:
        if 'year' not in movie or int(movie['year']) <= 0:
            helper.debug("Skipping a movie - year not found")
            return False
    except ValueError, error:
        helper.debug(error)
        return False

    if 'playcount' not in movie:
        helper.debug("Skipping movie - play count not found")
        return False

    return True
