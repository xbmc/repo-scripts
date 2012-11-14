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
import xbmcaddon
import notification
import xbmc
import source as src

ADDON = xbmcaddon.Addon(id = 'script.tvguide')
source = src.instantiateSource(ADDON)
if ADDON.getSetting('cache.data.on.xbmc.startup') == 'true':
    try:
        channelList = None
        if source._isChannelListCacheExpired():
            channelList = source.updateChannelAndProgramListCaches()

    except Exception, ex:
        xbmc.log('[script.tvguide] Unable to update caches: %s' % str(ex) , xbmc.LOGDEBUG)

if ADDON.getSetting('notifications.enabled') == 'true':
    try:
        n = notification.Notification(source, ADDON.getAddonInfo('path'))
        n.scheduleNotifications()
    except Exception, ex:
        xbmc.log('[script.tvguide] Unable to schedules notifications: %s' % str(ex), xbmc.LOGDEBUG)