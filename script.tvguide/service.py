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
import addon
import notification
import xbmc
import clear_cache

if addon.SETTINGS['cache.data.on.xbmc.startup'] == 'true':
    try:
        if addon.SETTINGS['clear.cache.on.xbmc.startup'] == 'true':
            clear_cache.clear_cache()
        addon.SOURCE.updateChannelAndProgramListCaches()
    except Exception:
        xbmc.log('[script.tvguide] Unable to update caches!', xbmc.LOGDEBUG)

if addon.SETTINGS['notifications.enabled'] == 'true':
    try:
        n = notification.Notification(addon.SOURCE, addon.ADDON.getAddonInfo('path'),
            xbmc.translatePath(addon.ADDON.getAddonInfo('profile')))
        n.scheduleNotifications()
    except Exception:
        xbmc.log('[script.tvguide] Unable to schedules notifications!', xbmc.LOGDEBUG)