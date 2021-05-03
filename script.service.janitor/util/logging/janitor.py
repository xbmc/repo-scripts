#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import time

import xbmc
from xbmcgui import Dialog, WindowXMLDialog

from util.addon_info import ADDON, ADDON_PROFILE
from util.logging.kodi import debug, translate


class Log(object):
    """
    The Log class will handle the writing of cleaned files to a log file in the addon settings.

    This log file will be automatically created upon first prepending data to it.

    Supported operations are prepend, trim, clear and get.
    """
    def __init__(self):
        self.logpath = os.path.join(ADDON_PROFILE, "cleaner.log")

    def prepend(self, data):
        """
        Prepend the given data to the current log file. Will create a new log file if none exists.

        :type data: list
        :param data: A list of strings to prepend to the log file.
        """
        if data:
            previous_data = ""
            debug("Prepending the log file with new data")
            try:
                debug("Backing up current log")
                with open(self.logpath, "r", encoding="utf-8") as f:
                    previous_data = f.read()
            except (IOError, OSError, FileNotFoundError) as err:
                debug(f"{err}", xbmc.LOGERROR)
                debug("Assuming there is no previous log data")
                previous_data = ""
            finally:
                try:
                    with open(self.logpath, "w", encoding="utf-8") as f:
                        debug("Writing new log data")
                        f.write(f"[B][{time.strftime('%d/%m/%Y  -  %H:%M:%S')}][/B]\n")
                        for line in data:
                            f.write(f" • {line}\n")
                        f.write("\n")

                        debug("Appending previous log file contents")
                        f.writelines(previous_data)
                except (IOError, OSError) as err:
                    debug(f"{err}", xbmc.LOGERROR)
        else:
            debug("Nothing to log")

    def trim(self, lines_to_keep=25):
        """
        Trim the log file to contain a maximum number of lines.

        :type lines_to_keep: int
        :param lines_to_keep: The number of lines to preserve. Any lines beyond this number get erased. Defaults to 25.
        :rtype: unicode
        :return: The contents of the log file after trimming.
        """
        try:
            debug("Trimming log file contents.")
            with open(self.logpath, encoding="utf-8") as f:
                debug(f"Saving the top {lines_to_keep} lines.")
                lines = []
                for i in range(lines_to_keep):
                    lines.append(f.readline())
        except (IOError, OSError) as err:
            debug(f"{err}", xbmc.LOGERROR)
        else:
            try:
                debug("Removing all log contents.")
                with open(self.logpath, "w", encoding="utf-8") as f:
                    debug("Restoring saved log contents.")
                    f.writelines(lines)
            except (IOError, OSError) as err:
                debug(f"{err}", xbmc.LOGERROR)
            else:
                return self.get()

    def clear(self):
        """
        Erase the contents of the log file.

        :rtype: unicode
        :return: An empty string if clearing succeeded.
        """
        try:
            debug("Clearing log file contents.")
            with open(self.logpath, "r+", encoding="utf-8") as f:
                f.truncate()
        except (IOError, OSError) as err:
            debug(f"{err}", xbmc.LOGERROR)
        else:
            return self.get()

    def get(self):
        """
        Retrieve the contents of the log file. Creates a new log if none is found.

        :rtype: unicode
        :return: The contents of the log file.
        """
        try:
            debug("Retrieving log file contents.")
            with open(self.logpath, "r", encoding="utf-8") as f:
                contents = f.read()
        except (IOError, OSError) as err:
            debug(f"{err}", xbmc.LOGERROR)
        else:
            return contents


class LogViewerDialog(WindowXMLDialog):
    """
    The LogViewerDialog class is an extension of the default windows supplied with Kodi.

    It is used to display the contents of a log file, and as such uses a fullscreen window to show as much text as
    possible. It also contains two buttons for trimming and clearing the contents of the log file.
    """
    TEXTBOXID = 202
    TRIMBUTTONID = 301
    CLEARBUTTONID = 302

    def __init__(self, xml_filename, script_path, default_skin="Default", default_res="720p", *args, **kwargs):
        self.log = Log()
        WindowXMLDialog.__init__(self, xml_filename, script_path, default_skin, default_res)

    def onInit(self):
        self.getControl(self.TEXTBOXID).setText(self.log.get())

    def onClick(self, control_id, *args):
        if control_id == self.TRIMBUTTONID:
            if Dialog().yesno(translate(32604), translate(32605)):
                self.getControl(self.TEXTBOXID).setText(self.log.trim())
        elif control_id == self.CLEARBUTTONID:
            if Dialog().yesno(translate(32604), translate(32606)):
                self.getControl(self.TEXTBOXID).setText(self.log.clear())
        else:
            raise ValueError("Unknown button pressed")


def view_log():
    win = LogViewerDialog("JanitorLogViewer.xml", ADDON.getAddonInfo("path"))
    win.doModal()
    del win
