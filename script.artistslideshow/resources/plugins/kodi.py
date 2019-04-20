#v.0.1.0

import sys, xbmc
if sys.version_info >= (2, 7):
    import json as _json
else:
    import simplejson as _json


class objectConfig():
    def __init__( self ):
        self.loglines = []


    def provides( self ):
        return ['bio']
        
        
    def getBio( self, bio_params ):
        self.loglines = []
        response = xbmc.executeJSONRPC ( '{"jsonrpc":"2.0", "method":"Player.GetItem", "params":{"playerid":0, "properties":["artist", "description"]},"id":1}' )
        try:
            bio = _json.loads(response).get( 'result', {} ).get( 'item', {} ).get( 'description', '' )
        except UnicodeDecodeError:
            bio = ''
        return bio, self.loglines