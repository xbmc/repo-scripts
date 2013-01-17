# -*- coding: utf-8 -*- 
'''
    Boblight for XBMC
    Copyright (C) 2012 Team XBMC

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
import sys
import os
import urllib

__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__icon__       = sys.modules[ "__main__" ].__icon__
__language__   = sys.modules[ "__main__" ].__language__

__libbasepath__  = xbmc.translatePath(os.path.join(__cwd__,'resources','lib','%s') )
__libbaseurl__   = "http://mirrors.xbmc.org/build-deps/addon-deps/binaries/libboblight"

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
        log("boblight: DOWNLOAD FAILED") # need to get this part working        
    if dp.iscanceled(): 
        log("boblight: DOWNLOAD CANCELLED") # need to get this part working
    dp.close()
 
def tools_downloadLibBoblight(platform,allowNotify):
  log("boblight: try to fetch libboblight")
  libname = get_libname(platform)
  destdir = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib') )
  url = "%s/%s/%s.zip" % (__libbaseurl__, platform, libname)
  dest = os.path.join( destdir, libname)
  try:
    DownloaderClass(url, dest + ".zip")
    log("%s -> %s" % (url, dest))
    xbmc.executebuiltin('XBMC.Extract("%s.zip","%s")' % (dest, destdir), True)
    os.remove(dest + ".zip")
  except:
    if allowNotify:
      text = __language__(510)
      xbmc.executebuiltin("XBMC.Notification(%s,%s,%s,%s)" % (__scriptname__,text,750,__icon__))

def log(msg):
  xbmc.log("### [%s] - %s" % (__scriptname__,msg,),level=xbmc.LOGDEBUG )
  
def get_platform():
  if xbmc.getCondVisibility('system.platform.osx'):
    platform = "osx"
  elif xbmc.getCondVisibility('system.platform.windows'):
    platform = "win32"
  elif  xbmc.getCondVisibility('system.platform.ios'):
    platform = "ios"
  else:
    platform = "linux"
  return platform 
  
def get_libname(platform):
  if platform == "osx":
    return "libboblight-osx.0.dylib"
  elif platform == "ios":
    return "libboblight-ios.0.dylib"
  elif platform == "win32":
    return "libboblight-win32.0.dll"
  elif platform == "linux":
    return "libboblight.so"
  
def get_libpath(platform):
  if platform == 'linux':
    return get_libname(platform)
  else:
    return __libbasepath__ % (get_libname(platform),)  
