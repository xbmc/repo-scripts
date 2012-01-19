#
#      Copyright (C) 2012 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
import buggalo
import xbmc
import xbmcaddon
import os
import source
import gui
import notification

try:
    SOURCES = {
        'YouSee.tv' : source.YouSeeTvSource,
        'DR.dk' : source.DrDkSource,
        'TVTID.dk' : source.TvTidSource,
        'XMLTV' : source.XMLTVSource
        }

    ADDON = xbmcaddon.Addon()
    sourceRef = SOURCES[ADDON.getSetting('source')]
    SETTINGS = {
        'cache.path' : xbmc.translatePath(ADDON.getAddonInfo('profile')),
        'xmltv.file' : ADDON.getSetting('xmltv.file'),
        'youseetv.category' : ADDON.getSetting('youseetv.category'),
        'youseewebtv.playback' : ADDON.getSetting('youseewebtv.playback'),
        'danishlivetv.playback' : ADDON.getSetting('danishlivetv.playback'),
        'notifications.enabled' : ADDON.getSetting('notifications.enabled'),
        'cache.data.on.xbmc.startup' : ADDON.getSetting('cache.data.on.xbmc.startup'),
        'clear.cache.on.xbmc.startup' : ADDON.getSetting('clear.cache.on.xbmc.startup')
    }

    if not os.path.exists(SETTINGS['cache.path']):
        os.makedirs(SETTINGS['cache.path'])
    SOURCE = sourceRef(SETTINGS)
    xbmc.log("[script.tvguide] Using source: " + str(sourceRef), xbmc.LOGDEBUG)

    if __name__ == '__main__':
        n = notification.Notification(SOURCE, ADDON.getAddonInfo('path'), xbmc.translatePath(ADDON.getAddonInfo('profile')))
        w = gui.TVGuide(source = SOURCE, notification = n)
        w.doModal()
        del w
except Exception:
    buggalo.onExceptionRaised()
