#!/usr/bin/python
# coding: utf-8

########################

import xbmc
import xbmcgui
import random

from resources.lib.utils import split
from resources.lib.helper import *
from resources.lib.image import *
from resources.lib.kodi_monitor import KodiMonitor

########################

MONITOR = KodiMonitor()
KODIVERSION = get_kodiversion()

########################


class Main(xbmc.Monitor):

    def __init__(self):
        self.restart = False

        self.widget_refresh = 0
        self.get_backgrounds = 200
        self.set_background = 10

        self.blur_background = True if visible('Skin.HasSetting(BlurEnabled)') else False
        self.blur_radius = xbmc.getInfoLabel('Skin.String(BlurRadius)') or 2
        self.focus_monitor = True if visible('Skin.HasSetting(FocusMonitor)') else False

        self.master_lock = None
        self.login_reload = False

        self.start()


    def onNotification(self, sender, method, data):
        if ADDON_ID in sender and 'restart' in method:
            self.restart = True


    def stop(self):
        log('Service stopped', force=True)

        if self.restart:
            log('Service is restarting', force=True)
            xbmc.sleep(500) # Give Kodi time to set possible changed skin settings. Just to be sure to bypass race conditions on slower systems.
            DIALOG.notification(ADDON_ID, ADDON.getLocalizedString(32006))
            self.__init__()


    def start(self):
        log('Service started', force=True)

        while not MONITOR.abortRequested() and not self.restart:

            # Focus monitor to split merged info labels by the default / seperator to properties
            if self.focus_monitor:
                split({'value': xbmc.getInfoLabel('ListItem.Genre'), 'property': 'ListItem.Genre', 'separator': ' / '})
                split({'value': xbmc.getInfoLabel('ListItem.Country'), 'property': 'ListItem.Country', 'separator': ' / '})
                split({'value': xbmc.getInfoLabel('ListItem.Studio'), 'property': 'ListItem.Studio', 'separator': ' / '})
                split({'value': xbmc.getInfoLabel('ListItem.Director'), 'property': 'ListItem.Director', 'separator': ' / '})

            # Grab fanarts
            if self.get_backgrounds >= 200:
                log('Start new fanart grabber process')
                fanarts = grabfanart()
                self.get_backgrounds = 0

            else:
                self.get_backgrounds += 1

            # Set fanart property
            if self.set_background >=10 and fanarts:
                winprop('EmbuaryBackground', random.choice(fanarts))
                self.set_background = 0

            else:
                self.set_background += 1

            # Blur backgrounds
            if self.blur_background:
                image_filter(radius=self.blur_radius)

            # Refresh widgets
            if self.widget_refresh >= 600:
                reload_widgets(instant=True)
                self.widget_refresh = 0

            else:
                self.widget_refresh += 1

            # Workaround for login screen bug
            if not self.login_reload:
                if visible('System.HasLoginScreen + Skin.HasSetting(ReloadOnLogin)'):
                    log('System has login screen enabled. Reload the skin to load all strings correctly.')
                    execute('ReloadSkin()')
                    self.login_reload = True

            # Master lock reload logic for widgets
            if visible('System.HasLocks'):
                if self.master_lock is None:
                    self.master_lock = True if visible('System.IsMaster') else False
                    log('Master mode: %s' % self.master_lock)

                if self.master_lock == True and not visible('System.IsMaster'):
                    log('Left master mode. Reload skin.')
                    self.master_lock = False
                    execute('ReloadSkin()')

                elif self.master_lock == False and visible('System.IsMaster'):
                    log('Entered master mode. Reload skin.')
                    self.master_lock = True
                    execute('ReloadSkin()')

            elif self.master_lock is not None:
                self.master_lock = None

            MONITOR.waitForAbort(1)

        self.stop()


if __name__ == '__main__':
    Main()