#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.skinbackup
    Kodi addon to backup skin settings
'''

from resources.lib.colorthemes import ColorThemes
from resources.lib.backuprestore import BackupRestore
from resources.lib.utils import log_msg
import xbmc
import _strptime


class Service():
    '''Background service for automatic skin backups and/or automatic colortheme switches'''

    def __init__(self):
        '''Init'''
        self.monitor = xbmc.Monitor()
        self.colorthemes = ColorThemes()
        self.backuprestore = BackupRestore()

    def stop(self):
        '''Cleanup Kodi Cpython instances'''
        del self.monitor
        del self.colorthemes
        del self.backuprestore

    def run(self):
        '''Main service code'''
        while not self.monitor.abortRequested():

            # check daynight colorthemes
            self.colorthemes.check_daynighttheme()

            # check for auto backups
            self.backuprestore.check_autobackup()

            # sleep for one minute
            self.monitor.waitForAbort(60)

        self.stop()


# main entry point
log_msg("Service started")
Service().run()
log_msg("Service stopped")
