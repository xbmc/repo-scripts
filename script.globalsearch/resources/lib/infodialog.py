import sys, re
import xbmc, xbmcgui

LANGUAGE   = sys.modules[ "__main__" ].LANGUAGE

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
        self.getControl( 110 ).setVisible( False )
        self.getControl( 120 ).setVisible( False )
        self.getControl( 130 ).setVisible( False )
        self.getControl( 140 ).setVisible( False )
        self.getControl( 150 ).setVisible( False )
        self.getControl( 160 ).setVisible( False )
        self.getControl( 170 ).setVisible( False )
        self.getControl( 180 ).setVisible( False )
        try:
            self.getControl( 200 ).setVisible( False )
        except:
            pass
        self.getControl( 191 ).setVisible( False )
        self.getControl( 192 ).setVisible( False )
        self.getControl( 193 ).setVisible( False )

    def _show_info( self ):
        self.getControl( 100 ).addItem( self.listitem )
        if self.content == 'epg':
            self.getControl( 192 ).setLabel( xbmc.getLocalizedString(208) )
            self.getControl( 193 ).setLabel( xbmc.getLocalizedString(20410) )
            try:
                self.getControl( 200 ).setVisible( True )
            except:
                pass
            self.getControl( 191 ).setVisible( True )
            self.getControl( 192 ).setVisible( True )
        if self.content == 'movies':
            self.getControl( 192 ).setLabel( xbmc.getLocalizedString(208) )
            self.getControl( 193 ).setLabel( xbmc.getLocalizedString(20410) )
            self.getControl( 110 ).setVisible( True )
            self.getControl( 191 ).setVisible( True )
            self.getControl( 192 ).setVisible( True )
            if self.listitem.getProperty('trailer'):
                self.getControl( 193 ).setVisible( True )
        elif self.content == 'tvshows':
            self.getControl( 192 ).setLabel( xbmc.getLocalizedString(1024) )
            self.getControl( 120 ).setVisible( True )
            self.getControl( 191 ).setVisible( True )
            self.getControl( 192 ).setVisible( True )
        elif self.content == 'seasons':
            self.getControl( 192 ).setLabel( xbmc.getLocalizedString(1024) )
            self.getControl( 130 ).setVisible( True )
            self.getControl( 191 ).setVisible( True )
            self.getControl( 192 ).setVisible( True )
        elif self.content == 'episodes':
            self.getControl( 192 ).setLabel( xbmc.getLocalizedString(208) )
            self.getControl( 140 ).setVisible( True )
            self.getControl( 191 ).setVisible( True )
            self.getControl( 192 ).setVisible( True )
        elif self.content == 'musicvideos':
            self.getControl( 192 ).setLabel( xbmc.getLocalizedString(208) )
            self.getControl( 150 ).setVisible( True )
            self.getControl( 191 ).setVisible( True )
            self.getControl( 192 ).setVisible( True )
        elif self.content == 'artists':
            self.getControl( 192 ).setLabel( xbmc.getLocalizedString(1024) )
            self.getControl( 160 ).setVisible( True )
            self.getControl( 191 ).setVisible( True )
            self.getControl( 192 ).setVisible( True )
        elif self.content == 'albums':
            self.getControl( 192 ).setLabel( xbmc.getLocalizedString(208) )
            self.getControl( 193 ).setLabel( xbmc.getLocalizedString(1024) )
            self.getControl( 170 ).setVisible( True )
            self.getControl( 191 ).setVisible( True )
            self.getControl( 192 ).setVisible( True )
            self.getControl( 193 ).setVisible( True )
        elif self.content == 'songs':
            self.getControl( 192 ).setLabel( xbmc.getLocalizedString(208) )
            self.getControl( 180 ).setVisible( True )
            self.getControl( 191 ).setVisible( True )
            self.getControl( 192 ).setVisible( True )
        elif self.content == 'actors':
            self.getControl( 192 ).setLabel( xbmc.getLocalizedString(208) )
            self.getControl( 193 ).setLabel( xbmc.getLocalizedString(20410) )
            self.getControl( 110 ).setVisible( True )
            self.getControl( 191 ).setVisible( True )
            self.getControl( 192 ).setVisible( True )
            if self.listitem.getProperty('trailer'):
                self.getControl( 193 ).setVisible( True )
        self.setFocus( self.getControl( 191 ) )

    def _close_dialog( self, action=None ):
        self.action = action
        self.close()

    def onClick( self, controlId ):
        if controlId == 191:
            self._close_dialog()
        elif controlId == 192:
            if self.content == 'epg':
                self._close_dialog( 'play_programme' )
            elif self.content == 'movies':
                self._close_dialog( 'play_movie' )
            elif self.content == 'tvshows':
                self._close_dialog( 'browse_tvshow' )
            elif self.content == 'seasons':
                self._close_dialog( 'browse_season' )
            elif self.content == 'episodes':
                self._close_dialog( 'play_episode' )
            elif self.content == 'musicvideos':
                self._close_dialog( 'play_musicvideo' )
            elif self.content == 'artists':
                self._close_dialog( 'browse_artist' )
            elif self.content == 'albums':
                self._close_dialog( 'play_album' )
            elif self.content == 'songs':
                self._close_dialog( 'play_song' )
            if self.content == 'actors':
                self._close_dialog( 'play_movie_actors' )
        elif controlId == 193:
            if self.content == 'movies':
                self._close_dialog( 'play_trailer' )
            if self.content == 'albums':
                self._close_dialog( 'browse_album' )
            if self.content == 'actors':
                self._close_dialog( 'play_trailer_actors' )

    def onFocus( self, controlId ):
        pass

    def onAction( self, action ):
        if ( action.getId() in CANCEL_DIALOG ) or ( action.getId() in ACTION_SHOW_INFO ):
            self._close_dialog()
