
# Modules general
import os
import sys
from traceback import print_exc

# Modules XBMC
import xbmc
import xbmcgui
from xbmcaddon import Addon


__settings__  = Addon( "script.module.dialogaddonscan" )
__addonName__ = __settings__.getAddonInfo( "name" )
__addonDir__  = __settings__.getAddonInfo( "path" )



class DialogTextViewer( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self, *args, **kwargs )
        self.heading = kwargs.get( "heading" ) or ""
        self.text = kwargs.get( "text" ) or ""

    def onInit( self ):
        try:
            self.getControl( 1 ).setLabel( self.heading )
            self.getControl( 5 ).setText( self.text )
        except:
            print_exc()

    def onFocus( self, controlID ):
        pass

    def onClick( self, controlID ):
        pass

    def onAction( self, action ):
        if action in [ 9, 10, 117 ]:
            self.close()


def showText( heading="", text="" ):
    w = DialogTextViewer( "DialogTextViewer.xml", __addonDir__, heading=heading, text=text )
    w.doModal()
    del w


if ( __name__ == "__main__" ):
    heading = __addonName__
    text = ""
    try:
        txt = None
        if sys.argv[ 1 ].lower() == "readme":
            heading = __addonName__ + ": Readme!"
            txt = os.path.join( __addonDir__, "readme.txt" )
        elif sys.argv[ 1 ].lower() == "changelog":
            heading = __addonName__ + ": changelog"
            txt = os.path.join( __addonDir__, "changelog.txt" )
        if txt:
            text = file( txt, "r" ).read()
    except:
        print_exc()
    if text:
        showText( heading, text )
