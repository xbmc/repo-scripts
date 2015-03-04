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

from __future__ import unicode_literals

import os
import sys
import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon


def main():
    addon = xbmcaddon.Addon()
    path = sys.listitem.getVideoInfoTag().getPath().decode('utf-8', 'ignore')
    if not path:
        return
    path = os.path.join(path, addon.getSetting('extras-folder').decode('utf-8'))
    xbmc.log(b"[%s] opening '%s'" % (addon.getAddonInfo('id'), path.encode('utf-8')), xbmc.LOGDEBUG)
    if xbmcvfs.exists((path + '/').encode('utf-8')):
        xbmc.executebuiltin('Container.Update(\"%s\")' % path)
    else:
        dialog = xbmcgui.Dialog()
        dialog.ok(addon.getAddonInfo('name'), "No extras found")

if __name__ == '__main__':
    main()
