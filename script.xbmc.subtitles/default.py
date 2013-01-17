# -*- coding: utf-8 -*- 

import os
import sys
import xbmc
import xbmcaddon

__addon__      = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__cwd__        = __addon__.getAddonInfo('path')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath( __addon__.getAddonInfo('path') ).decode("utf-8")
__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")

sys.path.append (__resource__)

import gui
from utilities import log, pause, unpause, UserNotificationNotifier

if ( __name__ == "__main__" ):
  __unpause__ = False
  ui = gui.GUI( "script-XBMC-Subtitles-main.xml" , __cwd__ , "Default")
  if (ui.set_allparam()):
    notification = UserNotificationNotifier(__scriptname__, __language__(764), 2000)    
    if not ui.Search_Subtitles(False):
      if __addon__.getSetting("pause") == "true":
        __unpause__ = pause()
      ui.doModal()
    else:
      notification.close(__language__(765), 1000) 
  else:
    if __addon__.getSetting("pause") == "true":
      __unpause__ = pause()
    ui.doModal()
        
  del ui
  if __unpause__:
    unpause()
  sys.modules.clear()


  
