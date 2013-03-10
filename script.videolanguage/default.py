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
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

class Main:
    def __init__( self ):
        log('version %s started' % __addonversion__ )
        self._parse_argv()
        self.window = xbmcgui.Window(12003) # Video info dialog
        if self.movieid:
            # clear old properties
            self._clear_properties()
            # only set new properties if movieid is not smaller than 0, e.g. -1
            if self.movieid > -1:
                # set new properties
                self._set_languages()

    def _parse_argv( self ):
        try:
            params = dict( arg.split( '=' ) for arg in sys.argv[ 1 ].split( '&' ) )
        except:
            params = {}
        self.movieid = int(params.get( 'movieid', False ))

    def _set_languages( self ):
        json_query = ''
        if xbmc.getCondVisibility('Container.Content(movies)'):
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["streamdetails"], "movieid":%s }, "id": 1}' % self.movieid)
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            log(json_query)
            json_response = simplejson.loads(json_query)
            if (json_response['result'] != None) and (json_response['result'].has_key('moviedetails')):
                self._set_properties( json_response['result']['moviedetails']['streamdetails']['audio'], json_response['result']['moviedetails']['streamdetails']['subtitle'])
        elif xbmc.getCondVisibility('Container.Content(episodes)'):
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": {"properties": ["streamdetails"], "episodeid":%s }, "id": 1}' % self.movieid)
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            log(json_query)
            json_response = simplejson.loads(json_query)
            if (json_response['result'] != None) and (json_response['result'].has_key('episodedetails')):
                self._set_properties( json_response['result']['episodedetails']['streamdetails']['audio'], json_response['result']['episodedetails']['streamdetails']['subtitle'])
     
    def _set_properties( self, audio, subtitles ):
        # Set language properties
        count = 1
        for item in audio:
            self.window.setProperty('AudioLanguage.%d' % count, item['language'])
            self.window.setProperty('AudioCodec.%d' % count, item['codec'])
            self.window.setProperty('AudioChannels.%d' % count, str(item['channels']))
            count += 1
        count = 1
        for item in subtitles:
            self.window.setProperty('SubtitleLanguage.%d' % count, item['language'])     
            count += 1
                
    def _clear_properties( self ):
        # 1 to 99 should really be enough
        for i in range(1,100):
            self.window.clearProperty('AudioLanguage.%d' % i)
            self.window.clearProperty('AudioCodec.%d' % i)
            self.window.clearProperty('AudioChannels.%d' % i)
            self.window.clearProperty('SubtitleLanguage.%d' % i)

if ( __name__ == "__main__" ):
    Main()
log('finished')
