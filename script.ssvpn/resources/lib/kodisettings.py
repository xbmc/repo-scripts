#/*
# *
# * OpenVPN for Kodi.
# *
# * Copyright (C) 2018 Venus
# *
# * This program is free software: you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation, either version 3 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program.  If not, see <http://www.gnu.org/licenses/>.
# *
# */

import xbmcaddon
import xbmc

class KodiSettings:
    def __init__(self):
        addonid = 'script.ssvpn'
        self.__addon__ = xbmcaddon.Addon(id=addonid)
        # self.__argv__ = argv
        self.__id__ = self.__addon__.getAddonInfo('id')
        self.__datapath__ = 'special://profile/addon_data/%s' % (self.__id__)
        self.__name__ = self.__addon__.getAddonInfo('name')
        self.__path__ = self.__addon__.getAddonInfo('path')
        self.__version__ = self.__addon__.getAddonInfo('version')

    def __getitem__(self, key):
        value = self.__addon__.getSetting(key)
        if value.isdigit():
            return int(value)
        else:
            return value

    def __setitem__(self, key, value):
        self.__addon__.setSetting(key, value)

    def get_string(self, id):
        return self.__addon__.getLocalizedString(id)

    # def get_argv(self, idx):
    #     return self.__argv__[idx]

    # def get_argc(self):
    #     return len(self.__argv__)

    def get_datapath(self, path=''):
        return xbmc.translatePath('%s/%s' % (self.__datapath__, path))

    def get_name(self):
        return self.__name__

    def get_path(self, path=''):
        return xbmc.translatePath('%s/%s' % (self.__path__, path))

    def get_version(self):
        return self.__version__

    def open(self):
        self.__addon__.openSettings()
