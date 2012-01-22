#import modules
import os
import sys
import time
import xbmc
import xbmcgui
from xbmcaddon import Addon

### get addon info
ADDON           = Addon( "script.artwork.downloader" )
ADDON_NAME      = ADDON.getAddonInfo( "name" )
ADDON_DIR       = ADDON.getAddonInfo( "path" )
ADDON_PROFILE   = xbmc.translatePath( ADDON.getAddonInfo('profile') )


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
        self.window.getControl( self.CONTROL_LABEL ).setLabel( "%s - %s" % ( heading, ADDON_NAME, ) )
        # set text
        self.window.getControl( self.CONTROL_TEXTBOX ).setText( text )

    def getText( self ):
        try:
            if sys.argv[ 1 ] == "downloadreport":
                return "Download report", self.readFile( os.path.join( ADDON_PROFILE, "downloadreport.txt" ) )
        except Exception, e:
            xbmc.log( ADDON_NAME + ': ' + str( e ), xbmc.LOGERROR )
        return "", ""

    def readFile( self, filename ):
        return open( filename ).read()


class WebBrowser:
    """ Display url using the default browser. """

    def __init__( self, *args, **kwargs ):
        try:
            url = sys.argv[ 2 ]
            # notify user
            notification( ADDON_NAME, url )
            xbmc.sleep( 100 )
            # launch url
            self.launchUrl( url )
        except Exception, e:
            xbmc.log( ADDON_NAME + ': ' + str( e ), xbmc.LOGERROR )

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
        xbmc.log( ADDON_NAME + ': ' + str( e ), xbmc.LOGERROR )



if ( __name__ == "__main__" ):
    Main()
