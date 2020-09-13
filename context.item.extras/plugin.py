# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
from kodi_six import xbmc, xbmcvfs, xbmcaddon, xbmcplugin
from kodi_six.xbmcgui import Dialog, ListItem
from kodi_six.utils import py2_encode, py2_decode
import routing
try:
    from urllib import urlencode, quote_plus
except ImportError:
    from urllib.parse import urlencode, quote_plus
    

plugin = routing.Plugin()


@plugin.route("/")
def browse():
    args = plugin.args

    if 'path' not in args:
        # back navigation workaround: just silently fail and we'll
        # eventually end outside the plugin dir
        xbmcplugin.endOfDirectory(plugin.handle, succeeded=False)
        return

    current_path = py2_decode(args['path'][0].decode('base64'))
    if not current_path.endswith('/'):
        current_path += '/'

    dirs = []
    files = []
    if xbmcvfs.exists(current_path):
        dirs, files = xbmcvfs.listdir(current_path)

    for name in dirs:
        li = ListItem(name)
        params = {
            b'path': path,
            b'title': args['title'][0],
        }
        if 'fanart' in args:
            li.setArt({'fanart': args['fanart'][0]})
            params.update({b'fanart':args['fanart'][0]})
        path = os.path.join(current_path, name)
        url = 'plugin://context.item.extras/?' + urlencode(params)
        xbmcplugin.addDirectoryItem(plugin.handle, url, li, isFolder=True)

    for name in files:
        li = ListItem(name)
        if 'fanart' in args:
            li.setArt({'fanart': args['fanart'][0]})
        url = os.path.join(current_path, py2_decode(name))
        xbmcplugin.addDirectoryItem(plugin.handle, url, li, isFolder=False)

    if 'isroot' in args:
        li = ListItem("Search on Youtube")
        li.setProperty("specialsort", "bottom")
        url = plugin.url_for(youtube, q=args['title'][0].decode('base64') + ' Extras') 
        # xbmcplugin.addDirectoryItem(plugin.handle, url, li, isFolder=True)

    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/youtube")
def youtube():
    query = plugin.args['q'][0]
    kb = xbmc.Keyboard(query, 'Search')
    kb.doModal()
    if kb.isConfirmed():
        edited_query = kb.getText()
        if edited_query:
            url = "plugin://plugin.video.youtube/kodion/search/query/?q=" + \
                  quote_plus(edited_query)
            xbmc.executebuiltin('Container.Update(\"%s\")' % url)


if __name__ == '__main__':
    plugin.run()
