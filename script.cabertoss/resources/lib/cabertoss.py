# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta
import socket
from typing import List, Tuple

import xbmc
import xbmcvfs
from bossanova808.constants import LOG_PATH
from bossanova808.constants import LANGUAGE
from bossanova808.logger import Logger
from bossanova808.notify import Notify
from resources.lib.store import Store
from resources.lib.clean import clean_log


def _vfs_join(base: str, name: str) -> str:
    if base.startswith(('special://', 'smb://', 'nfs://', 'ftp://', 'http://', 'https://')):
        return base.rstrip('/') + '/' + name
    return os.path.join(base, name)


def gather_log_files() -> List[Tuple[str, str]]:
    """
    Gather a list of the standard Kodi log files (Kodi.log, Kodi.old.log) and the latest crash log, if there is one.

    @return: list of log files as (type, path) tuples, where type is 'log', 'oldlog', or 'crashlog'
    """

    # Basic log files
    log_files = [('log', os.path.join(LOG_PATH, 'kodi.log'))]
    if xbmcvfs.exists(os.path.join(LOG_PATH, 'kodi.old.log')):
        log_files.append(('oldlog', os.path.join(LOG_PATH, 'kodi.old.log')))

    # Can we find a crashlog?
    # @TODO - add Android support if possible..?
    crashlog_path = ''
    items = []
    filematch = None
    if xbmc.getCondVisibility('system.platform.osx'):
        Logger.info("System is OSX")
        crashlog_path = os.path.join(os.path.expanduser('~'), 'Library/Logs/DiagnosticReports/')
        filematch = 'Kodi'
    elif xbmc.getCondVisibility('system.platform.ios'):
        Logger.info("System is IOS")
        crashlog_path = '/var/mobile/Library/Logs/CrashReporter/'
        filematch = 'Kodi'
    elif xbmc.getCondVisibility('system.platform.linux'):
        Logger.info("System is Linux")
        crashlog_path = os.path.expanduser('~')  # not 100% accurate (crashlogs can be created in the dir kodi was started from as well)
        filematch = 'kodi_crashlog'
    elif xbmc.getCondVisibility('system.platform.windows'):
        Logger.info("System is Windows")
        crashlog_path = LOG_PATH
        filematch = 'kodi_'
    elif xbmc.getCondVisibility('system.platform.android'):
        Logger.info("System is Android")
        Logger.info(LANGUAGE(32024))

    # If *ELEC, we can be more specific
    if xbmc.getCondVisibility('System.HasAddon(service.coreelec.settings)') or xbmc.getCondVisibility('System.HasAddon(service.libreelec.settings)'):
        Logger.info("System is *ELEC")
        crashlog_path = LOG_PATH
        filematch = 'kodi_crashlog_'

    if crashlog_path and os.path.isdir(crashlog_path):
        dirs, possible_crashlog_files = xbmcvfs.listdir(crashlog_path)
        for item in possible_crashlog_files:
            item_with_path = os.path.join(crashlog_path, item)
            if filematch in item and os.path.isfile(item_with_path):
                # Don't bother with older crashlogs
                x_days_ago = datetime.now() - timedelta(days=Store.crashlog_max_days)
                if x_days_ago < datetime.fromtimestamp(os.path.getmtime(item_with_path)):
                    items.append(os.path.join(crashlog_path, item))

        items.sort(key=lambda f:os.path.getmtime(f))
        # Windows crashlogs are a dmp and stacktrace combo...
        if xbmc.getCondVisibility('system.platform.windows'):
            lastcrash = items[-2:]
        else:
            lastcrash = items[-1:]

        if lastcrash:
            # Logger.info(f"lastcrash {lastcrash}")
            for crashfile in lastcrash:
                log_files.append(('crashlog', crashfile))

    Logger.info("Found these log files to copy (type, basename):")
    Logger.info([[t, os.path.basename(p)] for t, p in log_files])

    return log_files


def copy_log_files(log_files: List[Tuple[str, str]]) -> bool:
    """
    Copy the provided Kodi log files into a timestamped destination folder under the configured addon destination.

    Detailed behavior:
    - Expects log_files as List[Tuple[str, str]] where `type` is e.g. 'log', 'oldlog', or 'crashlog' and `path` is the source filesystem path.
    - Creates a destination directory at Store.destination_path named "<hostname>_Kodi_Logs_<YYYY-MM-DD_HH-MM-SS>".
    - For entries with type 'log' or 'oldlog', reads the source, sanitises the content with clean_log() (because the log content may contain URLs with embedded user/password details), and writes the sanitised content to a file with the same basename in the destination folder.
    - For other types (e.g., crash logs), copies the source file to the destination folder unchanged.

    Parameters:
        log_files (List[Tuple[str, str]]): list of log descriptors [type, path] to copy.

    Returns:
        bool: True if files were successfully copied, False otherwise.
    """
    if not log_files:
        Logger.error(LANGUAGE(32025))
        Notify.error(LANGUAGE(32025))
        return False

    now_folder_name = f"{socket.gethostname()}_Kodi_Logs_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    now_destination_path = _vfs_join(Store.destination_path, now_folder_name)

    try:
        Logger.info(f'Making destination folder: {now_destination_path}')
        if not xbmcvfs.mkdirs(now_destination_path):
            Logger.error(f'Failed to create destination folder: {now_destination_path}')
            Notify.error(LANGUAGE(32031))
            return False
        for file in log_files:
            if file[0] in ['log', 'oldlog']:
                Logger.info(f'Copying sanitised {file[0]} {file[1]}')
                with open(xbmcvfs.translatePath(file[1]), 'r', encoding='utf-8', errors='replace') as current:
                    content = current.read()
                    sanitised = clean_log(content)
                dest_path = _vfs_join(now_destination_path, os.path.basename(file[1]))
                f = xbmcvfs.File(dest_path, 'w')
                try:
                    f.write(sanitised.encode('utf-8'))
                finally:
                    f.close()
            else:
                Logger.info(f'Copying {file[0]} {file[1]}')
                if not xbmcvfs.copy(file[1], _vfs_join(now_destination_path, os.path.basename(file[1]))):
                    return False
        return True

    except Exception as e:
        Logger.error(LANGUAGE(32026) + f": {str(e)}")
        Notify.error(LANGUAGE(32026) + f": {str(e)}")
        return False


# This is 'main'...
def run():
    """
    Run the log collection and copying flow: initialize this addon's logging, load configuration, gather Kodi log files, copy them to the configured destination, notify the user, and stop this addon's logging.

    This function performs the module's main orchestration. It:
    - Starts the logger for this addon's internal logging (not Kodi's general logging system) and loads addon configuration from settings.
    - If no destination path is configured, shows an error notification and skips copying.
    - Otherwise, notifies the user, gathers available log files, attempts to copy them to the configured destination, and notifies success (including number of files copied) or failure.
    - Stops this addon's internal logging before returning.

    Side effects: starts/stops this addon's internal logging, reads configuration, performs filesystem operations (reading, sanitizing, and copying log files), and shows user notifications. Returns None.
    """
    Logger.start()
    try:
        Store.load_config_from_settings()

        if not Store.destination_path:
            Notify.error(LANGUAGE(32027))
        else:
            Notify.info(LANGUAGE(32030))
            log_file_list = gather_log_files()
            result = copy_log_files(log_file_list)
            if result:
                Notify.info(LANGUAGE(32028) + f": {len(log_file_list)}")
            else:
                Notify.error(LANGUAGE(32029))
    # and, we're done...
    finally:
        Logger.stop()
