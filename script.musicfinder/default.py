#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#    This script is a modification of service.skin.widgets and service.library.data.provider
#    Thanks to the original authors: BigNoid, Unfledged and Martijn.

import os
import sys
import xbmc
import xbmcgui
import xbmcaddon

try:
    import simplejson as json
except Exception:
    import json

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')
__localize__     = __addon__.getLocalizedString

class Main:
    def __init__(self):
        params = self.getParams()
        if params:
            action = params.get("ACTION","").upper()
            listid = params.get("LISTID","")
            if action == "ARTIST":
                #get the DBID for this artist
                data = getJson(method="AudioLibrary.GetAlbums",params={"filter":{"artist":params.get("TITLE","")},"properties": ["artistid"], "limits": {"end": 1}})
                if data.has_key('result') and data['result'].has_key('albums'):
                    artistID = data["result"]["albums"][0]["artistid"][0]
                    xbmc.executebuiltin("activatewindow(Music,musicdb://artists/%s)" % artistID)
                    xbmc.executebuiltin("Control.SetFocus(%s)" % int(listid))
                else:
                    xbmc.executebuiltin("Notification(%s,%s)" % (__localize__(32000),__localize__(32001)))
            if action == "ALBUM":
                #get the DBID for this album
                data = getJson(method="AudioLibrary.GetSongs",params={"filter":{"album":params.get("TITLE","")},"properties": ["albumid"], "limits": {"end": 1}})
                if data.has_key('result') and data['result'].has_key('songs'):
                    albumID = data["result"]["songs"][0]["albumid"]
                    xbmc.executebuiltin("activatewindow(Music,musicdb://albums/%s)" % albumID)
                    xbmc.executebuiltin("Control.SetFocus(%s)" % listid)
                else:
                    xbmc.executebuiltin("Notification(%s,%s)" % (__localize__(32000),__localize__(32002)))

    def getParams(self):
        #extract the params from the called script path
        params = {}
        for arg in sys.argv:
            if arg == 'script.musicfinder' or arg == 'default.py':
                continue
            arg = arg.replace('"', '').replace("'", " ").replace("?", "")
            if "=" in arg:
                paramname = arg.split('=')[0].upper()
                paramvalue = arg.split('=')[1]
                params[paramname] = paramvalue
        return params

def getJson(method, params):
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "%s", "params": %s, "id": 1}' % (method, json.dumps(params)))
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    return json.loads(json_query)


Main()