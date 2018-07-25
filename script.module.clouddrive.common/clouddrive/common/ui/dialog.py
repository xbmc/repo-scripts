#-------------------------------------------------------------------------------
# Copyright (C) 2017 Carlos Guzman (cguZZman) carlosguzmang@protonmail.com
# 
# This file is part of Cloud Drive Common Module for Kodi
# 
# Cloud Drive Common Module for Kodi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Cloud Drive Common Module for Kodi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

import xbmcgui

class DialogProgressBG (xbmcgui.DialogProgressBG):
    _default_heading = None
    created = False
    
    def __init__(self, default_heading):
        self._default_heading = default_heading
                 
    def create(self, heading, message=None):
        if self.created:
            self.update(heading=heading, message=message)
        else:
            super(DialogProgressBG, self).create(heading, message)
            self.created = True
    
    def close(self):
        if self.created:
            super(DialogProgressBG, self).close()
            self.created = False
    
    def update(self, percent=0, heading=None, message=None):
        if not self.created:
            if not heading: heading = self._default_heading
            self.create(heading=heading, message=message)
        if percent < 0: percent = 0
        if percent > 100: percent = 100
        super(DialogProgressBG, self).update(percent=percent, heading=heading, message=message)
    
    def iscanceled(self):
        if self.created:
            return super(DialogProgress, self).iscanceled()
        return False 
    
class DialogProgress (xbmcgui.DialogProgress):
    _default_heading = None
    created = False
    
    def __init__(self, default_heading):
        self._default_heading = default_heading
        
    def create(self, heading, line1='', line2='', line3=''):
        if self.created:
            self.close()
            
        super(DialogProgress, self).create(heading, line1, line2, line3)
        self.created = True
    
    def close(self):
        if self.created:
            super(DialogProgress, self).close()
            self.created = False
    
    def update(self, percent, line1='', line2='', line3=''):
        if not self.created:
            self.create(self._default_heading, line1, line2, line3)
        if percent < 0: percent = 0
        if percent > 100: percent = 100
        super(DialogProgress, self).update(percent, line1, line2, line3)
        
    def iscanceled(self):
        if self.created:
            return super(DialogProgress, self).iscanceled()
        return False 
        
        
