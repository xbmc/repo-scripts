import sys
import xbmc, xbmcgui, xbmcaddon
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')

def log(txt):
    message = '%s - %s' % (__addonid__, txt)
    xbmc.log(msg=message)

class Main:
    def __init__( self ):
        log('version %s started' % __addonversion__ )
        self._parse_argv()
        self._init_vars()
        if self.artist != '' and self.album != '':
            log('artist: %s' % self.artist)
            log('album: %s' % self.album)
            self._get_albumid()
            if self.albumid != '':
                self._get_songs()

    def _parse_argv( self ):
        try:
            params = dict( arg.split( '=' ) for arg in sys.argv[ 1 ].split( '&' ) )
        except:
            params = {}
        self.artist = params.get( 'artist', '' )
        self.album = params.get( 'album', '' )

    def _init_vars( self ):
        self.albumid = ''

    def _get_albumid( self ):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"properties": ["title", "artist"] }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if (json_response['result'] != None) and (json_response['result'].has_key('albums')):
            for item in json_response['result']['albums']:
                album = item['title']
                if album == self.album:
                    artist = item['artist']
                    if artist == self.artist:
                        self.albumid = str(item['albumid'])

    def _get_songs( self ):
        playlist = xbmc.PlayList(0)
        playlist.clear()
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"properties": ["file", "fanart"], "sort": { "method": "track" }, "albumid":%s }, "id": 1}' % self.albumid)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if (json_response['result'] != None) and (json_response['result'].has_key('songs')):
            for item in json_response['result']['songs']:
                song = item['file']
                fanart = item['fanart']
                listitem = xbmcgui.ListItem()
                listitem.setProperty( "fanart_image", fanart )
                playlist.add( url=song, listitem=listitem )
        xbmc.Player().play( playlist )

if ( __name__ == "__main__" ):
    Main()
log('finished')
