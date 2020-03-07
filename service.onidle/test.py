#   Copyright (C) 2020 Lunatixz
#
#
# This file is part of OnIdle
#
# OnIdle is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OnIdle is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OnIdle.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcaddon

# Plugin Info
ADDON_ID            = 'service.onidle'
REAL_SETTINGS       = xbmcaddon.Addon(id=ADDON_ID)
USER_DEFINED_ACTION = REAL_SETTINGS.getSetting('User_Action')
USER_EXIT_ACTION    = {0:'ActivateScreensaver',
                       1:'Quit',
                       2:'ShutDown',
                       3:'Suspend',
                       4:'Hibernate',
                       5:'CECStandby',
                       6:'CECToggleState',
                       7:USER_DEFINED_ACTION}[int(REAL_SETTINGS.getSetting('User_Exit_Action') or '0')]
                       # https://kodi.wiki/view/List_of_built-in_functions
xbmc.executebuiltin(USER_EXIT_ACTION)
REAL_SETTINGS.openSettings() 