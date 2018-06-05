'''
    XBMC LCDproc addon
    Copyright (C) 2012-2018 Team Kodi

    resources/lib/common.py: Common defines and functionality used throughout
                             the whole addon
    Copyright (C) 2018 Daniel 'herrnst' Scheller

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os
import sys

import xbmc
import xbmcaddon

KODI_ADDON_ID       = "script.xbmc.lcdproc"
KODI_ADDON_NAME     = "XBMC LCDproc"
KODI_ADDON_SETTINGS = xbmcaddon.Addon(id=KODI_ADDON_ID)
KODI_ADDON_ROOTPATH = KODI_ADDON_SETTINGS.getAddonInfo("path")
KODI_ADDON_ICON     = os.path.join(KODI_ADDON_ROOTPATH, "resources", "icon.png")

# copy loglevel defines to the global scope
LOGDEBUG   = xbmc.LOGDEBUG
LOGERROR   = xbmc.LOGERROR
LOGFATAL   = xbmc.LOGFATAL
LOGINFO    = xbmc.LOGINFO
LOGNONE    = xbmc.LOGNONE
LOGNOTICE  = xbmc.LOGNOTICE
LOGSEVERE  = xbmc.LOGSEVERE
LOGWARNING = xbmc.LOGWARNING

# log wrapper
def log(loglevel, msg):
	xbmc.log("### [%s] - %s" % (KODI_ADDON_NAME, msg), level=loglevel)
