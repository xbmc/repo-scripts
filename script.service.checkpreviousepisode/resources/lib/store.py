import os

import xbmcvfs

from bossanova808.constants import PROFILE
from bossanova808.utilities import get_setting_as_bool
from bossanova808.logger import Logger
from bossanova808.show_list import ShowList

# The list of shows to ignore, and the YAML file it was kept in before v0.5.0
IGNORED_SHOWS_FILE = 'ignored_shows.json'
LEGACY_IGNORED_SHOWS_FILE = 'ignored_shows.yaml'


class Store:
    """
    Helper class to read in and store the addon settings, and to provide a centralised store
    """

    # Static class variables, referred to by Store.whatever
    # https://docs.python.org/3/faq/programming.html#how-do-i-create-static-class-data-and-static-class-methods
    ignored_shows = None
    force_browse = None
    force_all_seasons = None
    ignore_if_episode_absent_from_library = None

    def __init__(self):
        """
        Load in the addon settings and do some basic initialisation stuff
        """

        Store.load_config_from_settings()

    @staticmethod
    def load_config_from_settings():
        """
        Load in the addon settings, at start or reload them if they have been changed
        :return:
        """
        Logger.info("Loading configuration")

        Store.get_ignored_shows_from_config_file()

        Store.force_browse = get_setting_as_bool('ForceBrowseForShow')
        Store.force_all_seasons = get_setting_as_bool('ForceBrowseAllSeasons')
        Store.ignore_if_episode_absent_from_library = get_setting_as_bool('IgnoreIfEpisodeAbsentFromLibrary')

        Store.log_configuration()

    @staticmethod
    def log_configuration():
        """
        Log out our key configuration values

        :return:
        """
        Logger.info(f'Force Kodi to browse to show dir: {Store.force_browse}')
        Logger.info(f'Force Kodi to browse to all seasons view: {Store.force_all_seasons}')
        Logger.info(f'Ignore if episode absent from library: {Store.ignore_if_episode_absent_from_library}')

    @staticmethod
    def get_ignored_shows_from_config_file():
        """
        (Re)load the user's list of shows to ignore from the saved file, first migrating the
        legacy YAML file from before v0.5.0 if there is one.
        :return:
        """
        Store.migrate_legacy_yaml()
        Store.ignored_shows = ShowList(IGNORED_SHOWS_FILE)
        Logger.info(f'Ignored Shows, loaded from file, is: {dict(Store.ignored_shows.items())}')

    @staticmethod
    def migrate_legacy_yaml():
        """
        One-off: carry the ignored shows over from the old ignored_shows.yaml ({tvshowid: title})
        into the new JSON file, then rename the YAML so it is not read again. The JSON is written
        first, so if anything fails the YAML is left in place and we simply try again next time.
        """
        legacy_file = os.path.join(PROFILE, LEGACY_IGNORED_SHOWS_FILE)
        if not xbmcvfs.exists(legacy_file):
            return

        ignored = ShowList(IGNORED_SHOWS_FILE)
        if ignored.exists():
            Logger.info("Ignored shows JSON already exists, not migrating the legacy YAML file")
        else:
            try:
                import yaml
                with xbmcvfs.File(legacy_file) as yaml_file:
                    data = yaml.safe_load(yaml_file.read())
                if isinstance(data, dict):
                    ignored.update(data)
                if not ignored.save():
                    Logger.error(f'Could not save migrated ignored shows, leaving {legacy_file} in place to retry next time')
                    return
                Logger.info(f'Migrated {len(ignored)} ignored show(s) from {legacy_file}')
            except Exception as e:
                Logger.error(f'Could not migrate legacy ignored shows file {legacy_file}, will retry next time: {e}')
                return

        migrated_file = legacy_file + '.migrated'
        if xbmcvfs.exists(migrated_file):
            xbmcvfs.delete(migrated_file)
        if not xbmcvfs.rename(legacy_file, migrated_file):
            Logger.warning(f'Could not rename legacy ignored shows file {legacy_file}')

    @staticmethod
    def add_ignored_show(tvshow_title, tvshow_id):
        """
        Ignore a show from now on, and save the list.
        """
        Logger.info(f'Set show title {tvshow_title}, id [{tvshow_id}], to ignore from now on.')
        Store.ignored_shows.add(tvshow_id, tvshow_title)
        Store.ignored_shows.save()
