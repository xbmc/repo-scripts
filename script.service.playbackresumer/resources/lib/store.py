from .common import *
import os
import json
import xml.etree.ElementTree as ElementTree

import xbmc


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

    # Store the full path of the currently playing file
    currently_playing_file_path = ''
    # What type of video is it?  episode, movie, musicvideo
    type_of_video = 'unknown'
    # What is the library id of this video, if there is one?
    library_id = -1
    # if the video was paused, at what time was it paused?
    paused_time = None
    # how long is the currently playing video (so we can ignorepercentatend)
    length_of_currently_playing_file = 0

    # Is this type of video in the library?  These start as true and are set to false if later not found.
    video_types_in_library = {'episodes': True, 'movies': True, 'musicvideos': True}

    # Persistently store some things, for e.g. access after a re-start
    file_to_store_last_played = ''
    file_to_store_resume_point = ''

    def __init__(self):
        """
        Load in the addon settings and do some basic initialisation stuff
        """
        Store.load_config_from_settings()

        # Create the addon_settings dir if it doesn't already exist
        if not os.path.exists(PROFILE):
            os.makedirs(PROFILE)

        # Two files to persistently track the last played file and the resume point
        Store.file_to_store_last_played = os.path.join(PROFILE, "lastplayed.txt")
        Store.file_to_store_resume_point = os.path.join(PROFILE, "resumepoint.txt")

        # Have to read this in ourselves as there appears to be no plugin function to access it...
        advancedsettings_file = xbmcvfs.translatePath("special://profile/advancedsettings.xml")

        root = None
        try:
            root = ElementTree.parse(advancedsettings_file).getroot()
            log("Found and parsed advancedsettings.xml")
        except (ElementTree.ParseError, IOError):
            log("Could not find/parse advancedsettings.xml, will use defaults")

        if root is not None:
            element = root.find('./video/ignoresecondsatstart')
            if element is not None:
                log("Found advanced setting ignoresecondsatstart")
                Store.ignore_seconds_at_start = int(element.text)
            element = root.find('./video/ignorepercentatend')
            if element is not None:
                log("Found advanced setting ignorepercentatend")
                Store.ignore_percent_at_end = int(element.text)

        log(f"Using ignoresecondsatstart: {Store.ignore_seconds_at_start}, ignorepercentatend: {Store.ignore_percent_at_end}")

    @staticmethod
    def clear_old_play_details():
        """
        As soon as a new file is played, clear out all old references to anything that was being stored as the currently playing file
        :return:
        """
        log("New playback - clearing legacy now playing details")
        Store.library_id = None
        Store.currently_playing_file_path = None
        Store.type_of_video = None
        Store.paused_time = None
        Store.length_of_currently_playing_file = None
        with open(Store.file_to_store_last_played, 'w+') as f:
            f.write('')
        with open(Store.file_to_store_resume_point, 'w+') as f:
            f.write('')

    @staticmethod
    def load_config_from_settings():
        """
        Load in the addon settings, at start or reload them if they have been changed
        :return:
        """
        log("Loading configuration")

        Store.save_interval_seconds = int(float(ADDON.getSetting("saveintervalsecs")))
        Store.resume_on_startup = get_setting_as_bool("resumeonstartup")
        Store.autoplay_random = get_setting_as_bool("autoplayrandom")
        Store.log_configuration()

    @staticmethod
    def log_configuration():
        log(f'Will save a resume point every {Store.save_interval_seconds} seconds')
        log(f'Resume on startup: {Store.resume_on_startup}')
        log(f'Autoplay random video: {Store.autoplay_random}')

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

        log(f'Store.isExcluded(): Checking exclusion settings for [{full_path}]')

        if (full_path.find("pvr://") > -1) and getSettingAsBool('ExcludeLiveTV'):
            log('Store.isExcluded(): Video is PVR (Live TV), which is currently set as an excluded source.')
            return True

        if (full_path.find("http://") > -1 or full_path.find("https://") > -1) and get_setting_as_bool('ExcludeHTTP'):
            log("Store.isExcluded(): Video is from an HTTP/S source, which is currently set as an excluded source.")
            return True

        exclude_path = get_setting('exclude_path')
        if exclude_path and get_setting_as_bool('ExcludePathOption'):
            if full_path.find(exclude_path) > -1:
                log(f'Store.isExcluded(): Video is playing from [{exclude_path}], which is set as excluded path 1.')
                return True

        exclude_path2 = get_setting('exclude_path2')
        if exclude_path2 and get_setting_as_bool('ExcludePathOption2'):
            if full_path.find(exclude_path2) > -1:
                log(f'Store.isExcluded(): Video is playing from [{exclude_path2}], which is set as excluded path 2.')
                return True

        exclude_path3 = get_setting('exclude_path3')
        if exclude_path3 and get_setting_as_bool('ExcludePathOption3'):
            if full_path.find(exclude_path3) > -1:
                log(f'Store.isExcluded(): Video is playing from [{exclude_path3}], which is set as excluded path 3.')
                return True

        return False

    @staticmethod
    def update_current_playing_file_path(filepath):
        """
        Persistently tracks the currently playing file (in case of crash, for possible resuming)

        :param filepath:
        :return:
        """

        if Store.is_excluded(filepath):
            log("Skipping excluded filepath: " + filepath)
            Store.currently_playing_file_path = None
            return

        Store.currently_playing_file_path = filepath

        # write the full path to a file for persistent tracking
        with open(Store.file_to_store_last_played, 'w+') as f:
            f.write(filepath)

        log(f'Last played file set to: {filepath}')

        # check if it is a library video and if so store the library_id and type_of_video
        query = {
            "jsonrpc": "2.0",
            "method": "Files.GetFileDetails",
            "params": {
                "file": filepath,
                "media": "video",
                "properties": [
                    "playcount",
                    "runtime"
                ]
            },
            "id": "fileDetailsCheck"
        }

        log(f'Executing JSON-RPC: {json.dumps(query)}')
        json_response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
        log(f'JSON-RPC Files.GetFileDetails response: {json.dumps(json_response)}')

        Store.type_of_video = 'unknown'

        try:
            Store.type_of_video = json_response['result']['filedetails']['type']
        except:
            Store.library_id = -1
            log(f'Error determining type of video; probably not in Kodi\'s library: {Store.currently_playing_file_path}')

        if Store.type_of_video == 'episode' or Store.type_of_video == 'movie' or Store.type_of_video == 'musicvideo':
            Store.library_id = json_response['result']['filedetails']['id']
            log(f'The library id for this {Store.type_of_video} is {Store.library_id}')
        else:
            Store.library_id = None
            log(f'Unsupported type of video {Store.type_of_video} for {Store.currently_playing_file_path}')

