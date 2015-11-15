# -*- coding: utf-8 -*-
'''
    screensaver.atv4
    Copyright (C) 2015 enen92

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import sys
import xbmc
import json
from resources.lib import playlist


if __name__ == '__main__':
    try: screensavertime = int(json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"screensaver.time"},"id":4}'))["result"]["value"])
    except : screensavertime = 60

    if not xbmc.getCondVisibility('Player.HasMedia') and xbmc.getGlobalIdleTime() > screensavertime:
        xbmc.log(msg='ATV4 Screensaver called and player has no media. Started', level=xbmc.LOGDEBUG)
    	atvPlaylist = playlist.AtvPlaylist()
    	playlist = atvPlaylist.getPlaylist()
    	if playlist:
            xbmc.Player().play(playlist)
    else:
        xbmc.log(msg="ATV4 Screensaver called but media is playing. Ignoring call.", level=xbmc.LOGDEBUG)
        sys.exit(0)
