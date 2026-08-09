import os
import xml.etree.ElementTree as ElementTree

import xbmcvfs

from bossanova808.constants import PROFILE
from bossanova808.logger import Logger
from bossanova808.utilities import get_setting, get_setting_as_bool


class Store:
    """
    Helper class to read in and store the addon settings, and to provide a centralised store
    """

    # Static class variables, referred to by Store.whatever
    # https://docs.python.org/3/faq/programming.html#how-do-i-create-static-class-data-and-static-class-methods
    save_interval_seconds = 30
    ignore_seconds_at_start = 180
    ignore_percent_at_end = 8
    resume_on_startup = False
    autoplay_random = False
    kodi_event_monitor = None
    player_monitor = None

    # The currently playing item, as detected by bossanova808.playback.Playback
    current_playback = None
    # if the video was paused, at what time was it paused?
    paused_time = None

    # Is this type of video in the library?  These start as true and are set to false if later not found.
    video_types_in_library = {'episodes': True, 'movies': True, 'musicvideos': True}

    # Persistently store the current playback (as Playback JSON), for resuming after a re-start
    file_to_store_playback = ''

    def __init__(self):
        """
        Load in the addon settings and do some basic initialisation stuff
        """
        Store.load_config_from_settings()

        # Create the addon_settings dir if it doesn't already exist
        if not os.path.exists(PROFILE):
            os.makedirs(PROFILE)

        # One file to persistently track the current playback (path, metadata, resume point)
        Store.file_to_store_playback = os.path.join(PROFILE, "playback.json")

        # Have to read this in ourselves as there appears to be no plugin function to access it...
        advancedsettings_file = xbmcvfs.translatePath("special://profile/advancedsettings.xml")

        root = None
        try:
            root = ElementTree.parse(advancedsettings_file).getroot()
            Logger.info("Found and parsed advancedsettings.xml")
        except (ElementTree.ParseError, IOError):
            Logger.info("Could not find/parse advancedsettings.xml, will use defaults")

        if root is not None:
            element = root.find('./video/ignoresecondsatstart')
            if element is not None:
                Logger.info("Found advanced setting ignoresecondsatstart")
                Store.ignore_seconds_at_start = int(element.text)
            element = root.find('./video/ignorepercentatend')
            if element is not None:
                Logger.info("Found advanced setting ignorepercentatend")
                Store.ignore_percent_at_end = int(element.text)

        Logger.info(f"Using ignoresecondsatstart: {Store.ignore_seconds_at_start}, ignorepercentatend: {Store.ignore_percent_at_end}")

    @staticmethod
    def clear_old_play_details():
        """
        As soon as a new file is played, clear out all old references to anything that was being stored as the currently playing file
        :return:
        """
        Logger.info("New playback - clearing legacy now playing details")
        Store.current_playback = None
        Store.paused_time = None
        if os.path.exists(Store.file_to_store_playback):
            os.remove(Store.file_to_store_playback)

    @staticmethod
    def load_config_from_settings():
        """
        Load in the addon settings, at start or reload them if they have been changed
        :return:
        """
        Logger.info("Loading configuration")

        Store.save_interval_seconds = int(float(get_setting("saveintervalsecs") or 30))
        Store.resume_on_startup = get_setting_as_bool("resumeonstartup")
        Store.autoplay_random = get_setting_as_bool("autoplayrandom")
        Store.log_configuration()

    @staticmethod
    def log_configuration():
        Logger.info(f'Will save a resume point every {Store.save_interval_seconds} seconds')
        Logger.info(f'Resume on startup: {Store.resume_on_startup}')
        Logger.info(f'Autoplay random video: {Store.autoplay_random}')

    @staticmethod
    def is_excluded(full_path):
        """
        Check exclusion settings for a given file
        :param full_path: the full path of the file to check if is excluded
        :return:
        """

        # Short circuit if called without something to check
        if not full_path:
            return True

        Logger.info(f'Store.isExcluded(): Checking exclusion settings for [{full_path}]')

        if (full_path.find("pvr://") > -1) and get_setting_as_bool('ExcludeLiveTV'):
            Logger.info('Store.isExcluded(): Video is PVR (Live TV), which is currently set as an excluded source.')
            return True

        if (full_path.find("http://") > -1 or full_path.find("https://") > -1) and get_setting_as_bool('ExcludeHTTP'):
            Logger.info("Store.isExcluded(): Video is from an HTTP/S source, which is currently set as an excluded source.")
            return True

        exclude_path = get_setting('exclude_path')
        if exclude_path and get_setting_as_bool('ExcludePathOption'):
            if full_path.find(exclude_path) > -1:
                Logger.info(f'Store.isExcluded(): Video is playing from [{exclude_path}], which is set as excluded path 1.')
                return True

        exclude_path2 = get_setting('exclude_path2')
        if exclude_path2 and get_setting_as_bool('ExcludePathOption2'):
            if full_path.find(exclude_path2) > -1:
                Logger.info(f'Store.isExcluded(): Video is playing from [{exclude_path2}], which is set as excluded path 2.')
                return True

        exclude_path3 = get_setting('exclude_path3')
        if exclude_path3 and get_setting_as_bool('ExcludePathOption3'):
            if full_path.find(exclude_path3) > -1:
                Logger.info(f'Store.isExcluded(): Video is playing from [{exclude_path3}], which is set as excluded path 3.')
                return True

        return False
