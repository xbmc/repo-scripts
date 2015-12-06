import sys
import xbmc, xbmcaddon
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

ADDON        = xbmcaddon.Addon()
ADDONID      = ADDON.getAddonInfo('id')
ADDONVERSION = ADDON.getAddonInfo('version')

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (ADDONID, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

class Main:
    def __init__( self ):
        self._parse_argv()
        if self.albumid:
            self._play_album()            
        elif self.songid:
            self._get_albumid()
            self._play_album()

    def _parse_argv( self ):
        try:
            params = dict( arg.split( '=' ) for arg in sys.argv[ 1 ].split( '&' ) )
        except:
            params = {}
        self.songid = int(params.get( 'songid', False ))
        self.albumid = int(params.get( 'albumid', False ))
        self.tracknr = int(params.get( 'tracknr', False ))

    def _get_albumid( self ):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongDetails", "params": {"properties": ["artist", "album"], "songid":%s }, "id": 1}' % self.songid)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        log(json_query)
        json_response = simplejson.loads(json_query)
        if (json_response['result'] != None) and (json_response['result'].has_key('songdetails')):
            self.artist = artist = " / ".join(json_response['result']['songdetails']['artist'])
            self.album = json_response['result']['songdetails']['album']
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"filter": {"and": [{"field": "album", "operator": "is", "value": "%s"}, {"field": "artist", "operator": "is", "value": "%s"}] } }, "id": 1}' % (self.album,self.artist))
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if (json_response['result'] != None) and (json_response['result'].has_key('albums')):
            for item in json_response['result']['albums']:
                self.albumid = item['albumid']

    def _play_album( self ):
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "albumid": %d } }, "id": 1 }' % self.albumid)
        if self.tracknr and self.tracknr > 0:
            xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.GoTo", "params": { "playerid": 0, "to": %d }, "id": 1 }' % (self.tracknr - 1))        

if ( __name__ == "__main__" ):
    log('script version %s started' % ADDONVERSION)
    Main()
log('finished')
