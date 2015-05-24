# -*- coding: utf-8 -*- 
'''
	REvoluzzer for KODI
	Copyright (C) 2015 icordforum.com

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

import sys

__addon__  = sys.modules[ "__main__" ].__addon__

class settings():
	def __init__( self, *args, **kwargs ):
		self.interval = 30
		self.hosts = []
		self.start()
     
	def start(self):
		self.interval = __addon__.getSetting('interval')
		for count in range(0,2):
			self.hosts.append([__addon__.getSetting('interval%s') % count, 0, 0.])