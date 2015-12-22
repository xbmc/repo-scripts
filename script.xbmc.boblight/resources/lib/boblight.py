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

"""

cheat sheet

c_void_p(self.libboblight.boblight_init())
self.libboblight.boblight_destroy(boblight)
c_int(self.libboblight.boblight_connect(boblight, const char* address, int port, int usectimeout))
c_int(self.libboblight.boblight_setpriority(boblight, int priority))
c_char_p(self.libboblight.boblight_geterror(boblight))
c_int(self.libboblight.boblight_getnrlights(boblight))
c_char_p(self.libboblight.boblight_getlightname(boblight, int lightnr))
c_int(self.libboblight.boblight_getnroptions(boblight))
c_char_p(self.libboblight.boblight_getoptiondescriptboblight, int option))
c_int(self.libboblight.boblight_setoption(boblight, int lightnr, const char* option))
c_int(self.libboblight.boblight_getoption(boblight, int lightnr, const char* option, const char** output))
self.libboblight.boblight_setscanrange(boblight, int width, int height)
c_int(self.libboblight.boblight_addpixel(boblight, int lightnr, int* rgb))
self.libboblight.boblight_addpixelxy(boblight, int x, int y, int* rgb)
c_int(self.libboblight.boblight_sendrgb(boblight, int sync, int* outputused))
c_int(self.libboblight.boblight_ping(boblight, int* outputused))

"""
import sys
import os

try:
  from ctypes import *
  HAVE_CTYPES = True
except:
  HAVE_CTYPES = False

class Boblight():
  def __init__( self, *args, **kwargs ):
    self.current_priority = -1
    self.libboblight      = None
    self.bobHandle        = None
    self.connected        = False
    self.boblightLoaded   = False

  def bob_loadLibBoblight(self,libname,platform):
    ret = 0
    if HAVE_CTYPES:
      try:
        if not os.path.exists(libname) and platform != "linux":
          ret = 1
        else:
          self.libboblight = CDLL(libname)
          self.libboblight.boblight_init.restype = c_void_p
          self.libboblight.boblight_geterror.restype = c_char_p
          self.libboblight.boblight_getlightname.restype = c_char_p
          self.libboblight.boblight_getoptiondescript.restype = c_char_p
          self.boblightLoaded = True
          self.bobHandle = c_void_p(self.libboblight.boblight_init(None))
          
      except:
        ret = 1
    else:
      ret = 2
    return ret
  
  def bob_set_priority(self,priority):   
    ret = True
    if self.boblightLoaded and self.connected:
      if priority != self.current_priority:
        self.current_priority = priority
        if not self.libboblight.boblight_setpriority(self.bobHandle, self.current_priority):
          ret = False
    return ret
    
  def bob_setscanrange(self,width, height):
    if self.boblightLoaded and self.connected:
      self.libboblight.boblight_setscanrange(self.bobHandle, width, height)
    
  def bob_addpixelxy(self,x,y,rgb):
    if self.boblightLoaded and self.connected:
      self.libboblight.boblight_addpixelxy(self.bobHandle, x, y, rgb)
  
  def bob_addpixel(self,rgb):
    if self.boblightLoaded and self.connected:
      self.libboblight.boblight_addpixel(self.bobHandle, -1, rgb)
  
  def bob_sendrgb(self):
    ret = False
    if self.boblightLoaded and self.connected:
      ret = c_int(self.libboblight.boblight_sendrgb(self.bobHandle, 1, None))  != 0
    return ret
    
  def bob_setoption(self,option):
    ret = False
    if self.boblightLoaded and self.connected:
      ret = c_int(self.libboblight.boblight_setoption(self.bobHandle, -1, option))  != 0
    else:
      ret = True
    return ret
    
  def bob_getnrlights(self):
    if HAVE_CTYPES:
      ret = c_int(0)
      if self.boblightLoaded and self.connected:
        ret = c_int(self.libboblight.boblight_getnrlights(self.bobHandle))
      return ret.value
    else:
      return 0
    
  def bob_getlightname(self,nr):
    ret = ""
    if self.boblightLoaded and self.connected:
      ret = self.libboblight.boblight_getlightname(self.bobHandle,nr)
    return ret
  
  def bob_connect(self,hostip, hostport):    
    if self.boblightLoaded:
      ret = c_int(self.libboblight.boblight_connect(self.bobHandle, hostip, hostport, 1000000))
      self.connected = ret.value != 0
    else:
      self.connected = False
    return self.connected
    
  def bob_set_static_color(self,rgb):
    res = False
    if self.boblightLoaded and self.connected:
      self.bob_addpixel(rgb)
      res = self.bob_sendrgb()
    return res  
  
  def bob_destroy(self):
    if self.boblightLoaded:
      self.libboblight.boblight_destroy(self.bobHandle)
      self.boblightLoaded = False
  
  def bob_geterror(self):
    ret = ""
    if self.boblightLoaded:
      ret = c_char_p(self.libboblight.boblight_geterror(self.bobHandle)).value
    return ret
  
  def bob_ping(self):
    ret = False
    if self.boblightLoaded and self.connected:
      ret = c_int(self.libboblight.boblight_ping(self.bobHandle, None)).value == 1
    return ret
