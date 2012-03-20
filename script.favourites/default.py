import os, sys
import xbmc, xbmcgui, xbmcaddon
from xml.dom.minidom import parseString

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__cwd__          = __addon__.getAddonInfo('path')
__language__  = __addon__.getLocalizedString

RESOURCES_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources' ) )
sys.path.append( os.path.join( RESOURCES_PATH, "lib" ) )

def log(txt):
    message = 'script.favourites: %s' % txt
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)
    
class Main:
    def __init__( self ):
        self.WINDOW = xbmcgui.Window( 10000 )
        self._parse_argv()
        self._clear_properties()
        self._read_file()
        self._parse_String()
        self._fetch_favourites()
        self.doc.unlink()
        
    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except:
            params = {}
        log( "### params: %s" % params )
        self.PROPERTY = params.get( "property", "" )
        self.PLAY = params.get( "playlists", False )

    def _clear_properties( self ):
        for count in range( 20 ):
            # clear Property
            self.WINDOW.clearProperty( "favourite.%d.path" % ( count + 1, ) )
            self.WINDOW.clearProperty( "favourite.%d.name" % ( count + 1, ) )
            self.WINDOW.clearProperty( "favourite.%d.thumb" % ( count + 1, ) )

    def _read_file( self ):
        # Set path
        self.fav_dir = xbmc.translatePath( 'special://profile/favourites.xml' )
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
        # If no property set
        if (self.PROPERTY == ""):
            # Go through each favourites
            count = 0
            for self.doc in self.favourites:
                self.fav_path = self.doc.childNodes [ 0 ].nodeValue
                # add return 
                if 'RunScript' not in self.fav_path: 
                    self.fav_path = self.fav_path.rstrip(')')
                    self.fav_path = self.fav_path + ',return)'
                if (self.PLAY):
                    if 'playlists/music' in self.fav_path: self.fav_path = self.fav_path.replace( 'ActivateWindow(10502,', 'PlayMedia(' )
                    if 'playlists/video' in self.fav_path: self.fav_path = self.fav_path.replace( 'ActivateWindow(10025,', 'PlayMedia(' )
                # set properties
                self.WINDOW.setProperty( "favourite.%d.path" % ( count + 1, ) , self.fav_path )
                self.WINDOW.setProperty( "favourite.%d.name" % ( count + 1, ) , self.doc.attributes [ 'name' ].nodeValue )
                try: self.WINDOW.setProperty( "favourite.%d.thumb" % ( count + 1, ) , self.doc.attributes [ 'thumb' ].nodeValue )
                except: pass
                count = count+1
        # Else show select dialog
        else:
            MyDialog(self.favourites, self.PROPERTY)
                
class MainGui( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self )
        self.listing = kwargs.get( "listing" )
        self.property = kwargs.get( "property" )

    def onInit(self):
        try:
            self.fav_list = self.getControl(6)
            self.getControl(3).setVisible(False)
        except:
            print_exc()
            self.fav_list = self.getControl(3)

        self.getControl(5).setVisible(False)
        self.getControl(1).setLabel(xbmc.getLocalizedString(1036))

        self.fav_list.addItem( xbmcgui.ListItem( __language__(451), iconImage="DefaultAddonNone.png" ) )

        for favourite in self.listing :
            listitem = xbmcgui.ListItem( favourite.attributes[ 'name' ].nodeValue )
            fav_path = favourite.childNodes [ 0 ].nodeValue
            try:
                if 'playlists/music' in fav_path or 'playlists/video' in fav_path:
                    listitem.setIconImage( "DefaultPlaylist.png" )
                    listitem.setProperty( "Icon", "DefaultPlaylist.png" )
                else:
                    listitem.setIconImage( favourite.attributes[ 'thumb' ].nodeValue )
                    listitem.setProperty( "Icon", favourite.attributes[ 'thumb' ].nodeValue )
            except: pass
            if 'RunScript' not in fav_path: 
                fav_path = fav_path.rstrip(')')
                fav_path = fav_path + ',return)'
            listitem.setProperty( "Path", fav_path )
            self.fav_list.addItem( listitem )
        self.setFocus(self.fav_list)

    def onAction(self, action):
        if action in ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, ):
            self.close()

    def onClick(self, controlID):
        log( "### control: %s" % controlID )
        if controlID == 6 or controlID == 3: 
            num = self.fav_list.getSelectedPosition()
            log( "### position: %s" % num )
            if num > 0:
                fav_path = self.fav_list.getSelectedItem().getProperty( "Path" )
                if 'playlists/music' in fav_path or 'playlists/video' in fav_path:
                    retBool = xbmcgui.Dialog().yesno(xbmc.getLocalizedString(559), __language__(450))
                    if retBool:
                        if 'playlists/music' in fav_path:
                            fav_path = fav_path.replace( 'ActivateWindow(10502,', 'PlayMedia(' )
                        else:
                            fav_path = fav_path.replace( 'ActivateWindow(10025,', 'PlayMedia(' )
                xbmc.executebuiltin( 'Skin.SetString(%s,%s)' % ( '%s.%s' % ( self.property, "Path", ), fav_path.encode('string-escape'), ) )
                xbmc.executebuiltin( 'Skin.SetString(%s,%s)' % ( '%s.%s' % ( self.property, "Label", ), self.fav_list.getSelectedItem().getLabel(), ) )
                fav_icon = self.fav_list.getSelectedItem().getProperty( "Icon" )
                if fav_icon:
                    xbmc.executebuiltin( 'Skin.SetString(%s,%s)' % ( '%s.%s' % ( self.property, "Icon", ), fav_icon, ) )
                xbmc.sleep(300)
                self.close()
            else:
                xbmc.executebuiltin( 'Skin.Reset(%s)' % '%s.%s' % ( self.property, "Path", ) )
                xbmc.executebuiltin( 'Skin.Reset(%s)' % '%s.%s' % ( self.property, "Label", ) )
                xbmc.executebuiltin( 'Skin.Reset(%s)' % '%s.%s' % ( self.property, "Icon", ) )
                xbmc.sleep(300) 
                self.close()

    def onFocus(self, controlID):
        pass
                
def MyDialog(fav_list, property):
    w = MainGui( "DialogSelect.xml", __cwd__, listing=fav_list, property=property )
    w.doModal()
    del w

if ( __name__ == "__main__" ):
    log('script version %s started' % __addonversion__)
    Main()
log('script stopped')
