#
#  MythBox for XBMC - http://mythbox.googlecode.com
#  Copyright (C) 2011 analogue@yahoo.com
# 
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
import logging
import os
import urllib
import urllib2

from mythbox.util import run_async

log = logging.getLogger('mythbox.core')

URL_MYTHBOX_UPDATE = 'http://mythbox-xbmc.dyndns.org/updates'
URL_MYTHBOX_DOWNLOAD_COUNTER = 'http://mythbox.googlecode.com/files/download_counter.txt'

class UpdateChecker(object):
    
    def __init__(self, platform, updateUrl=URL_MYTHBOX_UPDATE):
        self.platform = platform
        self.updateUrl = updateUrl
   
    @run_async
    def run(self):
        try:
            response = urllib2.urlopen('%s_%s_%s.xml' % (self.updateUrl, self.platform.addonVersion(), self.platform.getName()), None)
        except:
            pass
        
        # poke download counter one and only once
        try:
            fname = os.path.join(self.platform.getCacheDir(), 'mythbox-' + self.platform.addonVersion())
            if not os.path.exists(fname):
                filename, headers = urllib.urlretrieve(URL_MYTHBOX_DOWNLOAD_COUNTER, fname)
        except:
            pass
