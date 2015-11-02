import sys, re
import xbmc, xbmcgui


CANCEL_DIALOG  = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )
ACTION_SHOW_INFO = ( 11, )

class GUI( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self )
        self.listitem = kwargs[ "listitem" ]
        self.content = kwargs[ "content" ]

    def onInit( self ):
        self._hide_controls()
        self._show_info()

    def _hide_controls( self ):
        #self.getControl( 110 ).setVisible( False )
        pass

    def _show_info( self ):

        if self.content == 'movies':
            self.listitem.setProperty("type","movie")
        
        elif self.content == 'tvshows':
            self.listitem.setProperty("type","tvshow")
            
        elif self.content == 'episodes':
            self.listitem.setProperty("type","episode")
            
        list = self.getControl( 999 )
        list.addItem(self.listitem)
        
        self.setFocus( self.getControl( 5 ) )

    def _close_dialog( self, action=None ):
        self.action = action
        self.close()

    def onClick( self, controlId ):
        if controlId == 5:
            if self.content == 'movies':
                self._close_dialog( 'play_movie' )
            elif self.content == 'tvshows':
                self._close_dialog( 'browse_tvshow' )
            elif self.content == 'episodes':
                self._close_dialog( 'play_episode' )

    def onFocus( self, controlId ):
        pass

    def onAction( self, action ):
        if ( action.getId() in CANCEL_DIALOG ) or ( action.getId() in ACTION_SHOW_INFO ):
            self._close_dialog()
