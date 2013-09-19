'''
    MPRIS D-Bus Interface for XBMC (with Ubuntu sound-menu integration)
    Copyright (C) 2011-2013 Team XBMC
    
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
import gobject
from dbus.mainloop.glib import DBusGMainLoop

import xbmcmpris2

DBusGMainLoop(set_as_default=True)

service = xbmcmpris2.Service()
context = gobject.MainLoop().get_context()

while (not xbmc.abortRequested):
  context.iteration(False)
  xbmc.sleep(100)
