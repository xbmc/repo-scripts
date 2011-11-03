'''
    Cache service for XBMC
    Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen

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
    Version 0.8
'''
import platform
import xbmc
try: import xbmcvfs
except: import xbmcvfsdummy as xbmcvfs

dbg = False
dbglevel = 3

def run():
	s = StorageServer.StorageServer()
	print " StorageServer Module loaded RUN"
	print s.plugin + " Starting server"
	s.run()
	return True

if __name__ == "__main__":
	# ARM should run in instance mode, not as a service.
	if not xbmc.getCondVisibility('system.platform.ios'):
		import StorageServer
		run()
