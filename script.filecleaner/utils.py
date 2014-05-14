#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import time
from ctypes import *

import xbmcgui
import xbmcvfs
from settings import *


# Addon info
__addonID__ = "script.filecleaner"
__addon__ = Addon(__addonID__)
__title__ = __addon__.getAddonInfo("name")
__profile__ = xbmc.translatePath(__addon__.getAddonInfo("profile")).decode("utf-8")
__icon__ = xbmc.translatePath(__addon__.getAddonInfo("icon")).decode("utf-8")


class Log(object):
    """
    The Log class will handle the writing of cleaned files to a log file in the addon settings.

    This log file will be automatically created upon first prepending data to it.

    Supported operations are prepend, trim, clear and get.
    """
    def __init__(self):
        self.logpath = os.path.join(__profile__, "cleaner.log")

    def prepend(self, data):
        """
        Prepend the given data to the current log file. Will create a new log file if none exists.

        :type data: list
        :param data: A list of strings to prepend to the log file.
        """
        try:
            debug("Prepending the log file with new data.")
            debug("Backing up current log.")
            f = open(self.logpath, "a+")  # use append mode to make sure it is created if non-existent
            previous_data = f.read()
        except (IOError, OSError) as err:
            debug("%s" % err, xbmc.LOGERROR)
        else:
            f.close()

            try:
                debug("Writing new log data.")
                f = open(self.logpath, "w")
                if data:
                    f.write("[B][%s][/B]\n" % time.strftime("%d/%m/%Y  -  %H:%M:%S"))
                    for line in data:
                        if isinstance(line, unicode):
                            line = line.encode("utf-8")
                        f.write(" - %s\n" % line)
                    f.write("\n")
                    debug("New data written to log file.")
                else:
                    debug("No data to write. Stopping.")

                debug("Appending previous log file contents.")
                f.writelines(previous_data)
            except (IOError, OSError) as err:
                debug("%s" % err, xbmc.LOGERROR)
            else:
                f.close()

    def trim(self, lines_to_keep=25):
        """
        Trim the log file to contain a maximum number of lines.

        :type lines_to_keep: int
        :param lines_to_keep: The number of lines to preserve. Any lines beyond this number get erased. Defaults to 25.
        :rtype: str
        :return: The contents of the log file after trimming.
        """
        try:
            debug("Trimming log file contents.")
            f = open(self.logpath, "r")
            debug("Saving the top %d lines." % lines_to_keep)
            lines = []
            for i in xrange(lines_to_keep):
                lines.append(f.readline())
        except (IOError, OSError) as err:
            debug("%s" % err, xbmc.LOGERROR)
        else:
            f.close()

            try:
                debug("Removing all log contents.")
                f = open(self.logpath, "w")
                debug("Restoring saved log contents.")
                f.writelines(lines)
            except (IOError, OSError) as err:
                debug("%s" % err, xbmc.LOGERROR)
            else:
                f.close()
                return self.get()

    def clear(self):
        """
        Erase the contents of the log file.

        :rtype: str
        :return: An empty string if clearing succeeded.
        """
        try:
            debug("Clearing log file contents.")
            f = open(self.logpath, "r+")
            f.truncate()
        except (IOError, OSError) as err:
            debug("%s" % err, xbmc.LOGERROR)
        else:
            f.close()
            return self.get()

    def get(self):
        """
        Retrieve the contents of the log file.

        :rtype: str
        :return: The contents of the log file.
        """
        try:
            debug("Retrieving log file contents.")
            f = open(self.logpath, "r")
        except (IOError, OSError) as err:
            debug("%s" % err, xbmc.LOGERROR)
        else:
            contents = f.read()
            f.close()
            return contents


def get_free_disk_space(path):
    """Determine the percentage of free disk space.

    :type path: str
    :param path: The path to the drive to check. This can be any path of any depth on the desired drive.
    :rtype: float
    :return: The percentage of free space on the disk; 100% if errors occur.
    """
    percentage = float(100)
    debug("Checking for disk space on path: %r" % path)
    if xbmcvfs.exists(path):
        if xbmc.getCondVisibility("System.Platform.Windows"):
            debug("We are checking disk space from a Windows file system")
            debug("The path to check is %r" % path)

            if r"://" in path:
                debug("We are dealing with network paths")
                debug("Extracting information from share %r" % path)

                regex = "(?P<type>smb|nfs|afp)://(?:(?P<user>.+):(?P<pass>.+)@)?(?P<host>.+?)/(?P<share>.+?).*$"
                pattern = re.compile(regex, flags=re.I | re.U)
                match = pattern.match(path)
                try:
                    share = match.groupdict()
                    debug("Protocol: %r, User: %r, Password: %r, Host: %r, Share: %r" %
                          (share["type"], share["user"], share["pass"], share["host"], share["share"]))
                except AttributeError as ae:
                    debug("%r\nCould not extract required data from %r" % (ae, path), xbmc.LOGERROR)
                    return percentage

                debug("Creating UNC paths so Windows understands the shares")
                path = os.path.normcase(r"\\" + share["host"] + os.sep + share["share"])
                debug("UNC path: %r" % path)
                debug("If checks fail because you need credentials, please mount the share first")
            else:
                debug("We are dealing with local paths")

            if not isinstance(path, unicode):
                debug("Converting path to unicode for disk space checks")
                path = path.decode("mbcs")
                debug("New path: %r" % path)

            bytes_total = c_ulonglong(0)
            bytes_free = c_ulonglong(0)
            windll.kernel32.GetDiskFreeSpaceExW(c_wchar_p(path), byref(bytes_free), byref(bytes_total), None)

            try:
                percentage = float(bytes_free.value) / float(bytes_total.value) * 100
                debug("Hard disk check results:")
                debug("Bytes free: %s" % bytes_free.value)
                debug("Bytes total: %s" % bytes_total.value)
            except ZeroDivisionError:
                notify(translate(32511), 15000, level=xbmc.LOGERROR)
        else:
            debug("We are checking disk space from a non-Windows file system")
            debug("Stripping %r of all redundant stuff." % path)
            path = os.path.normpath(path)
            debug("The path now is " + path)

            try:
                diskstats = os.statvfs(path)
                percentage = float(diskstats.f_bfree) / float(diskstats.f_blocks) * 100
                debug("Hard disk check results:")
                debug("Bytes free: %r" % diskstats.f_bfree)
                debug("Bytes total: %r" % diskstats.f_blocks)
            except OSError as ose:
                # TODO: Linux cannot check remote share disk space yet
                # notify(translate(32512), 15000, level=xbmc.LOGERROR)
                notify(translate(32524), 15000, level=xbmc.LOGERROR)
                debug("Error accessing %r: %r" % (path, ose))
            except ZeroDivisionError:
                notify(translate(32511), 15000, level=xbmc.LOGERROR)
    else:
        notify(translate(32513), 15000, level=xbmc.LOGERROR)

    debug("Free space: %0.2f%%" % percentage)
    return percentage


def disk_space_low():
    """Check whether the disk is running low on free space.

    :rtype: bool
    :return: True if disk space is below threshold (set through addon settings), False otherwise.
    """
    return get_free_disk_space(get_setting(disk_space_check_path)) <= get_setting(disk_space_threshold)


def translate(msg_id):
    """
    Retrieve a localized string by id.

    :type msg_id: int
    :param msg_id: The id of the localized string.
    :rtype: str
    :return: The localized string. Empty if msg_id is not an integer.
    """
    if isinstance(msg_id, int):
        return __addon__.getLocalizedString(msg_id)
    else:
        return ""


def notify(message, duration=5000, image=__icon__, level=xbmc.LOGNOTICE, sound=True):
    """
    Display an XBMC notification and log the message.

    :type message: str
    :param message: the message to be displayed (and logged).
    :type duration: int
    :param duration: the duration the notification is displayed in milliseconds (defaults to 5000)
    :type image: str
    :param image: the path to the image to be displayed on the notification (defaults to ``icon.png``)
    :type level: int
    :param level: (Optional) the log level (supported values are found at xbmc.LOG...)
    :type sound: bool
    :param sound: (Optional) Whether or not to play a sound with the notification. (defaults to ``True``)
    """
    debug(message, level)
    if get_setting(notifications_enabled) and not (get_setting(notify_when_idle) and xbmc.Player().isPlaying()):
        xbmcgui.Dialog().notification(__title__, message, image, duration, sound)


def debug(message, level=xbmc.LOGNOTICE):
    """
    Write a debug message to xbmc.log

    :type message: str
    :param message: the message to log
    :type level: int
    :param level: (Optional) the log level (supported values are found at xbmc.LOG...)
    """
    if get_setting(debugging_enabled):
        if isinstance(message, unicode):
            message = message.encode("utf-8")
        for line in message.splitlines():
            xbmc.log(msg=__title__ + ": " + line, level=level)
