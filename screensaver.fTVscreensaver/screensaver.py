#!/usr/bin/python
# coding: utf-8

########################

from __future__ import division

import random
from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcvfs

from resources.lib.helper import *

########################

MONITOR = xbmc.Monitor()
DIM = ADDON.getSettingBool('dim')
DIM_TIMER = int(ADDON.getSetting('dim_timer')) * 60
DIM_LEVEL = ADDON.getSetting('dim_level')
REFRESH_INTERVAL = float(ADDON.getSetting('refresh'))
SCROLLSPEED = int(ADDON.getSetting('scrollspeed'))
RECURSIVE = ADDON.getSettingBool('recursive')
SOURCE = ADDON.getSetting('source')

########################

class Screensaver(xbmcgui.WindowXMLDialog):

    class ExitMonitor(xbmc.Monitor):
        def __init__(self, exit_callback):
            self.exit_callback = exit_callback

        def onScreensaverDeactivated(self):
            self.exit_callback()

    def onInit(self):
        self.abortRequested = False
        self.exit_monitor = self.ExitMonitor(self.exit)
        scrollspeed = self.calc_scrollspeed()

        self.cDim = self.getControl(300)
        if not DIM:
            self.cDim.setVisible(False)
        else:
            self.cDim.setAnimations([('conditional', 'effect=fade start=0 end=%s time=2000 delay=%s000 condition=true' % (str(DIM_LEVEL),str(DIM_TIMER)))])

        self.cGroup1 = self.getControl(100)
        self.cGroup1.setAnimations([('conditional', 'effect=slide start=0,0 end=-6135,0 time=%s delay0 condition=true reversible=false loop=true' % scrollspeed)])
        self.cGroup2 = self.getControl(200)
        self.cGroup2.setAnimations([('conditional', 'effect=slide start=0,0 end=-6135,0 time=%s delay0 condition=true reversible=false loop=true' % scrollspeed)])

        self.get_images()
        self.start_slideshow()

    def calc_scrollspeed(self):
        maxspeed = 100000
        scrollspeed_delta = int(maxspeed / 100 * SCROLLSPEED)
        speed = int(maxspeed - scrollspeed_delta + maxspeed / 10)
        return str(speed)

    def start_slideshow(self):
        src_poster = self.images if SOURCE == '1' else self.artworks['poster']
        src_fanart = self.images if SOURCE == '1' else self.artworks['fanart']

        while not MONITOR.abortRequested() and not self.abortRequested:
            for i in range(1,8):
                winprop('fTVscreensaver.Poster.%s' % i, random.choice(src_poster))
            for i in range(1,17):
                winprop('fTVscreensaver.Fanart.%s' % i, random.choice(src_fanart))

            MONITOR.waitForAbort(REFRESH_INTERVAL)

    def get_images(self):
        if ADDON.getSetting('source') == '1':
            self.images = self.scan_folder(ADDON.getSetting('path'))

        else:
            poster = []
            fanart = []

            for media in ['Movies','TVShows']:
                json_query = json_call('VideoLibrary.Get%s' % media,
                                        properties=['art']
                                        )

                try:
                    for item in json_query['result'][media.lower()]:
                        if item['art'].get('poster'):
                            poster.append(item['art'].get('poster'))
                        if item['art'].get('fanart'):
                            fanart.append(item['art'].get('fanart'))
                except Exception:
                    pass

            self.artworks = {}
            self.artworks['poster'] = poster
            self.artworks['fanart'] = fanart

    def scan_folder(self, path):
        dirs, files = xbmcvfs.listdir(path)

        images = [
            xbmc.validatePath(path + f) for f in files
            if f.lower()[-3:] in ('jpg', 'png')
        ]

        if RECURSIVE:
            for directory in dirs:
                if directory.startswith('.'):
                    continue

                images.extend(
                    self.scan_folder(
                        xbmc.validatePath('/'.join((path, directory, '')))
                    )
                )

        return images

    def exit(self):
        self.abortRequested = True
        for i in range(1,8):
            winprop('fTVscreensaver.Poster.%s' % i, clear=True)
        for i in range(1,17):
            winprop('fTVscreensaver.Fanart.%s' % i, clear=True)
        self.close()


if __name__ == '__main__':
    screensaver = Screensaver('screensaver.fTVscreensaver.xml',ADDON_PATH,'default')
    screensaver.doModal()
    del screensaver