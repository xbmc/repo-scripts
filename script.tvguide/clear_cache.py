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
import os
import xbmc
import xbmcgui

from strings import *

def clear_cache():
    try:
        xbmc.log("Clearing TVGuide [script.tvguide] caches...", xbmc.LOGDEBUG)
        cachePath = xbmc.translatePath(xbmcaddon.Addon(id = 'script.tvguide').getAddonInfo('profile'))

        for file in os.listdir(cachePath):
            if file not in ['settings.xml', 'notification.db', 'source.db']:
                os.unlink(os.path.join(cachePath, file))

        xbmc.log("[script.tvguide] Caches cleared!", xbmc.LOGDEBUG)
        return True
    except Exception:
        xbmc.log('[script.tvguide] Caught exception while clearing cache!', xbmc.LOGDEBUG)
        return False


if __name__ == '__main__':
    if clear_cache():
        xbmcgui.Dialog().ok(strings(CLEAR_CACHE), strings(DONE))

