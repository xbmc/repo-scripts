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
        self.getControl( 190 ).setLabel(self.content)
        
        if self.content == 'movies':
            self.getControl( 4 ).setText( self.listitem.getProperty('plot') )
            self.getControl( 3 ).setImage( self.listitem.getProperty('icon') )
            self.getControl( 188 ).setLabel( self.listitem.getLabel() )
            self.getControl( 189 ).setLabel( self.listitem.getProperty('tagline') )
            self.getControl( 191 ).setLabel( self.listitem.getProperty('director') )
            self.getControl( 192 ).setLabel( self.listitem.getProperty('genre') )
            self.getControl( 193 ).setLabel( self.listitem.getProperty('year') )
            self.getControl( 194 ).setLabel( self.listitem.getProperty('rating') )
            if not self.listitem.getProperty('trailer'):
                self.getControl( 6 ).setVisible( False )
        
        elif self.content == 'tvshows':
            self.getControl( 5 ).setLabel( xbmc.getLocalizedString(1024) )
            self.getControl( 6 ).setVisible( False )
            self.setProperty("content","tvshow")
            self.getControl( 4 ).setText( self.listitem.getProperty('plot') )
            self.getControl( 3 ).setImage( self.listitem.getProperty('icon') )
            self.getControl( 188 ).setLabel( self.listitem.getLabel() )
            self.getControl( 189 ).setLabel( self.listitem.getProperty('tagline') )
            self.getControl( 191 ).setLabel( self.listitem.getProperty('studio') )
            self.getControl( 192 ).setLabel( self.listitem.getProperty('genre') )
            self.getControl( 193 ).setLabel( self.listitem.getProperty('premiered') )
            self.getControl( 194 ).setLabel( self.listitem.getProperty('rating') )
            
        elif self.content == 'episodes':
            self.getControl( 6 ).setVisible( False )
            self.setProperty("content","episode")
            self.getControl( 4 ).setText( self.listitem.getProperty('plot') )
            self.getControl( 3 ).setImage( self.listitem.getProperty('poster') )
            self.getControl( 188 ).setLabel( self.listitem.getProperty('tvshowtitle') )
            self.getControl( 189 ).setLabel( "S" + self.listitem.getProperty('season') + "E" + self.listitem.getProperty('episode') + " - " + self.listitem.getLabel() )
            self.getControl( 191 ).setLabel( self.listitem.getProperty('director') )
            self.getControl( 192 ).setLabel( self.listitem.getProperty('genre') )
            self.getControl( 193 ).setLabel( self.listitem.getProperty('premiered') )
            self.getControl( 194 ).setLabel( self.listitem.getProperty('rating') )
        
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
        elif controlId == 6:
            if self.content == 'movies':
                self._close_dialog( 'play_trailer' )

    def onFocus( self, controlId ):
        pass

    def onAction( self, action ):
        if ( action.getId() in CANCEL_DIALOG ) or ( action.getId() in ACTION_SHOW_INFO ):
            self._close_dialog()
