#import modules
import os
import sys
import time
import xbmc
import xbmcgui
from xbmcaddon import Addon

### get addon info
__addon__           = Addon( "script.artwork.downloader" )
__addonname__       = __addon__.getAddonInfo( "name" )
__addonpath__       = __addon__.getAddonInfo( "path" )
__addonprofile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode('utf-8')


class Viewer:
    # constants
    WINDOW = 10147
    CONTROL_LABEL = 1
    CONTROL_TEXTBOX = 5

    def __init__( self, *args, **kwargs ):
        # activate the text viewer window
        xbmc.executebuiltin( "ActivateWindow(%d)" % ( self.WINDOW, ) )
        # get window
        self.window = xbmcgui.Window( self.WINDOW )
        # give window time to initialize
        xbmc.sleep( 100 )
        # set controls
        self.setControls()

    def setControls( self ):
        #get header, text
        heading, text = self.getText()
        # set heading
        self.window.getControl( self.CONTROL_LABEL ).setLabel( "%s - %s" % ( heading, __addonname__, ) )
        # set text
        self.window.getControl( self.CONTROL_TEXTBOX ).setText( text )

    def getText( self ):
        try:
            if sys.argv[ 1 ] == "downloadreport":
                return "Download report", self.readFile( os.path.join( __addonprofile__, "downloadreport.txt" ) )
        except Exception, e:
            xbmc.log( __addonname__ + ': ' + str( e ), xbmc.LOGERROR )
        return "", ""

    def readFile( self, filename ):
        return open( filename ).read()


class WebBrowser:
    """ Display url using the default browser. """

    def __init__( self, *args, **kwargs ):
        try:
            url = sys.argv[ 2 ]
            # notify user
            notification( __addonname__, url )
            xbmc.sleep( 100 )
            # launch url
            self.launchUrl( url )
        except Exception, e:
            xbmc.log( __addonname__ + ': ' + str( e ), xbmc.LOGERROR )

    def launchUrl( self, url ):
        import webbrowser
        webbrowser.open( url )


def Main():
    try:
        if sys.argv[ 1 ] == "webbrowser":
            WebBrowser()
        else:
            Viewer()
    except Exception, e:
        xbmc.log( __addonname__ + ': ' + str( e ), xbmc.LOGERROR )



if ( __name__ == "__main__" ):
    Main()
