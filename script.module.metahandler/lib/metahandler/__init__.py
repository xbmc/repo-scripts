#    metahandler XBMC Addon
#    Copyright (C) 2012 Eldorado
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
This module provides a small front API for accessing some of the basic metahandler features.

You will likely want to use directly the metahandlers.MetaData() class for the majority of functions.

eg.
    from metahandler import metahandlers
    mh=metahandlers.MetaData()
     
'''

import common
common.addon.log('Initializing MetaHandlers version: %s' % common.addon_version)

def display_settings():
    '''
    Opens the settings dialog for :mod:`metahandler`.
    
    This can be called from your addon to provide access to global 
    :mod:`metahandler` settings. 
    
    .. note::
    
        All changes made to these setting by the user are global and will 
        affect any addon that uses :mod:`metahandler`.
    '''
    common.addon.show_settings()
