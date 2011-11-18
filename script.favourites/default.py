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
            self.favList = [__language__(451)]
            self.favProperties = []
            for favourite in self.favourites:
                fav_path = favourite.childNodes [ 0 ].nodeValue
                fav_play = False
                # add return 
                if 'RunScript' not in fav_path: 
                    fav_path = fav_path.rstrip(')')
                    fav_path = fav_path + ',return)'
                if 'playlists/music' in fav_path or 'playlists/video' in fav_path:
                    fav_play = True
                self.favList.append(favourite.attributes[ 'name' ].nodeValue)
                try: fav_thumb = favourite.attributes[ 'thumb' ].nodeValue
                except: fav_thumb = ""
                self.favProperties.append([fav_path, fav_thumb, fav_play])
            self._show_dialog()
  
    def _show_dialog(self):
        if len(self.favList) > 0:
            dialog = xbmcgui.Dialog()
            try: retIndex = dialog.select(xbmc.getLocalizedString(1036), self.favList)
            except: retIndex = -1
            if retIndex > 0:
                fav_path = self.favProperties[retIndex-1][0]
                if (self.favProperties[retIndex-1][2]):
                    retBool = dialog.yesno(xbmc.getLocalizedString(559), __language__(450))
                    if retBool:
                        if 'playlists/music' in fav_path:
                            fav_path = fav_path.replace( 'ActivateWindow(10502,', 'PlayMedia(' )
                        else:
                            fav_path = fav_path.replace( 'ActivateWindow(10025,', 'PlayMedia(' )  
                # sleep to ensure smooth open/close animations
                xbmc.sleep(300)
                xbmc.executebuiltin( 'Skin.SetString(%s,%s)' % ( '%s.%s' % ( self.PROPERTY, "Path", ), fav_path.encode('utf-8'), ) )
                xbmc.executebuiltin( 'Skin.SetString(%s,%s)' % ( '%s.%s' % ( self.PROPERTY, "Label", ), self.favList[retIndex].encode('utf-8'), ) )
                xbmc.executebuiltin( 'Skin.SetString(%s,%s)' % ( '%s.%s' % ( self.PROPERTY, "Icon", ), self.favProperties[retIndex-1][1].encode('utf-8'), ) )
            elif retIndex == 0:
                # sleep to ensure smooth open/close animations
                xbmc.sleep(300)
                xbmc.executebuiltin( 'Skin.Reset(%s)' % '%s.%s' % ( self.PROPERTY, "Path", ) )
                xbmc.executebuiltin( 'Skin.Reset(%s)' % '%s.%s' % ( self.PROPERTY, "Label", ) )
                xbmc.executebuiltin( 'Skin.Reset(%s)' % '%s.%s' % ( self.PROPERTY, "Icon", ) )


if ( __name__ == "__main__" ):
        log('script version %s started' % __addonversion__)
        Main()
log('script stopped')
