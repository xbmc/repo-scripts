import sys
import os
import xbmc
import string

__scriptname__ = "XBMC Subtitles"
__scriptid__ = "script.xbmc.subtitles"
__author__ = "Amet"
__url__ = "http://code.google.com/p/xbmc-subtitles/"
__credits__ = ""
__version__ = "1.6.3"
__XBMC_Revision__ = "29565"

if not xbmc.getCondVisibility('Player.Paused') : xbmc.Player().pause() #Pause if not paused

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources', 'lib' ) )

sys.path.append (BASE_RESOURCE_PATH)

__language__ = xbmc.Language( os.getcwd() ).getLocalizedString
_ = sys.modules[ "__main__" ].__language__
__settings__ = xbmc.Settings( id=__scriptid__ )

  
#############-----------------Is script runing from OSD? -------------------------------###############

if not xbmc.getCondVisibility('videoplayer.isfullscreen') :
    
    __settings__.openSettings()
    if xbmc.getCondVisibility('Player.Paused'): xbmc.Player().pause() # if Paused, un-pause
else:
    skin = "main"
#    skin1 = str(xbmc.getSkinDir().lower())
#    skin1 = skin1.replace("-"," ")
#    skin1 = skin1.replace("."," ")
#    skin1 = skin1.replace("_"," ")
#    if ( skin1.find( "eedia" ) > -1 ):
#        skin = "MiniMeedia"
#    elif ( skin1.find( "tream" ) > -1 ):
#        skin = "MediaStream"
#    elif ( skin1.find( "edux" ) > -1 ):
#        skin = "MediaStream_Redux"
#    elif ( skin1.find( "aeon" ) > -1 ):
#        skin = "Aeon"
#    elif ( skin1.find( "alaska" ) > -1 ):
#        skin = "Alaska"
  
  
#    print " XBMC Subtitles version [ %s ]\nSkin Folder: [ %s ]\nXBMC Subtitles skin XML: [ %s ]" % (__version__,skin1,skin,)



    if ( __name__ == "__main__" ):          
        import gui
        ui = gui.GUI( "script-XBMC-Subtitles-%s.xml" % skin , os.getcwd(), "Default")
        ui.doModal()
        if xbmc.getCondVisibility('Player.Paused'): xbmc.Player().pause() # if Paused, un-pause
        del ui
        sys.modules.clear()


  
