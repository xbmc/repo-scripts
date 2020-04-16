import json
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONVERSION = ADDON.getAddonInfo('version')

def log(txt):
    message = '%s: %s' % (ADDONID, txt)
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

class Main():
    def __init__(self, *args, **kwargs):
        log('script started')
        params = kwargs['params']
        self._parse_argv(params)
        if self.songid:
            self._get_albumid()
        self._play_album()
        log('script finished')

    def _parse_argv(self, params):
        self.songid = int(params.get('songid', False))
        self.albumid = int(params.get('albumid', False))
        self.tracknr = int(params.get('tracknr', False))

    def _get_albumid(self):
        json_query = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"AudioLibrary.GetSongDetails", "params":{"properties":["albumid"], "songid":%s}, "id":1}' % self.songid)
        json_response = json.loads(json_query)
        if json_response and 'result' in json_response and json_response['result'] and json_response['result'].get('songdetails', None):
            self.albumid = json_response['result']['songdetails']['albumid']

    def _play_album(self):
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Player.Open", "params":{"item":{"albumid":%d}}, "id":1}' % self.albumid)
        if self.tracknr and self.tracknr > 0:
            xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Player.GoTo", "params":{"playerid":0, "to":%d}, "id":1}' % (self.tracknr - 1))
