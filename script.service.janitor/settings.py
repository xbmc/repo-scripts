#!/usr/bin/python
# -*- coding: utf-8 -*-

import utils
from xbmc import translatePath

# Exhaustive list of constants as used by the addon's settings
service_enabled = "service_enabled"
delete_folders = "delete_folders"
ignore_extensions = "ignore_extensions"

clean_related = "clean_related"
delayed_start = "delayed_start"
scan_interval = "scan_interval"

notifications_enabled = "notifications_enabled"
notify_when_idle = "notify_when_idle"
debugging_enabled = "debugging_enabled"

default_action = "default_action"
cleaning_type = "cleaning_type"
clean_kodi_library = "clean_kodi_library"
clean_movies = "clean_movies"
clean_tv_shows = "clean_tv_shows"
clean_music_videos = "clean_music_videos"
clean_when_idle = "clean_when_idle"

enable_expiration = "enable_expiration"
expire_after = "expire_after"

clean_when_low_rated = "clean_when_low_rated"
minimum_rating = "minimum_rating"
ignore_no_rating = "ignore_no_rating"

clean_when_low_disk_space = "clean_when_low_disk_space"
disk_space_threshold = "disk_space_threshold"
disk_space_check_path = "disk_space_check_path"

holding_folder = "holding_folder"
create_subdirs = "create_subdirs"

not_in_progress = "not_in_progress"

keep_hard_linked = "keep_hard_linked"

exclusion_enabled = "exclusion_enabled"
exclusion1 = "exclusion1"
exclusion2 = "exclusion2"
exclusion3 = "exclusion3"
exclusion4 = "exclusion4"
exclusion5 = "exclusion5"

bools = [service_enabled, delete_folders, clean_related, notifications_enabled, notify_when_idle, debugging_enabled,
         clean_kodi_library, clean_movies, clean_tv_shows, clean_music_videos, clean_when_idle, enable_expiration,
         clean_when_low_rated, ignore_no_rating, clean_when_low_disk_space, create_subdirs,
         not_in_progress, keep_hard_linked, exclusion_enabled]
strings = [ignore_extensions, cleaning_type, default_action]
numbers = [delayed_start, scan_interval, expire_after, minimum_rating, disk_space_threshold]
paths = [disk_space_check_path, holding_folder, create_subdirs, exclusion1, exclusion2, exclusion3, exclusion4,
         exclusion5]


def get_setting(setting):
    """
    Get the value for a specified setting.

    Note: Make sure to check the return type of the setting you get.

    :param setting: The setting you want to retrieve the value of.
    :return: The value corresponding to the provided setting. This can be a float, a bool, a string or None.
    """
    if setting in bools:
        return bool(utils.ADDON.getSetting(setting) == "true")
    elif setting in numbers:
        return float(utils.ADDON.getSetting(setting))
    elif setting in strings:
        return str(utils.ADDON.getSetting(setting))
    elif setting in paths:
        return translatePath(utils.ADDON.getSetting(setting).encode("utf-8"))
    else:
        raise ValueError("Failed loading {0!r} value. Type {1!r} cannot be handled.".format(setting, type(setting)))


def load_all():
    """
    Get the values for all settings.

    Note: Make sure to check the return type of settings you get.

    :rtype: dict
    :return: All settings and their current values.
    """
    settings = dict()
    for s in bools + strings + numbers + paths:
        settings[s] = get_setting(s)
    return settings
