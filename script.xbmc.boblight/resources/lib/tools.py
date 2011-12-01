'''
    Boblight for XBMC
    Copyright (C) 2011 Team XBMC

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

import platform
import xbmc
import xbmcgui
import sys
import os
import re
import urllib
import urllib2

__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__settings__ = sys.modules[ "__main__" ].__settings__
__cwd__ = sys.modules[ "__main__" ].__cwd__
__icon__ = sys.modules[ "__main__" ].__icon__

__libbaseurl__ = sys.modules[ "__main__" ].__libbaseurl__
__libnameosx__ = sys.modules[ "__main__" ].__libnameosx__
__libnameios__ = sys.modules[ "__main__" ].__libnameios__
__libnamewin__ = sys.modules[ "__main__" ].__libnamewin__

def DownloaderClass(url,dest):
    dp = xbmcgui.DialogProgress()
    dp.create(__scriptname__,"Downloading File",url)
    urllib.urlretrieve(url,dest,lambda nb, bs, fs, url=url: _pbhook(nb,bs,fs,url,dp))
 
def _pbhook(numblocks, blocksize, filesize, url=None,dp=None):
    try:
        percent = min((numblocks*blocksize*100)/filesize, 100)
        dp.update(percent)
    except:
        percent = 100
        dp.update(percent)
        print "boblight: DOWNLOAD FAILED" # need to get this part working        
    if dp.iscanceled(): 
        print "boblight: DOWNLOAD CANCELLED" # need to get this part working
        dp.close()
 
def tools_downloadLibBoblight():
  print "boblight: try to fetch libboblight"  
  url = "none"
  dest = "none"
  destdir = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib') )
  if xbmc.getCondVisibility('system.platform.osx'):
    url = xbmc.translatePath( os.path.join( __libbaseurl__, 'osx', __libnameosx__) ) + ".zip"
    dest = os.path.join( destdir, __libnameosx__) 
    DownloaderClass(url, dest + ".zip")
  elif  xbmc.getCondVisibility('system.platform.ios'):
    url = xbmc.translatePath( os.path.join( __libbaseurl__, 'ios', __libnameios__) ) + ".zip"
    dest = os.path.join( destdir, __libnameios__)
    DownloaderClass(url, dest + ".zip")
  elif xbmc.getCondVisibility('system.platform.windows'): 
    url = xbmc.translatePath( os.path.join( __libbaseurl__, 'win32', __libnamewin__) ) + ".zip"
    dest = os.path.join( destdir, __libnamewin__)
    DownloaderClass(url, dest + ".zip")
  print "boblight: " + url + " -> " + dest
  xbmc.executebuiltin('XBMC.Extract("%s","%s")' % (dest + ".zip", destdir), True)
  os.remove(dest + ".zip")
