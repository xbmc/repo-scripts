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
import sys
import xbmc
import xbmcgui
import xbmcaddon
from urllib import urlencode


def main():
    addon = xbmcaddon.Addon()
    item_path = sys.listitem.getVideoInfoTag().getPath()
    if not item_path:
        return

    extras_dir = os.path.join(item_path, addon.getSetting('extras-folder'))
    xbmc.log("[%s] opening '%s'" % (addon.getAddonInfo('id'), extras_dir), xbmc.LOGDEBUG)

    params = {
        'path': extras_dir,
        'isroot': 'true',
        'title': sys.listitem.getLabel(),
        'fanart': sys.listitem.getProperty('fanart_image'),
    }
    plugin_url = "plugin://context.item.extras/browse?" + urlencode(params)

    if xbmcgui.getCurrentWindowId() == 10025:
        xbmc.executebuiltin('Container.Update(\"%s\")' % plugin_url)
    else:
        xbmc.executebuiltin('ActivateWindow(Video, \"%s\", return)' % plugin_url)


if __name__ == '__main__':
    main()
