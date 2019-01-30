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

import xbmcgui
import xbmc
import sys
import os
import subprocess
import json

from resources.lib import apputils
from resources.lib import kodisettings
from resources.lib import kodiutils
from resources.lib import selectservers
from resources.lib import loading
from resources.lib import dashboard

# Initialise settings.
settings = kodisettings.KodiSettings()

# Get addon information.
addonname = settings.get_name()
version = settings.get_version()

# initialize serverlist and serverid
dashboard.serverInfoInit()

apputils.log_debug('Addon Name: [%s]' % (addonname))
apputils.log_debug('Version:    [%s]' % (version))

# input email, password
if (__name__ == '__main__'):
	sudo = (settings['sudo'] == 'true')
	sudopassword = settings['sudopassword']
	sudo_require = (settings['sudo_require'] == 'true')
	if sudo:
		if sudopassword == "" or sudo_require:
			sudopassword = xbmcgui.Dialog().input("Root User Password", "")
			settings.__setitem__("sudopassword", sudopassword)

			sudopassword = settings['sudopassword']

	if os.path.isfile(settings['openvpn']):
		loading.show_loading(connected=True, action="login")
	else:
		loading.show_loading(connected=True, action="preinstall")
