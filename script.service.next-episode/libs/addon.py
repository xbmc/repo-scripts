# (c) Roman Miroshnychenko, 2023
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os

from xbmc import getInfoLabel
from xbmcaddon import Addon
from xbmcvfs import translatePath


ADDON = Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_PATH = translatePath(ADDON.getAddonInfo('path'))
ICON = os.path.join(ADDON_PATH, 'icon.png')
KODI_VERSION = getInfoLabel('System.BuildVersion')[:2]
