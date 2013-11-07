'''
    universal XBMC module
    Copyright (C) 2013 the-one @ XUNITYTALK.COM

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
import xbmcgui
import xbmcplugin
import xbmcvfs
import socket
import xbmcaddon
import cookielib
import urllib2

settings = xbmcaddon.Addon(id='script.module.universal')
language = settings.getLocalizedString
version = "0.0.2"
plugin = "Universal-AnAddonsToolkit-" + version
core = ""
common = ""
downloader = ""
dbg = False
dbglevel = 3

from universal import watchhistory

print 'Universal - An Addons Toolkit: - watchhistory - -Auto Cleanup Start'
wh = watchhistory.WatchHistory('script.module.watchhistory')
wh.cleanup_history()
print 'Universal - An Addons Toolkit: - watchhistory - -Auto Cleanup End'
