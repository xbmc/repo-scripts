# -*- coding: utf-8 -*-
import os
from datetime import datetime
import re
import xbmc
import xbmcvfs
from bossanova808.constants import *
from bossanova808.utilities import *
from bossanova808.logger import Logger
from bossanova808.notify import Notify
from resources.lib.store import Store


def clean_log(content):
    """
    Remove username/password details from log file content

    @param content:
    @return:
    """
    for pattern, repl in Store.replaces:
        sanitised = re.sub(pattern, repl, content)
        return sanitised


def gather_log_files():
    """
    Gather a list of the standard Kodi log files (Kodi.log, Kodi.old.log) and the latest crash log, if there is one.

    @return: list of log files in form [type, path], where type is log, oldlog, or crashlog
    """

    # Basic log files
    log_files = [['log', os.path.join(LOG_PATH, 'kodi.log')]]
    if os.path.exists(os.path.join(LOG_PATH, 'kodi.old.log')):
        log_files.append(['oldlog', os.path.join(LOG_PATH, 'kodi.old.log')])

    # Can we find a crashlog?
    # @TODO - check support for CoreElec & add Android if possible...
    crashlog_path = ''
    items = []
    filematch = None
    if xbmc.getCondVisibility('system.platform.osx'):
        crashlog_path = os.path.join(os.path.expanduser('~'), 'Library/Logs/DiagnosticReports/')
        filematch = 'Kodi'
    elif xbmc.getCondVisibility('system.platform.ios'):
        crashlog_path = '/var/mobile/Library/Logs/CrashReporter/'
        filematch = 'Kodi'
    elif xbmc.getCondVisibility('system.platform.linux'):
        crashlog_path = os.path.expanduser('~')  # not 100% accurate (crashlogs can be created in the dir kodi was started from as well)
        filematch = 'kodi_crashlog'
    elif xbmc.getCondVisibility('system.platform.windows'):
        crashlog_path = LOG_PATH
        filematch = 'crashlog'
    elif xbmc.getCondVisibility('system.platform.android'):
        Logger.info(LANGUAGE(32023))

    if crashlog_path and os.path.isdir(crashlog_path):
        lastcrash = None
        dirs, possible_crashlog_files = xbmcvfs.listdir(crashlog_path)
        for item in possible_crashlog_files:
            if filematch in item and os.path.isfile(os.path.join(crashlog_path, item)):
                items.append(os.path.join(crashlog_path, item))
                items.sort(key=lambda f: os.path.getmtime(f))
                if not xbmc.getCondVisibility('system.platform.windows'):
                    lastcrash = [items[-1]]
                else:
                    lastcrash = items[-2:]
        if lastcrash:
            for crashfile in lastcrash:
                log_files.append(['crashlog', crashfile])

    Logger.info("Found these log files to copy:")
    Logger.info(log_files)

    return log_files


def copy_log_files(log_files: []):
    """
    Actually copy the log files to the path in the addon settings

    @param log_files: [] list of log files to copy
    @return: None
    """
    if not log_files:
        Logger.error(LANGUAGE(32025))
        Notify.error(LANGUAGE(32025))
        return

    now_folder_name = 'Kodi_Logs_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    now_destination_path = os.path.join(Store.destination_path, now_folder_name)

    try:
        Logger.info(f'Making destination folder: {now_destination_path}')
        xbmcvfs.mkdir(now_destination_path)
        for file in log_files:
            if file[0] in ['log', 'oldlog']:
                Logger.info(f'Copying sanitised {file[0]} {file[1]}')
                with open(xbmcvfs.translatePath(file[1]), 'r', encoding='utf-8') as current:
                    content = current.read()
                    sanitised = clean_log(content)
                with open(xbmcvfs.translatePath(os.path.join(now_destination_path,os.path.basename(file[1]))), 'w+', encoding='utf-8') as output:
                    output.write(sanitised)
            else:
                Logger.info(f'Copying {file[0]} {file[1]}')
                if not xbmcvfs.copy(file[1], os.path.join(now_destination_path,os.path.basename(file[1]))):
                    return False
        return True

    except Exception as e:
        Logger.error(LANGUAGE(32026) + f": {str(e)}")
        Notify.error(LANGUAGE(32026) + f": {str(e)}")
        return False


# This is 'main'...
def run():

    footprints()
    Store.load_config_from_settings()

    if not Store.destination_path:
        Notify.error(LANGUAGE(32027))
    else:
        log_file_list = gather_log_files()
        result = copy_log_files(log_file_list)
        if result:
            Notify.info(LANGUAGE(32028) + f": {len(log_file_list)}")
        else:
            Notify.info(LANGUAGE(32029))
    # and, we're done...
    footprints(startup=False)
