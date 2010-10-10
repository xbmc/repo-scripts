import sys
import os
import xbmc
import xbmcaddon

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources', 'lib' ) )
sys.path.append (BASE_RESOURCE_PATH)

__settings__ = xbmcaddon.Addon(id='script.xbmc.subtitles')
__language__ = __settings__.getLocalizedString
__version__  = __settings__.getAddonInfo('version')
__scriptname__ = "XBMC Subtitles"
__scriptid__ = "script.xbmc.subtitles"
__author__ = "Amet,mr_blobby"

xbmc.output("### [%s] - Version: %s" % (__scriptname__,__version__,),level=xbmc.LOGDEBUG )

if ( __name__ == "__main__" ):
    if not xbmc.getCondVisibility('Player.Paused') : xbmc.Player().pause() #Pause if not paused        
    import gui
    ui = gui.GUI( "script-XBMC-Subtitles-main.xml" , os.getcwd(), "Default")
    ui.doModal()
    if xbmc.getCondVisibility('Player.Paused'): xbmc.Player().pause() # if Paused, un-pause
    del ui
    sys.modules.clear()


  
