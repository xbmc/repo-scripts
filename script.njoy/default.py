# -*- coding: utf-8 -*- 

import os
import sys
import xbmc
import xbmcaddon

__author__     = "amet"
__scriptid__   = "script.njoy"
__scriptname__ = "Njoy Live TV"

__addon__      = xbmcaddon.Addon()

__cwd__        = __addon__.getAddonInfo('path')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') )
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )

sys.path.append (__resource__)

import gui

if ( __name__ == "__main__" ):
  ui = gui.GUI( "script-njoy-main.xml" , __cwd__ , "Default")
  ui.doModal()
  del ui
