# -*- coding: utf-8 -*- 

import os
import sys
import xbmc
import xbmcaddon

__author__     = "amet,mr_blobby"
__scriptid__   = "script.xbmc.subtitles"
__scriptname__ = "XBMC Subtitles"

__addon__      = xbmcaddon.Addon(id='script.xbmc.subtitles')

__cwd__        = __addon__.getAddonInfo('path').decode("utf-8")
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")

sys.path.append (__resource__)

import gui
from utilities import log, pause, unpause, UserNotificationNotifier

log( __name__ ,"Version: %s" % __version__)

if ( __name__ == "__main__" ):
  __unpause__ = False
  ui = gui.GUI( "script-XBMC-Subtitles-main.xml" , __cwd__ , "Default")
  movieFullPath = ui.set_allparam()
  if (__addon__.getSetting( "auto_download" ) == "true") and (__addon__.getSetting( "auto_download_file" ) != os.path.basename( movieFullPath )):
    notification = UserNotificationNotifier(__scriptname__, __language__(764).encode('utf-8'), 2000)    
    if not ui.Search_Subtitles(False):
      __unpause__ = pause()
      ui.doModal()
    else:
      notification.close(__language__(765).encode('utf-8'), 1000) 
  else:
    __unpause__ = pause() 
    ui.doModal()
        
  del ui
  if __unpause__:
    unpause()
  sys.modules.clear()


  
