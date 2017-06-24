# -*- coding: utf-8 -*- 
'''
    Boblight for Kodi
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
import platform

__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__icon__       = sys.modules[ "__main__" ].__icon__
__language__   = sys.modules[ "__main__" ].__language__

__libbasepath__  = xbmc.translatePath(os.path.join(__cwd__,'resources','lib','%s') )
__libbaseurl__   = "http://mirrors.kodi.tv/build-deps/addon-deps/binaries/libboblight"

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
 
def tools_downloadLibBoblight(platformstr,allowNotify):
  log("boblight: try to fetch libboblight")
  libname = get_libname(platformstr)
  destdir = get_download_path(platformstr)
  url = "%s/%s/%s.zip" % (__libbaseurl__, platformstr, libname)
  dest = os.path.join( destdir, libname)
  try:
    DownloaderClass(url, dest + ".zip")
    log("%s -> %s" % (url, dest))
    xbmc.executebuiltin('XBMC.Extract("%s.zip","%s")' % (dest, destdir), True)
    os.remove(dest + ".zip")
  except:
    if allowNotify:
      text = __language__(32510)
      xbmc.executebuiltin("XBMC.Notification(%s,%s,%s,%s)" % (__scriptname__,text,750,__icon__))

def log(msg):
  xbmc.log("### [%s] - %s" % (__scriptname__,msg,),level=xbmc.LOGDEBUG )
  
def get_platform():
  if xbmc.getCondVisibility('system.platform.osx'):
    platformstr = "osx"
  elif xbmc.getCondVisibility('system.platform.windows'):
    if platform.machine().endswith('64'):
      platformstr = "win64"
    else:
      platformstr = "win32"
  elif  xbmc.getCondVisibility('system.platform.ios'):
    platformstr = "ios"
  elif  xbmc.getCondVisibility('system.platform.tvos'):
    platformstr = "tvos"
  elif  xbmc.getCondVisibility('system.platform.android'):
    if os.uname()[4].startswith("arm") or os.uname()[4].startswith("aarch64"):
      platformstr = "android"
    else:
      platformstr = "androidx86"
  else:
    platformstr = "linux"
  return platformstr 
  
def get_libname(platformstr):
  if platformstr == "osx":
    return "libboblight-osx.0.dylib"
  elif platformstr == "ios":
    return "libboblight-ios.0.dylib"
  elif platformstr == "tvos":
    return "libboblight-tvos.0.dylib"
  elif platformstr == "win32":
    return "libboblight-win32.0.dll"
  elif platformstr == "win64":
    return "libboblight-win64.0.dll"
  elif platformstr == "android" or platformstr == "androidx86":
    return "libboblight.so"
  elif platformstr == "linux":
    return "libboblight.so"

def get_download_path(platformstr):
  if platformstr == "android" or platformstr == "androidx86":
    return "/data/data/org.xbmc.kodi/files/"
  else:
    return xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib') )

def get_libpath(platformstr):
  if platformstr == 'linux':
    return get_libname(platformstr)
  elif platformstr == 'android' or platformstr == 'androidx86':
    return "/data/data/org.xbmc.kodi/files/%s" % (get_libname(platformstr),)
  elif platformstr == 'tvos':
    return "%s/system/%s" % (xbmc.translatePath("special://xbmc"),get_libname(platformstr),)
  else:
    return __libbasepath__ % (get_libname(platformstr),)  
