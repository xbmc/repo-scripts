"""
Sync watched TV episodes to Episodehunter
"""

import copy
import sync
from resources.exceptions import UserAbortExceptions, ConnectionExceptions, SettingsExceptions
from resources.lib import xbmc_helper
from resources.lib import helper
from resources.lib.gui import dialog
from resources.model import series_model


class Series(sync.Sync):
    """ Two way sync between EH and xbmc"""

    def __init__(self, connection):
        super(Series, self).__init__(connection)
        self.progress = None
        self.upstream_sync = []
        self.downstream_sync = []
        self.eh_watched_series = []
        self.xbmc_series = []

    def sync(self):
        self.create_progress(helper.language(32051))  # "Comparing XBMC database with episodehunter.tv"
        try:
            self.get_series()
            self.get_series_to_sync_upstream()
            self.get_series_to_sync_downstream()
            self._sync()
        except UserAbortExceptions:
            dialog.create_ok(helper.language(32022))  # "Progress Aborted"
        except ConnectionExceptions as error:
            self.create_error_dialog(error.value)
        except SettingsExceptions as error:
            self.create_error_dialog(error.value)
        except SystemExit:
            pass

        self.quit()

    def _sync(self):
        num_sync_upstream = sum(len(e.episodes) for e in self.upstream_sync)
        num_sync_downstream = sum(len(e.episodes) for e in self.downstream_sync)

        if num_sync_upstream > 0 and self.ask_user_yes_or_no(str(num_sync_upstream) + " " + helper.language(32031)):  # 'episodes will be marked as watched on episodehunter.tv'
            self.progress_update(50, helper.language(32043))  # "Uploading shows to episodehunter.tv"
            self.connection.set_shows_watched(self.upstream_sync)

        if num_sync_downstream > 0 and self.ask_user_yes_or_no(str(num_sync_downstream) + " " + helper.language(32049)):  # 'episode will be marked as watched in xbmc':
            self.progress_update(75, helper.language(32052))  # "Setting episodes as seen in xbmc"
            xbmc_helper.set_series_as_watched(self.downstream_sync)

        if num_sync_upstream == 0 and num_sync_downstream == 0:
            dialog.create_ok(helper.language(32050))

    def get_series_to_sync_upstream(self):
        xbmc_series = copy.deepcopy(self.xbmc_series)
        num_series = len(xbmc_series)
        self.upstream_sync = []
        for i, show in enumerate(xbmc_series):
            assert isinstance(show, series_model.Series)
            self.progress.update(50 / num_series * i)
            if self.is_canceled():
                break
            show.episodes = [
                e for e in show.episodes
                if not self.is_marked_as_watched_on_eh(show.tvdb_id, e.season, e.episode) and e.plays > 0
            ]
            if len(show.episodes) == 0:
                continue
            self.upstream_sync.append(show)

    def get_series_to_sync_downstream(self):
        xbmc_series = copy.deepcopy(self.xbmc_series)
        num_series = len(xbmc_series)
        self.downstream_sync = []
        for i, show in enumerate(xbmc_series):
            assert isinstance(show, series_model.Series)
            self.progress.update(50 / num_series * i + 50)
            if self.is_canceled():
                break
            show.episodes = [
                e for e in show.episodes
                if self.is_marked_as_watched_on_eh(show.tvdb_id, e.season, e.episode) and e.plays == 0
            ]
            if len(show.episodes) == 0:
                continue
            self.downstream_sync.append(show)

    def is_marked_as_watched_on_eh(self, series_id, season, episode):
        """
        Check if an episode has been set as watched on EH
        :rtype : bool
        """
        series_id = int(series_id)
        season = int(season)
        episode = int(episode)
        if series_id not in self.eh_watched_series:
            return False
        if season not in self.eh_watched_series[series_id]:
            return False
        if episode not in self.eh_watched_series[series_id][season]:
            return False

        return True

    def get_series(self):
        self.get_series_from_eh()
        self.get_series_from_xbmc()

    def get_series_from_eh(self):
        eh_watched_series = self.connection.get_watched_shows()
        self.eh_watched_series = {}
        for k, v in eh_watched_series.iteritems():
            k = int(k)
            self.eh_watched_series[k] = {}
            for s in v['seasons']:
                self.eh_watched_series[k][int(s['season'])] = s['episodes']

    def get_series_from_xbmc(self):
        xbmc_series = xbmc_helper.get_tv_shows_from_xbmc()

        if not isinstance(xbmc_series, list):
            self.xbmc_series = []
            return

        for tvshow in xbmc_series:
            seasons = xbmc_helper.get_seasons_from_xbmc(tvshow)
            episodes = [xbmc_helper.get_episodes_from_xbmc(tvshow, season['season']) for season in seasons]
            if series_criteria(tvshow, episodes):
                continue
            self.xbmc_series.append(series_model.create_from_xbmc(tvshow, episodes))


def series_criteria(tvshow, episodes):
    """
    Determine if a shows meets the criteria
    :rtype : bool
    """
    if 'title' not in tvshow:
        return False

    if 'imdbnumber' not in tvshow:
        return False

    try:
        if 'year' not in tvshow or int(tvshow['year']) <= 0:
            return False
    except ValueError:
        return False

    if 'playcount' not in tvshow:
        return False

    if not all(['season' in e and 'episode' in e and 'playcount' in e for e in episodes]):
        return False

    return True
