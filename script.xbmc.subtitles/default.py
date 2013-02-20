# -*- coding: utf-8 -*- 

import os
import sys
import xbmc
import xbmcaddon

__addon__      = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath( __addon__.getAddonInfo('path') ).decode("utf-8")
__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")

sys.path.append (__resource__)

import gui
from utilities import Pause

if xbmc.Player().isPlayingVideo():
  pause = Pause()
  ui = gui.GUI( "script-XBMC-Subtitles-main.xml" , __cwd__ , "Default")
  if (not ui.set_allparam() or not ui.Search_Subtitles(False)):
    if __addon__.getSetting("pause") == "true":
      pause.pause()
    ui.doModal()
        
  del ui
  pause.restore()
  sys.modules.clear()
else:
  xbmc.executebuiltin((u'Notification(%s,%s,%s)' %(__scriptname__, __language__(611), "1000")).encode("utf-8")) 


  
