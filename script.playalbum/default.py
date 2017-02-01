import sys
import xbmc, xbmcaddon
import json

ADDON        = xbmcaddon.Addon()
ADDONID      = ADDON.getAddonInfo('id')
ADDONVERSION = ADDON.getAddonInfo('version')

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (ADDONID, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

class Main:
    def __init__(self):
        self._parse_argv()
        if self.songid:
            self._get_albumid()
        self._play_album()

    def _parse_argv(self):
        try:
            params = dict(arg.split('=') for arg in sys.argv[1].split('&'))
        except:
            params = {}
        self.songid = int(params.get('songid', False))
        self.albumid = int(params.get('albumid', False))
        self.tracknr = int(params.get('tracknr', False))

    def _get_albumid(self):
        json_query = xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"AudioLibrary.GetSongDetails", "params":{"properties":["albumid"], "songid":%s}, "id":1}' % self.songid)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if json_response and json_response['result'] and json_response['result'].get('songdetails', None):
            self.albumid = json_response['result']['songdetails']['albumid']

    def _play_album(self):
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Player.Open", "params":{"item":{"albumid":%d}}, "id":1}' % self.albumid)
        if self.tracknr and self.tracknr > 0:
            xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Player.GoTo", "params":{"playerid":0, "to":%d}, "id":1}' % (self.tracknr - 1))

if (__name__ == "__main__"):
    log('script version %s started' % ADDONVERSION)
    Main()
log('finished')
