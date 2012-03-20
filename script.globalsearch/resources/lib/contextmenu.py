# credits: Nuka1195

import sys
import xbmcgui

CANCEL_DIALOG  = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )
ACTION_CONTEXT_MENU = ( 117, )

class GUI( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self )
        self.area = kwargs[ "area" ]
        self.labels = kwargs[ "labels" ]

    def onInit( self ):
        self._show_context_menu()

    def _show_context_menu( self ):
        self._hide_buttons()
        self._setup_menu()
        self.setFocus( self.getControl( 1001 ) )

    def _hide_buttons( self ):
        for button in range( 1001, 1004 ):
            self.getControl( button ).setVisible( False )

    def _setup_menu( self ):
        button_height = self.getControl( 1001 ).getHeight()
        button_posx, button_posy = self.getControl( 1001 ).getPosition()
        dialog_width = self.getControl( 997 ).getWidth()
        dialog_top_height = self.getControl( 997 ).getHeight()
        dialog_bottom_height = self.getControl( 999 ).getHeight()
        dialog_top_posx, dialog_top_posy = self.getControl( 997 ).getPosition()
        dialog_middle_posy = self.getControl( 998 ).getPosition()[ 1 ]
        dialog_middle_offsety = dialog_middle_posy - dialog_top_posy
        button_offsetx = button_posx - dialog_top_posx
        button_offsety = button_posy - dialog_top_posy
        button_gap = 0
        dialog_middle_height = ( ( len( self.labels ) * ( button_height + button_gap ) ) - button_gap ) - 2 * ( dialog_top_height - ( button_posy - dialog_top_posy ) )
        dialog_height = dialog_middle_height + dialog_top_height + dialog_bottom_height
        dialog_posx = int( float( self.area[ 2 ] - dialog_width ) / 2 ) + self.area[ 0 ]
        dialog_posy = int( float( self.area[ 3 ] - dialog_height ) / 2 ) + self.area[ 1 ]
        button_posx = dialog_posx + button_offsetx
        button_posy = dialog_posy + button_offsety
        self.getControl( 998 ).setHeight( dialog_middle_height )
        self.getControl( 997 ).setPosition( dialog_posx, dialog_posy )
        self.getControl( 998 ).setPosition( dialog_posx, dialog_posy + dialog_middle_offsety )
        self.getControl( 999 ).setPosition( dialog_posx, dialog_posy + dialog_middle_offsety + dialog_middle_height )
        for button in range( len( self.labels ) ):
            self.getControl( button + 1001 ).setPosition( button_posx, button_posy + ( ( button_height + button_gap ) * button ) )
            self.getControl( button + 1001 ).setLabel( self.labels[ button ] )
            self.getControl( button + 1001 ).setVisible( True )
            self.getControl( button + 1001 ).setEnabled( True )

    def _close_dialog( self, selection=None ):
        self.selection = selection
        self.close()

    def onClick( self, controlId ):
        self._close_dialog( controlId - 1001 )

    def onFocus( self, controlId ):
        pass

    def onAction( self, action ):
        if ( action.getId() in CANCEL_DIALOG ) or ( action.getId() in ACTION_CONTEXT_MENU ):
            self._close_dialog()
