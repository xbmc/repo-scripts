#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.skinbackup
    Kodi addon to backup skin settings
'''

import sys
from resources.lib.backuprestore import BackupRestore
from resources.lib.colorthemes import ColorThemes
from resources.lib.utils import log_exception, log_msg


class Main():
    '''Main entry point for script'''

    def __init__(self):
        '''Initialization and main code run'''
        try:
            self.params = self.get_params()
            log_msg("called with parameters: %s" % self.params)
            action = self.params.get("action", "")
            if not action:
                # launch main backuprestore dialog
                BackupRestore().backuprestore()
            else:
                # launch module for action provided by this script
                if hasattr(self, action):
                    getattr(self, action)()
                else:
                    log_msg("No such action: %s" % action, xbmc.LOGWARNING)
        except Exception as exc:
            log_exception(__name__, exc)
        finally:
            xbmc.executebuiltin("dialog.Close(busydialog)")

    def backup(self):
        '''backup skin settings to file'''
        backuprestore = BackupRestore()
        filters = self.params.get("filter", [])
        if filters:
            filters = filters.split("|")
        silent = self.params.get("silent", "")
        promptfilename = self.params.get("promptfilename", "") == "true"
        if silent:
            silent_backup = True
            backup_file = silent
        else:
            silent_backup = False
            backup_file = backuprestore.get_backupfilename(promptfilename)
        backuprestore.backup(filters, backup_file, silent_backup)
        del backuprestore

    def restore(self):
        '''restore skin settings from file'''
        backuprestore = BackupRestore()
        silent = self.params.get("SILENT", "")
        if silent and not xbmcvfs.exists(silent):
            log_msg(
                "ERROR while restoring backup ! --> Filename invalid."
                "Make sure you provide the FULL path, for example special://skin/extras/mybackup.zip",
                xbmc.LOGERROR)
            return
        backuprestore.restore(silent)

    def reset(self):
        '''reset skin settings'''
        backuprestore = BackupRestore()
        filters = self.params.get("filter", [])
        if filters:
            filters = filters.split("|")
        silent = self.params.get("silent", "") == "true"
        backuprestore.reset(filters, silent)
        xbmc.Monitor().waitForAbort(2)
        # Optional: If skin helper service present - tell it that the skin settings should be checked.
        if xbmc.getCondVisibility("System.HasAddon(script.skin.helper.service)"):
            xbmc.executebuiltin("RunScript(script.skin.helper.service,action=checkskinsettings)")

    def colorthemes(self):
        '''Open colorthemes dialog'''
        if self.params.get("daynight"):
            self.daynighttheme()
        else:
            ColorThemes().colorthemes()

    def daynighttheme(self):
        '''Select day/night theme'''
        daynight = self.params.get("daynight")
        if daynight:
            ColorThemes().daynightthemes(daynight)

    @staticmethod
    def createcolortheme():
        '''Method to directly create a colortheme'''
        colorthemes = ColorThemes()
        colorthemes.createColorTheme()

    @staticmethod
    def restorecolortheme():
        '''Restore colortheme from backupfile'''
        colorthemes = ColorThemes()
        colorthemes.restoreColorTheme()

    @staticmethod
    def get_params():
        '''extract the params from the called script path'''
        params = {}
        for arg in sys.argv[1:]:
            paramname = arg.split('=')[0]
            paramvalue = arg.replace(paramname + "=", "")
            paramname = paramname.lower()
            if paramname == "action":
                paramvalue = paramvalue.lower()
            params[paramname] = paramvalue
        return params


# MAIN
Main()
