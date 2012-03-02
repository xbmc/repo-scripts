'''
    YouTube plugin for XBMC
    Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen

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
#import xbmc
#import xbmcplugin
#import xbmcaddon
#import xbmcgui
#try:
#    import xbmcvfs
#except ImportError:
#    import xbmcvfsdummy as xbmcvfs

# plugin constants
#version = "2.9.1"
plugin = "downloader"
#author = "TheCollective"
#url = "www.xbmc.com"

# xbmc hooks
#settings = xbmcaddon.Addon(id='plugin.video.youtube')
#language = settings.getLocalizedString
#dbg = settings.getSetting("debug") == "true"
#dbglevel = 3
dbg = True

if (__name__ == "__main__" ):
    if dbg:
        print plugin + " ARGV: " + repr(sys.argv)
    else:
        print plugin

#    try:
#        import StorageServer
#        cache = StorageServer.StorageServer("YouTube")
#    except:
#        import storageserverdummy as StorageServer
#        cache = StorageServer.StorageServer("YouTube")

