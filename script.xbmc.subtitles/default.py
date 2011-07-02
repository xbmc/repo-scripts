# -*- coding: utf-8 -*- 

import sys
import os
import xbmc
import xbmcaddon

__settings__   = xbmcaddon.Addon(id='script.xbmc.subtitles')
__language__   = __settings__.getLocalizedString
__version__    = __settings__.getAddonInfo('version')
__cwd__        = __settings__.getAddonInfo('path')
__profile__    = xbmc.translatePath( __settings__.getAddonInfo('profile') )
__scriptname__ = "XBMC Subtitles"
__scriptid__   = "script.xbmc.subtitles"
__author__     = "Amet,mr_blobby"

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
sys.path.append (BASE_RESOURCE_PATH)

from utilities import *

xbmc.output("### [%s] - Version: %s" % (__scriptname__,__version__,),level=xbmc.LOGDEBUG )

if ( __name__ == "__main__" ):
          
  import gui
  ui = gui.GUI( "script-XBMC-Subtitles-main.xml" , __cwd__ , "Default")
  movieFullPath = ui.set_allparam()
  if (__settings__.getSetting( "auto_download" ) == "true") and (__settings__.getSetting( "auto_download_file" ) != os.path.basename( movieFullPath )):
    notification = UserNotificationNotifier(__scriptname__, __language__(764), 2000)    
    if not ui.Search_Subtitles(False):
      if not xbmc.getCondVisibility('Player.Paused') : xbmc.Player().pause() #Pause if not paused
      ui.doModal()
    else:
      notification.close(__language__(765), 1000) 
  else:
    if not xbmc.getCondVisibility('Player.Paused') : xbmc.Player().pause() #Pause if not paused
    ui.doModal()
        
  del ui
  if xbmc.getCondVisibility('Player.Paused'): xbmc.Player().pause()      # if Paused, un-pause
  sys.modules.clear()


  
