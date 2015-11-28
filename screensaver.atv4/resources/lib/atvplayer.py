# -*- coding: utf-8 -*-
'''
    screensaver.atv4
    Copyright (C) 2015 enen92

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
'''

import xbmc
import xbmcgui
import playlist

class ATVPlayer(xbmc.Player):
	def __init__(self,):
		xbmc.log(msg='ATV4 Screensaver player has been created', level=xbmc.LOGDEBUG)

	def onPlayBackStarted(self):
		xbmc.log(msg='ATV4 Screensaver player has started. Toggling repeatAll', level=xbmc.LOGDEBUG)
        xbmc.executebuiltin("PlayerControl(RepeatAll)")

	def onPlayBackStopped(self):
		xbmc.log(msg='ATV4 Screensaver player has been stopped', level=xbmc.LOGDEBUG)
		return
