import sys
import os
import xbmc
import xbmcaddon

__settings__   = xbmcaddon.Addon(id='script.xbmc.subtitles')
__language__   = __settings__.getLocalizedString
__version__    = __settings__.getAddonInfo('version')
__cwd__        = __settings__.getAddonInfo('path')
__scriptname__ = "XBMC Subtitles"
__scriptid__   = "script.xbmc.subtitles"
__author__     = "Amet,mr_blobby"

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
sys.path.append (BASE_RESOURCE_PATH)

xbmc.output("### [%s] - Version: %s" % (__scriptname__,__version__,),level=xbmc.LOGDEBUG )

if ( __name__ == "__main__" ):
    if not xbmc.getCondVisibility('Player.Paused') : xbmc.Player().pause() #Pause if not paused        
    import gui
    ui = gui.GUI( "script-XBMC-Subtitles-main.xml" , __cwd__ , "Default")
    ui.doModal()
    if xbmc.getCondVisibility('Player.Paused'): xbmc.Player().pause() # if Paused, un-pause
    del ui
    sys.modules.clear()


  
