import xbmcgui

CANCEL_DIALOG  = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )

class PLAYER( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        self.channel_list = kwargs['ch_list']
        self.current      = kwargs['current_label']
        self.current_pos  = kwargs['current_channel']
        self.tune         = kwargs['tune']
      
    def onInit( self ):
        for item in self.channel_list:
            listitem = xbmcgui.ListItem( label=item['title'], thumbnailImage=item['thumb'] )
            listitem.setProperty( "thumb", item['thumb'] )
            listitem.setProperty( "url", item['url'] )
            self.getControl( 120 ).addItem( listitem )
        self.getControl( 206 ).setLabel( self.current )
        self.getControl( 120 ).selectItem( self.current_pos )  

    def onClick( self, controlId ):
        if controlId == 120:
            pos = self.getControl(120).getSelectedPosition()
            if pos != self.current_pos:
                self.current = self.tune(pos)
                self.getControl( 206 ).setLabel( self.current )
                self.current_pos = pos
        elif controlId == 601:
            self.close() # close player window when we stop the stream
    def onFocus( self, controlId ):
        pass

    def onAction( self, action ):
        if ( action.getId() in CANCEL_DIALOG):
          self.close()



