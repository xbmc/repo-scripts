import xbmc, xbmcgui, os, sys
from xbmcgui import Window
from xml.dom.minidom import parseString

dialog = xbmcgui.DialogProgress()

class Main:
    # grab the home window
    WINDOW = Window ( 10000 )

    def __init__( self ):
        self._clear_properties()
        self._read_file()
        self._parse_String()
        self._fetch_favourites()
        self.doc.unlink()
        dialog.close()

    def _clear_properties( self ):
        for count in range( 20 ):
            # clear Property
            self.WINDOW.clearProperty( "favourite.%d.path" % ( count + 1, ) )
            self.WINDOW.clearProperty( "favourite.%d.name" % ( count + 1, ) )

    def _read_file( self ):
        # Set path
        self.fav_dir = 'special://masterprofile//favourites.xml'
        # Check to see if file exists
        if (os.path.isfile( self.fav_dir ) == False):
            self.favourites_xml = '<favourites><favourite name="Can Not Find favourites.xml">-</favourite></favourites>'
        else:
            # read file
            self.fav = open( self.fav_dir , 'r')
            self.favourites_xml = self.fav.read()
            self.fav.close()

    def _parse_String( self ):
        self.doc = parseString( self.favourites_xml )
        self.favourites = self.doc.documentElement.getElementsByTagName ( 'favourite' )

    def _fetch_favourites( self ):
        # Go through each favourites
        count = 0
        for self.doc in self.favourites:
            self.fav_path = self.doc.childNodes [ 0 ].nodeValue
            # add return 
            if '10024' not in self.fav_path: self.fav_path = self.fav_path.replace( ')', ',return)' )
            if (sys.argv[ 1 ] == 'playlists=window'):
                if 'playlists/music' in self.fav_path: self.fav_path = self.fav_path.replace( 'PlayMedia(', 'ActivateWindow(10502,' )
                if 'playlists/video' in self.fav_path: self.fav_path = self.fav_path.replace( 'PlayMedia(', 'ActivateWindow(MyVideoLibrary,' )
            print 'playlists :' + sys.argv[ 1 ]
            # set properties
            self.WINDOW.setProperty( "favourite.%d.path" % ( count + 1, ) , self.fav_path )
            self.WINDOW.setProperty( "favourite.%d.name" % ( count + 1, ) , self.doc.attributes [ 'name' ].nodeValue )
            count = count+1

if ( __name__ == "__main__" ):
    Main()
