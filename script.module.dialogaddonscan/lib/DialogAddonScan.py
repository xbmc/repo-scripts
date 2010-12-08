
import os
import sys
from traceback import print_exc

import xbmc
from xbmcaddon import Addon

from AddonScan import Window
from AddonScan import xbmcguiWindowError


__settings__  = Addon( "script.module.dialogaddonscan" )
__addonName__ = __settings__.getAddonInfo( "name" )


class AddonScan( Window ):
    def __init__( self, parent_win=None, **kwargs ):
        # get class Window object
        Window.__init__( self, parent_win, **kwargs )
        self.canceled = False
        self.header = ""
        self.line = ""

    def close( self ):
        self.canceled = True
        xbmc.sleep( 100 )
        self.removeControls()
        del self.controls
        del self.window

    def create( self, line1="", line2="" ):
        self.header = line1 or __addonName__
        self.line   = line2
        self.update( 0, 0, line1, line2 )

    def iscanceled( self ):
        """ @ module.py
            if xbmc.getInfoLabel( "Window.Property(DialogAddonScanIsAlive)" ) == "true":
                # ok rajoute un bouton stop dans le context menu
                c_items += [ ( "Stop Addon Scan", "RunPlugin(%s?action=stopscan)" % sys.argv[ 0 ] ) ]
                listitem.addContextMenuItems( c_items )

            @ main.py
            if "stopscan" in sys.argv[ 2 ]:
                window = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
                window.setProperty( "CancelDialogAddonScan", "true" )
        """
        return self.canceled

    def update( self, percent1=0, percent2=0, line1="", line2="" ):
        self.setupWindow()
        if line1 and hasattr( self.heading, "setLabel" ):
            # set heading
            try: self.heading.setLabel( line1 )
            except: print_exc()
        if line2 and hasattr( self.label, "setLabel" ):
            # set label
            self.line = line2
            try: self.label.setLabel( line2 )
            except: print_exc()
        if percent1 and hasattr( self.progress1, "setPercent" ):
            # set current progress
            try: self.progress1.setPercent( percent1 )
            except: print_exc()
        if percent2 and hasattr( self.progress2, "setPercent" ):
            # set progress of listing
            try: self.progress2.setPercent( percent2 )
            except: print_exc()



def Demo():
    import xbmcgui
    selected = xbmcgui.Dialog().select( "Demo: "+__addonName__, [ "Show demo scan", "Open settings" ] )
    if selected == 0:
        from time import sleep
        try:
            scan = AddonScan()
            # create dialog
            scan.create( "Demo: "+__addonName__ )

            for pct in range( 101 ):
                percent2 = pct
                percent1 = percent2*10
                while percent1 > 100:
                    percent1 -= 100
                line2 = "Progress1 [B]%i%%[/B]   |   Progress2 [B]%i%%[/B]" % ( percent1, percent2 )

                # update dialog ( [ percent1=int, percent2=int, line1=str, line2=str ] ) all args is optional
                scan.update( percent1, percent2, line2=line2 )

                # if is canceled stop 
                if scan.iscanceled():
                    break

                sleep( .1 )

            # close dialog and auto destroy all controls
            scan.close()
        except xbmcguiWindowError:
            print_exc()
        except:
            print_exc()

    elif selected == 1:
        __settings__.openSettings()



if ( __name__ == "__main__" ):
    try:
        # settings called from other addon
        if sys.argv[ 1 ].lower() == "opensettins":
            __settings__.openSettings()
    except:
        print_exc()
