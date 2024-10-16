import os
import yaml
from bossanova808.logger import Logger
from bossanova808.constants import *
from bossanova808.utilities import *
import xbmc
import xbmcvfs


class Store:
    """
    Helper class to read in and store the addon settings, and to provide a centralised store
    """

    # Static class variables, referred to by Store.whatever
    # https://docs.python.org/3/faq/programming.html#how-do-i-create-static-class-data-and-static-class-methods
    ignored_shows_file = None
    ignored_shows = {}
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

        Store.ignored_shows_file = xbmcvfs.translatePath(os.path.join(PROFILE, 'ignored_shows.yaml'))
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
        Load the user's list of shows to ignore from the saved file
        :return:
        """

        # Update our internal list of ignored shows if there are any...
        if os.path.exists(Store.ignored_shows_file):
            Logger.info("Loading ignored shows from config file: " + Store.ignored_shows_file)
            with open(Store.ignored_shows_file, 'r') as yaml_file:
                Store.ignored_shows = yaml.load(yaml_file, Loader=yaml.FullLoader)
        else:
            Store.ignored_shows = {}

        Logger.info(f'Ignored Shows, loaded from yaml file, is: {Store.ignored_shows}')

    @staticmethod
    def write_ignored_shows_to_config(new_to_ignore_tv_show_title=None, new_to_ignore_tv_show_id=None):

        # Addon settings folder not there yet?  Make it...
        if not xbmcvfs.exists(PROFILE):
            xbmcvfs.mkdirs(PROFILE)

        # Add new show, if supplied, to our dict of ignored shows if there is one...
        if new_to_ignore_tv_show_id:
            Logger.info(f'Set show title {new_to_ignore_tv_show_title}, id [{new_to_ignore_tv_show_id}], to ignore from now on.')
            Store.ignored_shows[new_to_ignore_tv_show_id] = new_to_ignore_tv_show_title

        # No ignored shows?  We've been called from settings after removal of the last ignored show
        # Clean up & delete the empty file...
        if len(Store.ignored_shows) == 0:
            Logger.info("No shows left to ignore, removing ignored shows file")
            if os.path.exists(Store.ignored_shows_file):
                os.remove(Store.ignored_shows_file)
            return

        # Shows to ignore, so dump the current dict to our yaml file (clobber over any old file)
        with open(Store.ignored_shows_file, 'w') as yaml_file:
            Logger.info(f'Ignored Shows to write to config is: {Store.ignored_shows}')
            yaml.dump(Store.ignored_shows, yaml_file, default_flow_style=False)
