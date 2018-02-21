"""
    metahandler XBMC Addon
    Copyright (C) 2012 Eldorado

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
"""

import os    
from addon.common.addon import Addon

addon = Addon('script.module.metahandler')
addon_path = addon.get_path()
profile_path = addon.get_profile()
settings_file = os.path.join(addon_path, 'resources', 'settings.xml')
addon_version = addon.get_version()
