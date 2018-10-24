#   Copyright (C) 2018 Lunatixz, Anisan
#
#
# This file is part of Flip Clock.
#
# Flip Clock is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Flip Clock is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Flip Clock.  If not, see <http://www.gnu.org/licenses/>.

import gui
import xbmcaddon

# Plugin Info
ADDON_ID       = 'screensaver.flipclock'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))

if __name__ == '__main__':
    ui = gui.GUI("default.xml", ADDON_PATH, "default")
    ui.doModal()