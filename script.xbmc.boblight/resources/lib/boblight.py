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

"""

cheat sheet

c_void_p(g_libboblight.boblight_init())
g_libboblight.boblight_destroy(boblight)
c_int(g_libboblight.boblight_connect(boblight, const char* address, int port, int usectimeout))
c_int(g_libboblight.boblight_setpriority(boblight, int priority))
c_char_p(g_libboblight.boblight_geterror(boblight))
c_int(g_libboblight.boblight_getnrlights(boblight))
c_char_p(g_libboblight.boblight_getlightname(boblight, int lightnr))
c_int(g_libboblight.boblight_getnroptions(boblight))
c_char_p(g_libboblight.boblight_getoptiondescriptboblight, int option))
c_int(g_libboblight.boblight_setoption(boblight, int lightnr, const char* option))
c_int(g_libboblight.boblight_getoption(boblight, int lightnr, const char* option, const char** output))
g_libboblight.boblight_setscanrange(boblight, int width, int height)
c_int(g_libboblight.boblight_addpixel(boblight, int lightnr, int* rgb))
g_libboblight.boblight_addpixelxy(boblight, int x, int y, int* rgb)
c_int(g_libboblight.boblight_sendrgb(boblight, int sync, int* outputused))
c_int(g_libboblight.boblight_ping(boblight, int* outputused))

"""
import platform
import xbmc
import sys
import os

__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__settings__ = sys.modules[ "__main__" ].__settings__
__cwd__ = sys.modules[ "__main__" ].__cwd__
__icon__ = sys.modules[ "__main__" ].__icon__

__libbaseurl__ = sys.modules[ "__main__" ].__libbaseurl__
__libnameosx__ = sys.modules[ "__main__" ].__libnameosx__
__libnameios__ = sys.modules[ "__main__" ].__libnameios__
__libnamewin__ = sys.modules[ "__main__" ].__libnamewin__

global g_boblightLoaded
global g_bobHandle
global g_current_priority
global g_libboblight
global g_connected

try:
  from ctypes import *
  HAVE_CTYPES = True
except:
  HAVE_CTYPES = False

def bob_loadLibBoblight():
  global g_boblightLoaded
  global g_current_priority
  global g_libboblight  
  global g_bobHandle
  global g_connected

  g_connected = False
  g_current_priority = -1
  ret = 0

  if HAVE_CTYPES:
    libname = "libboblight.so" #default to linux type
    # load g_libboblight.so/dylib
    try:
      if xbmc.getCondVisibility('system.platform.osx'):
        libname = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib', __libnameosx__) )
        if not os.path.exists(libname):
          ret = 1
        else:
          cdll.LoadLibrary(libname)
          g_libboblight = CDLL(libname)
      elif  xbmc.getCondVisibility('system.platform.ios'):
        libname = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib', __libnameios__) )
        if not os.path.exists(libname):
          ret = 1
        else:
          cdll.LoadLibrary(libname)
          g_libboblight = CDLL(libname)
      elif xbmc.getCondVisibility('system.platform.windows'): 
        libname = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib', __libnamewin__) )
        if not os.path.exists(libname):
          ret = 1
        else:
          cdll.LoadLibrary(libname)
          g_libboblight = CDLL(libname)
      else:
        cdll.LoadLibrary("libboblight.so")
        g_libboblight = CDLL("libboblight.so")
      g_libboblight.boblight_init.restype = c_void_p
      g_libboblight.boblight_geterror.restype = c_char_p
      g_libboblight.boblight_getlightname.restype = c_char_p
      g_libboblight.boblight_getoptiondescript.restype = c_char_p
      g_boblightLoaded = True
      g_bobHandle = c_void_p(g_libboblight.boblight_init(None))
    except:
      g_boblightLoaded = False
      print "boblight: Error loading " + libname + " - only demo mode."
      ret = 1
  else:
    print "boblight: No ctypes available - only demo mode."
    ret = 2
    g_boblightLoaded = False
  return ret

def bob_set_priority(priority):
  global g_current_priority
  
  ret = True
  if g_boblightLoaded and g_connected:
    if priority != g_current_priority:
      g_current_priority = priority
      if not g_libboblight.boblight_setpriority(g_bobHandle, g_current_priority):
        print "boblight: error setting priority: " + c_char_p(g_libboblight.boblight_geterror(g_bobHandle)).value
        ret = False
  return ret
  
def bob_setscanrange(width, height):
  if g_boblightLoaded and g_connected:
    g_libboblight.boblight_setscanrange(g_bobHandle, width, height)
  
def bob_addpixelxy(x,y,rgb):
  if g_boblightLoaded and g_connected:
    g_libboblight.boblight_addpixelxy(g_bobHandle, x, y, rgb)

def bob_addpixel(rgb):
  if g_boblightLoaded and g_connected:
    g_libboblight.boblight_addpixel(g_bobHandle, -1, rgb)

def bob_sendrgb():
  ret = False
  if g_boblightLoaded and g_connected:
    ret = c_int(g_libboblight.boblight_sendrgb(g_bobHandle, 1, None))  != 0
  else:
    ret = True
  return ret
  
def bob_setoption(option):
  ret = False
  if g_boblightLoaded and g_connected:
    ret = c_int(g_libboblight.boblight_setoption(g_bobHandle, -1, option))  != 0
  else:
    ret = True
  return ret
  
def bob_getnrlights():
  if HAVE_CTYPES:
    ret = c_int(0)
    if g_boblightLoaded and g_connected:
      ret = c_int(g_libboblight.boblight_getnrlights(g_bobHandle))
    return ret.value
  else:
    return 0
  
def bob_getlightname(nr):
  ret = ""
  if g_boblightLoaded and g_connected:
    ret = g_libboblight.boblight_getlightname(g_bobHandle,nr)
  return ret

def bob_connect(hostip, hostport):
  global g_connected
  
  if g_boblightLoaded:
    ret = c_int(g_libboblight.boblight_connect(g_bobHandle, hostip, hostport, 1000000))
    g_connected = ret.value != 0
  else:
    g_connected = False
  return g_connected
  
def bob_set_static_color(rgb):
  if g_boblightLoaded and g_connected:
    bob_addpixel(rgb)
    bob_sendrgb()

def bob_destroy():
  if g_boblightLoaded:
    g_libboblight.boblight_destroy(g_bobHandle)

def bob_geterror():
  ret = ""
  if g_boblightLoaded:
    ret = c_char_p(g_libboblight.boblight_geterror(g_bobHandle)).value
  return ret
