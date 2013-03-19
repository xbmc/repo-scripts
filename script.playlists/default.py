import os, sys, unicodedata
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
from elementtree import ElementTree as xmltree

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode('utf-8')
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode('utf-8'), level=xbmc.LOGDEBUG)

class Main:
    def __init__( self ):
        self._init_vars()
        self._clear_properties()
        self._parse_argv()
        self._fetch_playlists()
        self._set_properties()

    def _init_vars( self ):
        self.WINDOW = xbmcgui.Window( 10000 )
        self.playlists = []

    def _clear_properties( self ):
        for count in range( 100 ):
            self.WINDOW.clearProperty( 'ScriptPlaylist.%d.Name' % count)
            self.WINDOW.clearProperty( 'ScriptPlaylist.%d.Path' % count)

    def _parse_argv( self ):
        try:
            params = dict( arg.split( '=' ) for arg in sys.argv[ 1 ].split( '&' ) )
        except:
            params = {}
        self.type = params.get( 'type', '' )
        log('params: %s' % params)

    def _fetch_playlists( self ):
        if self.type == 'video':
            path = 'special://profile/playlists/video/'
        elif self.type == 'music':
            path = 'special://profile/playlists/music/'
        else:
            return
        try:
            dirlist = os.listdir( xbmc.translatePath( path ).decode('utf-8') )
        except:
            dirlist = []
        log('dirlist: %s' % dirlist)
        for item in dirlist:
            playlist = os.path.join( path, item)
            playlistfile = xbmc.translatePath( playlist )
            if item.endswith('.xsp'):
                contents = xbmcvfs.File(playlistfile, 'r')
                contents_data = contents.read().decode('utf-8')
                xmldata = xmltree.fromstring(contents_data.encode('utf-8'))
                for line in xmldata.getiterator():
                    if line.tag == "name":
                        name = line.text
                        if not name:
                            name = item[:-4]
                        self.playlists.append( (name, playlist) )
                        break
            elif item.endswith('.m3u'):
                name = item[:-4]
                self.playlists.append( (name, playlist) )
        log('playlists: %s' % self.playlists)

    def _set_properties( self ):
	for count, item in enumerate( self.playlists ):
            self.WINDOW.setProperty( 'ScriptPlaylist.%d.Name' % (count + 1), item[0] )
            self.WINDOW.setProperty( 'ScriptPlaylist.%d.Path' % (count + 1), item[1] )

if ( __name__ == "__main__" ):
        log('script version %s started' % __addonversion__)
        Main()
log('script stopped')
